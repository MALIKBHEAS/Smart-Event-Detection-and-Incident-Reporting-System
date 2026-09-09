# syntax=docker/dockerfile:1

# --- base: shared system deps -----------------------------------------------
FROM python:3.12-slim AS base

# libgl1/libglib required by opencv-python-headless at import time even
# though it's the "headless" build; curl is used by the HEALTHCHECK.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
ENV PYTHONPATH=/srv/backend \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY backend/requirements.txt backend/requirements.txt

# YOLO runtime: install CPU-only torch FIRST (no CUDA required/assumed --
# app/plugins/cv/yolo_detector.py auto-selects cuda only if
# torch.cuda.is_available() at runtime, and works fine on CPU otherwise).
# requirements.txt also lists torch/ultralytics; installing the CPU wheel
# up front means that later install is a no-op for torch instead of
# pulling much larger default CUDA wheels from PyPI.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/yolov8n.pt backend/yolov8n.pt

COPY docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh
RUN chmod +x /usr/local/bin/backend-entrypoint.sh

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["backend-entrypoint.sh"]

# --- dev: hot-reload, dev+test tooling included -----------------------------
FROM base AS dev

COPY backend/requirements-dev.txt backend/requirements-dev.txt
RUN pip install --no-cache-dir -r backend/requirements-dev.txt

# Source is bind-mounted over this in docker-compose for live reload; this
# COPY keeps the image runnable standalone too (e.g. `docker run` in CI).
COPY backend backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- production: minimal image, no dev tooling ------------------------------
FROM base AS production

COPY backend backend
RUN mkdir -p /srv/backend/evidence

# NOTE: intentionally running as root here, not a dropped-privilege user.
# The evidence-data named volume (see docker-compose.yml) is created
# root-owned by the Docker daemon; a non-root USER here would need the
# entrypoint to chown it at container start, which we can't verify works
# without a Docker daemon available in this environment. Harden this for a
# real production deployment (e.g. an init container or entrypoint chown
# step) once you can test it end-to-end.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
