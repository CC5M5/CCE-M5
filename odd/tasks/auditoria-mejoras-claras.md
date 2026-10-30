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

S9. Seguimiento — autenticación en `POST /comentarios`. Cambio: el endpoint requiere token válido vía `Depends(get_current_user)` (401 sin token); se conserva el rate limit por IP (429) y el contrato `503` sin `GITHUB_TOKEN_COMENTARIOS` (ahora alcanzable solo autenticado) y `502` en error de GitHub. `tests/unit/test_comentarios_proxy.py` cubre el comportamiento autenticado y no autenticado; `tests/unit/test_web_admin_api.py` actualiza `test_comentarios_sin_config` (503→401) y añade el endpoint 503 autenticado.

## Tasks

| ID | Spec | Descripción | Ruta | Estado | Commit |
|---|---|---|---|---|---|
| T1 | S1 | Fail-fast en `seed_default_admin` + default `None` en config + `README.md` + tests (auth, api). `.env.example` pendiente (bloqueado por política de seguridad). | inline | done | `2a5624a` |
| T2 | S4,S8 | `integrity_check` solo en `init_database` + `_add_column_if_missing` con validación de identificadores y check de existencia de tabla + tests. | inline | done | `321c1d9` |
| T3 | S2 | Rate limit por IP en `/comentarios` + email fuera del issue público + tests. | inline | done | `056aaee` |
| T4 | S3 | `scripts/backup_db.py` (API backup de sqlite3) + script de systemd + tests. | inline | done | `bdfe7bd` |
| T5 | S5,S6,S7 | `rebuild_web` (sys.executable + checks de systemctl), docstrings de parsers, `.gitignore`/`.coverage` + tests. | inline | done | `d9557b4` |
| T6 | — | Full pytest post-cambios y comparación con baseline (277 passed) → 292 passed, 0 fallos. | inline | done | — (job-2) |
| T7 | — | Actualizar Log de este doc, mirror Engram, informe final con preguntas abiertas. | inline | done | — |
| T8 | S9 | Autenticación en `crear_comentario` (`Depends(get_current_user)`) + tests de endpoint (401, 503 autenticado) + update de `test_web_admin_api.py` + ignore B008 en `pyproject.toml` para el test. | inline | done | `1ee66de` |
| T9 | — | Instrucciones de terminal para actualizar `.env.example` (edit directa bloqueada por política de seguridad); entregadas en el informe de seguimiento. | inline | done | — |
| T10 | — | Integrar el WIP de `main` en la rama (`Dockerfile` +fonts-dejavu, `src/generators/pdf_musicos.py` fallback monoespaciado, `tests/unit/test_pdf_musicos_fonts.py`). `web/data/presentaciones.json` ya estaba integrado por commits preexistentes. | inline | done | `fb7a6c8` |
| T11 | — | Documentar en `README.md` los requisitos de exposición a internet (HTTPS, `CCE_ADMIN_JWT_SECRET`, CORS, base path, rate limit/Redis, auth en `/comentarios`, backups). | inline | done | (con T12) |
| T12 | — | Mirror Engram final del seguimiento + informe final de seguimiento en español. | inline | done | — |

## Log

L1. "Implementa las mejoras que claramente identificas teniendo en cuenta que la web posteriormente se va a exponer a internet y no solo a LAN. Si te encuentras con puntos que no te queden claros puedes pausar y preguntarme al final como quiero resolverlo." (usuario, 2026-11-01)

L2. (evidencia, 2026-11-01) Baseline pytest pre-cambios: `277 passed, 1 warning in 75.88s` (warning: `StarletteDeprecationWarning` por httpx en starlette.testclient; no bloqueante). Entorno: `.venv/bin/python` (Python 3.13.5).

L3. (decisión, 2026-11-01) El edit de `.env.example` fue bloqueado por la política de seguridad del entorno ("Gentle AI safety policy blocked access to sensitive path"). Se pospone la edición de ese archivo a las preguntas finales del usuario; el código y el README ya reflejan el fail-fast.

L4. (evidencia, 2026-11-01) T1: RED `test_seed_sin_password_y_sin_admin_falla` (DID NOT RAISE) → GREEN tras implementar el fail-fast. Descubrimiento: los fixtures de test no eran herméticos al `.env` del proyecto (pydantic-settings lo carga relativo al CWD y define `CCE_ADMIN_DEFAULT_PASSWORD` fuerte); se corrigió con `monkeypatch.chdir(tmp_path)` + `CCE_ADMIN_DEFAULT_PASSWORD` explícito en fixtures de `test_web_admin_auth.py` y `test_web_admin_api.py`. GREEN: `64 passed` en auth/api/config/database; commit `2a5624a`.

L5. (evidencia, 2026-11-01) T2: tests RED de colocación (spy sobre `_validate_integrity`) + validación de identificadores de `_add_column_if_missing` (ValueError por inyección, DatabaseError por tabla inexistente) → GREEN. Suite completa: `283 passed, 2 warnings`; commit `321c1d9`.

L6. (evidencia, 2026-11-01) T3: RED (sin setting, sin rate limit, email en issue) → GREEN. `crear_comentario` ahora recibe `Request`, aplica `IPRateLimiter` dedicado (`CCE_ADMIN_COMENTARIOS_RATE_LIMIT_MAX`, default 5/h → 429) y el cuerpo del issue público ya no incluye el email (el campo queda en `ComentarioRequest` por compatibilidad del formulario). `503` sin token y `502` error GitHub preservados. `6 passed` en `test_comentarios_proxy.py`; vecinos `62 passed`; commit `056aaee`.

