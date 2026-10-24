#!/bin/bash
# Notifica por el canal configurado cuando el healthcheck de Docker falla.
# Se ejecuta dentro del contenedor; usa variables de entorno para el canal/target.
set -euo pipefail

SERVICE=${HEALTHCHECK_SERVICE:-cce-m5-admin}
URL=${HEALTHCHECK_URL:-http://localhost:4323/health}
CHANNEL=${HEALTHCHECK_NOTIFY_CHANNEL:-}
TARGET=${HEALTHCHECK_NOTIFY_TARGET:-}
TS=$(date -Iseconds)

# Registrar fallo en automation_log para observabilidad externa
register_db_log() {
    local msg="$1"
    local db=${HEALTHCHECK_DB_PATH:-/app/data/db.sqlite3}
    if [ -f "$db" ]; then
        python3 - "$db" "$msg" "$TS" <<'PY'
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
conn.execute(
    "INSERT INTO automation_log (agente, tarea, estado, mensaje, fecha) VALUES (?, ?, ?, ?, ?)",
    ("healthcheck", "health", "fallo", sys.argv[2], sys.argv[3]),
)
conn.commit()
conn.close()
PY
    fi
}

if [ -z "$CHANNEL" ] || [ -z "$TARGET" ]; then
    MSG="[$TS] healthcheck_notify: no hay canal/target configurado. Healthcheck FALLÓ para $SERVICE en $URL"
    echo "$MSG"
    register_db_log "$MSG"
    exit 1
fi

MESSAGE="🚨 Healthcheck FALLIDO para $SERVICE en $URL ($TS)"

case "$CHANNEL" in
    telegram)
        curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=$TARGET" -d "text=$MESSAGE" >/dev/null || true
        ;;
    slack)
        curl -fsS -X POST "$TARGET" -H "Content-type: application/json" \
            -d "{\"text\":\"$MESSAGE\"}" >/dev/null || true
        ;;
    discord)
        curl -fsS -X POST "$TARGET" -H "Content-type: application/json" \
            -d "{\"content\":\"$MESSAGE\"}" >/dev/null || true
        ;;
    webhook)
        curl -fsS -X POST "$TARGET" -H "Content-type: application/json" \
            -d "{\"message\":\"$MESSAGE\",\"service\":\"$SERVICE\",\"url\":\"$URL\",\"time\":\"$TS\"}" >/dev/null || true
        ;;
    *)
        echo "[$TS] healthcheck_notify: canal '$CHANNEL' no soportado"
        ;;
esac

register_db_log "$MESSAGE"
exit 1
