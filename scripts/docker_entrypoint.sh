#!/bin/bash
set -euo pipefail

# Inicializa la base de datos desde el seed si no existe
if [ ! -f /app/data/db.sqlite3 ]; then
    echo "[entrypoint] Creando db.sqlite3 desde seed..."
    cp /app/data/seeds/db.empty.sqlite3 /app/data/db.sqlite3
fi

# Exporta datos para la web estática si es necesario
if [ -d /app/web/data ]; then
    echo "[entrypoint] Exportando datos para web..."
    /app/.venv/bin/python /app/scripts/export_data_for_web.py --project-dir /app || true
fi

# Arranca la API de admin (incluye editores Flask montados bajo FastAPI)
echo "[entrypoint] Iniciando CCE-M5 admin en 0.0.0.0:4323"
/app/.venv/bin/python /app/scripts/run_admin_api.py --host 0.0.0.0 --port 4323 &
ADMIN_PID=$!

# Arranca servidor estático para la web pre-buildada en web/dist
echo "[entrypoint] Iniciando web estática en 0.0.0.0:4321"
/app/.venv/bin/python /app/scripts/serve_static.py --directory /app/web/dist --port 4321 --host 0.0.0.0 &
WEB_PID=$!

# Manejo de señales para shutdown limpio
cleanup() {
    echo "[entrypoint] Recibida señal de terminación, deteniendo servicios..."
    kill "$ADMIN_PID" "$WEB_PID" 2>/dev/null || true
    wait
    exit 0
}
trap cleanup SIGTERM SIGINT

# Espera a que cualquiera de los dos procesos termine
wait -n
EXIT_CODE=$?
echo "[entrypoint] Un servicio terminó con código $EXIT_CODE. Deteniendo el resto..."
kill "$ADMIN_PID" "$WEB_PID" 2>/dev/null || true
wait
exit $EXIT_CODE