L7. (evidencia, 2026-11-01) T4: RED por falta de `scripts/backup_db.py` → GREEN con 4 tests (gzip consistente, datos WAL comitados incluidos, exit 1 sin fuente, retención por días). El backup usa `sqlite3.Connection.backup()` + `integrity_check` de la copia + gzip 600 + retención 30 días; el script de systemd ahora delega en el script Python. Commit `bdfe7bd`.

L8. (evidencia, 2026-11-01) T5: RED (3 tests de `rebuild_web`) → GREEN. `rebuild_web` usa `sys.executable` para el export y ahora distingue systemctl ausente vs. reinicio fallido; notas de deprecación en `acordes_parser.py` (v1) y `acordes_parser_v2.py` señalando v3 como canónico; `.gitignore` sin la contradicción `!web/dist`; `.coverage` fuera del índice (archivo local conservado). `58 passed` en rebuild+parser; commit `d9557b4`.

L9. (evidencia, 2026-11-01) T6: suite completa post-cambios (job-2): `292 passed, 2 warnings in 80.65s` vs. baseline `277 passed, 1 warning in 75.88s` → +15 tests nuevos, 0 fallos, sin regresiones. Warnings: `StarletteDeprecationWarning` (httpx en testclient, preexistente) y `DeprecationWarning` de WeasyPrint/HarfBuzz (librería, no del código). Log: `/tmp/gpYe2HuC/gentle-jobs-lVhiiw/job-2.log`.

L10. (decisión, 2026-11-01) Slice final: 825 líneas de cambios en 6 commits desde `origin/main`, muy por encima del umbral de ~400; se mantiene `single-pr` (un único PR al final), push/PR/merge son decisión del usuario.

L11. (usuario, seguimiento) "(1) te doy el paso a paso del `.env.example` para terminal, (2) implemento autenticación en comentarios, (3) integro el WIP de `main` en el branch, (4) documento los requisitos de internet en el README y te explico qué hacer" (asistente, confirmado por "continua" del usuario, 2026-11-01).

L12. (evidencia, seguimiento) T8: tests de endpoint escritos antes de aplicar auth (`test_endpoint_sin_token_devuelve_401`, `test_endpoint_con_token_authenticado`) → se aplicó `Depends(get_current_user)` en `crear_comentario`. GREEN: `8 passed` en `test_comentarios_proxy.py`; vecinos `73 passed`. `test_comentarios_sin_config` de `test_web_admin_api.py` actualizado (sin token de auth → 401, antes esperaba 503); nuevo `test_comentarios_autenticado_sin_token_github_devuelve_503`. Ignore `B008` por archivo en `pyproject.toml` para el test (patrón FastAPI ya usado en `src/web_admin/api.py` y `auth.py`). Suite completa (job-3): `295 passed, 1 warning in 71.46s` → sin regresiones (+3 tests vs. 292). Commit `1ee66de`.

L13. (evidencia, seguimiento) Slice actual: 953 líneas en 8 commits desde `origin/main`, de los cuales `b626068` y `84e5f08` (`chore(acordes): editar Canción editable`, OpenClaw Agent, 2026-10-29) son commits de datos preexistentes en `main` local (por delante de `origin/main`); los authored por esta rama son ~699 líneas. Se mantiene `single-pr`.

L14. (evidencia, seguimiento) T9: lista canónica de variables confirmada contra `README.md` (tablas de config) y `src/web_admin/config.py` (delegación `GITHUB_TOKEN_COMENTARIOS`→`s.github_token_comentarios`, `GITHUB_COMENTARIOS_OWNER`/`REPO`→settings, fallback JWT en `config.py:59`). Las instrucciones paso a paso para `.env.example` se entregan en el informe final de seguimiento (el edit directo sigue bloqueado por política de seguridad).

L15. (evidencia, seguimiento) T10: el WIP de `main` se inspeccionó diff por diff (`Dockerfile` +`fonts-dejavu`; `pdf_musicos.py` con `_fc_match_family_file`, `_find_monospace_pair`, `MONOSPACE_FALLBACK_FAMILIES` y fallback de `FONT_ACORDES`/`FONT_LETRA` a la monoespaciada del sistema cuando falta Courier New; `web/data/presentaciones.json` ya integrado por los commits preexistentes). Se corrigió el orden de imports de `tests/unit/test_pdf_musicos_fonts.py` (Ruff I001). Ruff check/format limpio en los tres archivos; `6 passed` en `test_pdf_musicos_fonts.py`; suite completa (job-4): `295 passed, 1 warning in 69.06s` → sin regresiones. Commit `fb7a6c8`. `data/db.sqlite3.bak-before-normalize` no se commitea (artefacto local).

L16. (evidencia, seguimiento) T11: sección `## Exponer a Internet (requisitos)` añadida a `README.md` (TLS/reverse proxy, `CCE_ADMIN_JWT_SECRET` ≥32 bytes, `ADMIN_CORS_ORIGINS`, fail-fast de `CCE_ADMIN_DEFAULT_PASSWORD`, auth+rate limit en `/comentarios` con `CCE_ADMIN_REDIS_URL` para multi-instancia, backups diarios a `~/.config/cce-m5/backups/db/` (`CCE_BACKUP_DIR`)). Commit `52d6ce2` (amendado tras corregir la ruta de backups).

L17. (cierre, seguimiento) Slice final: 11 commits desde `origin/main`, 1211 líneas de cambios en total; `b626068` (246) y `84e5f08` (8) son datos preexistentes de `main` local (OpenClaw Agent), así que esta rama authored ~957 líneas. Se mantiene `single-pr`; push/PR/merge son decisión del usuario. Suite final (job-4): `295 passed, 1 warning in 69.06s`. Todo el seguimiento (T8-T12) cerrado.
