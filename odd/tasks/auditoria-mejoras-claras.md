# Mejoras claras de la auditoría técnica de CCE-M5-Web-Presentaciones

**Objetivo:** Implementar las recomendaciones no ambiguas de la auditoría read-only de 2026-11-01, preparadas para la exposición futura a internet. Las decisiones con varias opciones viables quedan para las preguntas finales del usuario.

**Branch:** `fix/auditoria-mejoras-claras` (desde `main`, con el work-in-progress preexistente de Dockerfile/pdf_musicos/presentaciones.json intacto).

**Delivery strategy:** `single-pr` — un único PR al final; push/PR/merge son decisión del usuario (precedente: `migracion-post-auditoria`, PR #1 squash-mergeado).

**Test runner:** `.venv/bin/python -m pytest -q -p no:cacheprovider` (baseline pre-cambios: `277 passed, 1 warning in 75.88s`).

## Specs

S1. Auditoría H1 — credencial débil por defecto. Evidencia: `src/config.py` (`default_admin_password` default `"1234"`), `src/web_admin/auth.py::seed_default_admin` (llamado desde `lifespan` en `src/web_admin/api.py`), `.env.example:24` (`CCE_ADMIN_DEFAULT_PASSWORD=1234`), `README.md:23`. Cambio: sin default de contraseña; si no existe el admin y `CCE_ADMIN_DEFAULT_PASSWORD` no está configurado, el arranque falla con error claro (fail-fast); si el admin ya existe, no se requiere la variable. Actualizar `.env.example` y `README.md`.

S2. Auditoría H3 — `POST /comentarios` público sin autenticación. Evidencia: `src/web_admin/api.py::crear_comentario` expone `nombre`/`email` del visitante en un issue público de GitHub (`GITHUB_COMENTARIOS_OWNER`/`REPO`). Cambio: rate limit por IP (5/hora, configurable con `CCE_ADMIN_COMENTARIOS_RATE_LIMIT_MAX`); el issue público nunca incluye el email (el campo del modelo `ComentarioRequest.email` se conserva para compatibilidad con el formulario de la web). Se conservan los códigos 503 (sin token) y 502 (error GitHub).

S3. Auditoría H4 — backup de SQLite en vivo con WAL sin garantía de consistencia. Evidencia: `scripts/systemd/cce-m5-backup-db.sh` hace `gzip -c "$SRC" > "$DST"` sobre `data/db.sqlite3` mientras la base está en WAL. Cambio: nuevo `scripts/backup_db.py` que usa la API `sqlite3.Connection.backup()` (copia atómica y consistente); el script de systemd lo invoca; se conserva gzip, permisos 600 y retención de 30 días.

S4. Auditoría H2 — `PRAGMA integrity_check` por conexión. Evidencia: `src/db_manager.py::create_connection` llama a `_validate_integrity` en cada conexión. Cambio: quitarlo de `create_connection`; ejecutarlo una vez en `init_database`; la función `_validate_integrity` se conserva (el health endpoint hace su propio check).

S5. Auditoría M7 — `rebuild_web` usa `python3` del sistema y `systemctl` con `check=False`. Evidencia: `src/rebuild_web.py` (`python3 scripts/export_data_for_web.py`, `systemctl --user restart cce-m5-web.service` sin comprobación). Cambio: usar `sys.executable` (python del venv); `FileNotFoundError` → `"rebuild OK (sin reinicio: systemctl no disponible)"`; `CalledProcessError` → `"rebuild OK con error al reiniciar web: <última línea de error>"`; el camino de éxito sigue devolviendo `"rebuild OK"`.

S6. Auditoría M8 — tres versiones del parser de acordes (`v3` es la de producción). Cambio: nota de deprecación en los docstrings de `src/parsers/acordes_parser.py` (v1) y `src/parsers/acordes_parser_v2.py` (v2), señalando que `acordes_parser_v3` es el canónico. Sin eliminación de código.

S7. Auditoría B13/B14 — higiene de repo. Evidencia: `.gitignore` tiene `web/dist/` seguido de `!web/dist` (contradicción; `web/dist` no está trackeado) y `.coverage` está trackeado pese a estar en `.gitignore`. Cambio: eliminar la línea `!web/dist`; `git rm --cached .coverage` (el archivo local se conserva, queda ignorado).

S8. Auditoría B15 — SQL por f-string en `_add_column_if_missing` (`PRAGMA table_info({tabla})`, `ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}`). Cambio: validación de identificadores (regex `^[A-Za-z_][A-Za-z0-9_]*$`) con `ValueError` si no califican; `sqlite3.DatabaseError` si la tabla no existe; `PRAGMA table_info` con parámetro en `sqlite_master` para el check de existencia.

## Tasks

| ID | Spec | Descripción | Ruta | Estado | Commit |
|---|---|---|---|---|---|
| T1 | S1 | Fail-fast en `seed_default_admin` + default `None` en config + `README.md` + tests (auth, api). `.env.example` pendiente (bloqueado por política de seguridad). | inline | done | `2a5624a` |
| T2 | S4 | `integrity_check` solo en `init_database` + tests. | inline | pending | — |
| T3 | S2 | Rate limit por IP en `/comentarios` + email fuera del issue público + tests. | inline | pending | — |
| T4 | S3 | `scripts/backup_db.py` (API backup de sqlite3) + script de systemd + tests. | inline | pending | — |
| T5 | S5,S6,S7,S8 | `rebuild_web` (sys.executable + checks de systemctl), docstrings de parsers, `.gitignore`/`.coverage`, `_add_column_if_missing` + tests. | inline | pending | — |
| T6 | — | Full pytest post-cambios y comparación con baseline (277 passed). | inline | pending | — |
| T7 | — | Actualizar Log de este doc, mirror Engram, informe final con preguntas abiertas. | inline | pending | — |

## Log

L1. "Implementa las mejoras que claramente identificas teniendo en cuenta que la web posteriormente se va a exponer a internet y no solo a LAN. Si te encuentras con puntos que no te queden claros puedes pausar y preguntarme al final como quiero resolverlo." (usuario, 2026-11-01)

L2. (evidencia, 2026-11-01) Baseline pytest pre-cambios: `277 passed, 1 warning in 75.88s` (warning: `StarletteDeprecationWarning` por httpx en starlette.testclient; no bloqueante). Entorno: `.venv/bin/python` (Python 3.13.5).

L3. (decisión, 2026-11-01) El edit de `.env.example` fue bloqueado por la política de seguridad del entorno ("Gentle AI safety policy blocked access to sensitive path"). Se pospone la edición de ese archivo a las preguntas finales del usuario; el código y el README ya reflejan el fail-fast.

L4. (evidencia, 2026-11-01) T1: RED `test_seed_sin_password_y_sin_admin_falla` (DID NOT RAISE) → GREEN tras implementar el fail-fast. Descubrimiento: los fixtures de test no eran herméticos al `.env` del proyecto (pydantic-settings lo carga relativo al CWD y define `CCE_ADMIN_DEFAULT_PASSWORD` fuerte); se corrigió con `monkeypatch.chdir(tmp_path)` + `CCE_ADMIN_DEFAULT_PASSWORD` explícito en fixtures de `test_web_admin_auth.py` y `test_web_admin_api.py`. GREEN: `64 passed` en auth/api/config/database; commit `2a5624a`.
