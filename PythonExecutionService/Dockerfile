# Build with a reviewed Python 3.11 base image digest supplied by the release process.
ARG PYTHON_BASE_IMAGE
FROM ${PYTHON_BASE_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/codequest
COPY runner.py /opt/codequest/runner.py
USER 65534:65534
ENTRYPOINT ["python", "-I", "-S", "/opt/codequest/runner.py"]
