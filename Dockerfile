# syntax=docker/dockerfile:1.7

# ---- Build stage ---------------------------------------------------------
# Build a wheel in an isolated stage so the runtime image stays small.
FROM python:3.12-slim AS build

WORKDIR /build

COPY pyproject.toml ./
COPY README.rst ./
COPY LICENSE ./
COPY steel_pigs ./steel_pigs

RUN pip install --no-cache-dir build \
    && python -m build --wheel --outdir /dist


# ---- Runtime stage -------------------------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/virtdevninja/steel_pigs"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.description="Powerful iPXE Generation Service"

# Install the built wheel plus gunicorn. Use a dedicated non-root user.
COPY --from=build /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl gunicorn==23.* \
    && rm -rf /tmp/*.whl \
    && useradd --system --uid 1000 --home-dir /app --create-home steel_pigs \
    && mkdir -p /data \
    && chown steel_pigs:steel_pigs /data

USER steel_pigs
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GUNICORN_WORKERS=2 \
    GUNICORN_BIND=0.0.0.0:8000

EXPOSE 8000

# Liveness probe hits the route we just added in webapp.py.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
import urllib.error; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)" \
    || exit 1

CMD ["sh", "-c", "exec gunicorn --bind ${GUNICORN_BIND} --workers ${GUNICORN_WORKERS} --access-logfile - steel_pigs.webapp:app"]
