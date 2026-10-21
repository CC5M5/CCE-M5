#!/bin/bash
set -euo pipefail

PROJECT_DIR="${CCE_PROJECT_DIR:-$HOME/proyectos/CCE-M5-Web-Presentaciones}"
SRC="$PROJECT_DIR/data/db.sqlite3"
DST_DIR="${CCE_BACKUP_DIR:-$HOME/.config/cce-m5/backups/db}"
KEEP_DAYS="${CCE_BACKUP_KEEP_DAYS:-30}"

if [[ ! -f "$SRC" ]]; then
    echo "ERROR: no existe $SRC" >&2
    exit 1
fi

mkdir -p "$DST_DIR"
TS=$(date +%Y%m%d_%H%M%S)
DST="$DST_DIR/db_${TS}.sqlite3.gz"

gzip -c "$SRC" > "$DST"
chmod 600 "$DST"

# Eliminar backups antiguos
find "$DST_DIR" -type f -name 'db_*.sqlite3.gz' -mtime +"$KEEP_DAYS" -delete

echo "Backup creado: $DST"
