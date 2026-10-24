# Dockerfile de runtime para CCE-M5
# Uso: construir primero web/dist en el host con `cd web && npm run build`,
# luego `docker compose up --build`.

FROM python:3.13-slim

WORKDIR /app

# Dependencias runtime mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.lock.txt /app/
RUN sed -i '/^-e git+/d' /app/requirements.lock.txt \
    && python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.lock.txt

# Fuentes
COPY src /app/src
COPY scripts /app/scripts
COPY data/seeds /app/data/seeds

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CCE_PROJECT_DIR=/app \
    CCE_NODE_BIN=/usr/bin \
    CCE_ADMIN_HOST=0.0.0.0 \
    CCE_ADMIN_PORT=4323 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 4321 4323

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:4323/health || /app/scripts/healthcheck_notify.sh || exit 1

CMD ["/app/scripts/docker_entrypoint.sh"]
