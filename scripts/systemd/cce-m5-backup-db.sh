#!/bin/bash
set -euo pipefail

PROJECT_DIR="${CCE_PROJECT_DIR:-$HOME/proyectos/CCE-M5-Web-Presentaciones}"

# Backup WAL-consistente: sqlite3.Connection.backup() vía scripts/backup_db.py
PY="$PROJECT_DIR/.venv/bin/python"
[[ -x "$PY" ]] || PY="python3"

"$PY" "$PROJECT_DIR/scripts/backup_db.py"
