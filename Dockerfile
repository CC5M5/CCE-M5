# Dockerfile de runtime para CCE-M5
# Asume que la web estática (web/dist) ya fue buildada en el host.

FROM python:3.13-slim

WORKDIR /app

# Dependencias runtime mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo lo necesario para instalar dependencias Python
COPY requirements.lock.txt /app/
RUN sed -i '/^-e git+/d' /app/requirements.lock.txt \
    && python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.lock.txt

# Copiar fuentes
COPY src /app/src
COPY scripts /app/scripts
COPY web/dist /app/web/dist

# Variables de entorno por defecto
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CCE_PROJECT_DIR=/app \
    CCE_NODE_BIN=/usr/bin \
    PATH="/app/.venv/bin:$PATH"

# Healthcheck genérico
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:4323/health || exit 1

EXPOSE 4321 4322 4323 4324

CMD ["/app/.venv/bin/python", "scripts/run_admin_api.py", "--host", "0.0.0.0", "--port", "4323"]
