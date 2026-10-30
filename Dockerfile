# Dockerfile multi-stage para CCE-M5 Web Presentaciones.
# Construye la web estática en un stage de Node y copia el dist al runtime de Python.
# Uso: docker compose up --build

# ---------------------------------------------------------------------------
# Stage 1: build de la web estática (Astro)
# ---------------------------------------------------------------------------
FROM node:22.23.3-slim AS web-builder

WORKDIR /build

# Instalar Python 3.13 para que el script `npm run sync` pueda ejecutar scripts Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copiar fuentes de la web y scripts de sincronización.
COPY web /build/web
COPY scripts/sync_presentaciones_html.py /build/scripts/sync_presentaciones_html.py
COPY scripts/export_data_for_web.py /build/scripts/export_data_for_web.py
COPY data/seeds /build/data/seeds

WORKDIR /build/web
RUN npm ci

# Exportar datos del seed y construir el sitio estático.
# Se usa el seed canónico como base de datos de build.
RUN mkdir -p /build/data /build/presentaciones_html \
    && cp /build/data/seeds/db.empty.sqlite3 /build/data/db.sqlite3 \
    && PYTHON=python3 npm run build \
    && rm -rf /build/data/db.sqlite3

# ---------------------------------------------------------------------------
# Stage 2: runtime Python mínimo
# ---------------------------------------------------------------------------
FROM python:3.13-slim

WORKDIR /app

# Dependencias del sistema necesarias para WeasyPrint, python-pptx y SQLite.
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libfreetype6 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# Dependencias Python runtime.
COPY requirements.runtime.txt /app/
RUN python -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r /app/requirements.runtime.txt

# Fuentes de la aplicación.
COPY src /app/src
COPY scripts /app/scripts
COPY data/seeds /app/data/seeds

# Copiar la web estática pre-construida desde el stage web-builder.
COPY --from=web-builder /build/web/dist /app/web/dist

# Variables de entorno por defecto.
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CCE_PROJECT_DIR=/app \
    CCE_ADMIN_HOST=0.0.0.0 \
    CCE_ADMIN_PORT=4323 \
    PATH="/app/.venv/bin:$PATH"

EXPOSE 4321 4323

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/.venv/bin/python /app/scripts/healthcheck_docker.py || /app/scripts/healthcheck_notify.sh || exit 1

CMD ["/app/scripts/docker_entrypoint.sh"]
