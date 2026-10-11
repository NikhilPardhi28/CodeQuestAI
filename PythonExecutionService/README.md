# Python execution service

The worker is an internal adapter only. It has no database credentials and accepts jobs from BackendAPI only when the shared worker token is configured. Learner code runs in a disposable Docker job container; there is no Python subprocess fallback on the API or Windows host.

## Evaluator image

Build the evaluator from a reviewed Python base image pinned by digest. The CI build currently pins `python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb`; see the [Docker Official Image metadata](https://hub.docker.com/layers/library/python/3.11-slim-bookworm/) and `.github/workflows/baseline.yml`.

```powershell
docker info --format '{{.ServerVersion}}'
docker build --pull --build-arg PYTHON_BASE_IMAGE='python:3.11-slim-bookworm@sha256:2333bd330d12de02514770b3585cad313644316047cdee24a7acfdece6de6efb' --tag codequest-evaluator:local PythonExecutionService
docker image inspect --format '{{.Id}}' codequest-evaluator:local
```

For deployment, publish the built image to an approved registry, record its immutable repository digest, and set `CODEQUEST_EVALUATOR_IMAGE=registry.example/codequest-evaluator@sha256:<64-lowercase-hex>`. Production does not accept mutable tags or local image IDs. The local image content ID is accepted only in `local`, `test`, or `ci` environments to run reproducible tests on a freshly built disposable image.

Run the worker separately from BackendAPI after the Linux Docker daemon and image are verified:

```powershell
$env:CODEQUEST_ENV = 'local'
$env:CODEQUEST_EVALUATOR_IMAGE = 'sha256:<content-id-from-inspect>'
$env:CODEQUEST_EVALUATION_WORKER_TOKEN = '<local-random-secret-at-least-32-characters>'
python PythonExecutionService/worker.py
```

Configure BackendAPI with the loopback worker URL and the same token through local secret storage. Remote worker URLs must use HTTPS. Do not commit the token or add it to Unity. The evaluator container is started without networking, with a read-only root filesystem, non-root UID 65534, dropped capabilities, no-new-privileges, process/memory/CPU/file limits, and a bounded temporary filesystem. These controls are not a substitute for reviewing Docker host privilege, the kernel, seccomp/AppArmor policy, and adversarial tests on the target Linux host.

## Integration checks

`test_contract.py` uses mocked Docker calls to validate the request boundary and launch flags; it never executes student source. `test_container_integration.py` is different: it executes probe and hostile samples only inside the actual evaluator container. It requires the opt-in `CODEQUEST_RUN_EVALUATOR_CONTAINER_TESTS=1` and a freshly built content digest. The workflow enables it on a hosted Ubuntu runner after checking Docker. Do not set the opt-in on a machine that is not approved for hostile-code testing.

The current Windows environment has Docker CLI 29.6.1 but no `dockerDesktopLinuxEngine` pipe. The evaluator container and hostile-code tests were therefore not run locally. Backend submission routes remain disabled unless the worker URL and token are configured.
