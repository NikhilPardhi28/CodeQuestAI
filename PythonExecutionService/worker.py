"""Small internal HTTP adapter for the isolated Docker job runner.

This service has no database credentials and accepts only a bounded JSON job.
It is not usable as a secure execution boundary until Docker's Linux daemon,
the evaluator image digest, and the ADR adversarial checks are available.
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore

from docker_runner import EvaluationUnavailable, run_isolated_job

MAX_REQUEST_BYTES = 96 * 1024
JOB_SLOTS = BoundedSemaphore(2)
MAX_REQUEST_THREADS = 8


class WorkerHandler(BaseHTTPRequestHandler):
    server_version = "CodeQuestWorker/1"

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/internal/evaluate":
            self._send(404, {"error": "not_found"})
            return
        expected = os.environ.get("CODEQUEST_EVALUATION_WORKER_TOKEN", "")
        supplied = self.headers.get("Authorization", "")
        if not expected or not hmac.compare_digest(supplied, "Bearer " + expected):
            self._send(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, {"error": "invalid_request"})
            return
        if length < 1 or length > MAX_REQUEST_BYTES:
            self._send(413, {"error": "request_too_large"})
            return
        try:
            job = json.loads(self.rfile.read(length))
            if not JOB_SLOTS.acquire(blocking=False):
                self._send(503, {"error": "worker_busy"})
                return
            try:
                result = run_isolated_job(job)
            finally:
                JOB_SLOTS.release()
        except (ValueError, TypeError, KeyError):
            self._send(422, {"error": "invalid_job"})
            return
        except EvaluationUnavailable:
            self._send(503, {"error": "evaluation_unavailable"})
            return
        self._send(200, result)

    def log_message(self, _format: str, *_args: object) -> None:
        # Never log source code, test definitions, tokens, or arbitrary worker output.
        return

    def _send(self, status: int, data: dict[str, object]) -> None:
        encoded = json.dumps(data, separators=(",", ":")).encode("utf-8")
        if len(encoded) > 32 * 1024:
            status = 500
            encoded = b'{"error":"response_too_large"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(encoded)


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Bound open worker requests and time out slow clients before job admission."""

    def __init__(self, server_address, request_handler):
        self.request_slots = BoundedSemaphore(MAX_REQUEST_THREADS)
        super().__init__(server_address, request_handler)

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(10)
        return request, client_address

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Length: 0\r\nConnection: close\r\n\r\n"
                )
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.request_slots.release()
            self.shutdown_request(request)
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.request_slots.release()

    def handle_error(self, _request, _client_address):
        # Do not write request payloads, including partial source bodies, to stderr.
        return


def main() -> None:
    if not os.environ.get("CODEQUEST_EVALUATION_WORKER_TOKEN"):
        raise SystemExit("worker token is required")
    server = BoundedThreadingHTTPServer(
        (os.environ.get("CODEQUEST_WORKER_HOST", "127.0.0.1"), 8100), WorkerHandler
    )
    server.daemon_threads = True
    server.serve_forever()


if __name__ == "__main__":
    main()
