# syntax=docker/dockerfile:1
# --- Frontend-Build -----------------------------------------------------------
FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Laufzeit ---------------------------------------------------------------------
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data \
    FRONTEND_DIST=/app/frontend/dist \
    HOST=0.0.0.0 \
    PORT=8000 \
    TZ=Europe/Berlin

RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home /app app
WORKDIR /app/backend
COPY backend/requirements.lock ./
RUN pip install --require-hashes -r requirements.lock
COPY backend/ ./
COPY --from=frontend /build/dist /app/frontend/dist
RUN mkdir -p /data && chown -R app:app /data
USER app
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import json,os,ssl,urllib.request;s='https' if os.environ.get('TLS_CERT_FILE') else 'http';c=ssl._create_unverified_context();print(json.load(urllib.request.urlopen(f'{s}://127.0.0.1:8000/api/v1/health',context=c))['status'])" || exit 1
# Erststart führt Migrationen aus (serve ruft migrate auf)
CMD ["python", "-m", "app.cli", "serve"]
