#!/usr/bin/env bash
# Supervisor simple para el editor de diapositivas CCE-M5.
# Reinicia el editor si termina por cualquier motivo.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="/tmp/editor_flask.log"
PID_FILE="/tmp/editor.pid"
PYTHON="$PROJECT_DIR/.venv/bin/python"
SERVER="$PROJECT_DIR/scripts/editor_diapositivas_server.py"

# Limpiar PID antiguo
rm -f "$PID_FILE"

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando editor de diapositivas..." >> "$LOG_FILE"
    "$PYTHON" "$SERVER" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo "$PID" > "$PID_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Editor PID: $PID" >> "$LOG_FILE"
    # Esperar a que el proceso termine
    if wait "$PID"; then
        EXIT_CODE=$?
    else
        EXIT_CODE=$?
    fi
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Editor terminó con código $EXIT_CODE. Reiniciando en 3s..." >> "$LOG_FILE"
    sleep 3
done
