# Migración portable del proyecto CCE-M5-Web-Presentaciones

**Objetivo:** Preparar el proyecto para que pueda clonarse y ejecutarse en otro ordenador sin fallos por rutas, IPs o servicios hardcodeados del PC actual.

**Branch:** `main` (cambios de preparación directos, sin rama de feature por ser ajustes de infraestructura/portabilidad).

**Delivery strategy:** `single-pr` — un único PR con todos los cambios de portabilidad.

**Test runner:** `pytest` (Python) y `npm run build` (Astro). Verificación final con `.venv/bin/python scripts/healthcheck.py`.

## Specs

S1. **Preparar el proyecto para ser exportado a otro ordenador.**
S2. **Cuando se ejecute en otro ordenador, no debe fallar.**
S3. **Identificar qué cosas tienen que cambiar para migrarlo al otro PC.**

## Tasks

| ID | Spec | Descripción | Ruta | Estado | Commit |
|---|---|---|---|---|---|
| T1 | S1-S3 | Auditar y consolidar unidades systemd: eliminar duplicados, eliminar servicios legacy de editores separados, dejar como fuente canónica `config/systemd/user/` y asegurar que usan `%h` y variables de entorno. | `config/systemd/user/`, `systemd/` | completed | 6e383fe |
| T2 | S1-S3 | Eliminar rutas/IPs hardcodeadas del código fuente: `workflow_engine.py` (node path), `data/matching_config.json` (db_path absoluto), `web/src/pages/cancionero/index.astro` (admin API URL). | `src/web_admin/workflow_engine.py`, `data/matching_config.json`, `web/src/pages/cancionero/index.astro` | completed | 6e383fe |
| T3 | S2 | Hacer que `scripts/export_data_for_web.py` convierta rutas absolutas del PC origen a rutas relativas al proyecto. | `scripts/export_data_for_web.py` | completed | 6e383fe |
| T4 | S3 | Actualizar `docs/SDD/10-migracion-nuevo-pc.md`, `docs/SDD/09-despliegue.md` y `README.md` con instrucciones precisas y lista de valores que el destino debe configurar. | `docs/SDD/*.md`, `README.md` | completed | 6e383fe |
| T5 | S2 | Verificar portabilidad: tests unitarios pasan, build Astro OK, healthcheck pasa localmente. | `tests/`, `web/` | completed | verificación local (healthcheck exit 0, 2026-10-27) |

## Log

L1. "Quiero que prepares este proyecto para ser exportado a otro ordenador. Cuando lo ejecute en otro ordenador, no quiero que falle. Identifica que cosas tienen que cambiar para poder migrarlo al otro PC."

L2. Hallazgos de la auditoría inicial:
- Existen dos copias de units systemd: `systemd/` (6 ficheros, actual) y `config/systemd/user/` (6 ficheros, desfasada, aún incluye editores separados en puertos 4322/4324).
- `src/web_admin/workflow_engine.py:687` hardcodea `/home/pciath/.nvm/versions/node/v22.23.3/bin`.
- `data/matching_config.json:2` almacena `db_path` absoluto del PC origen.
- `web/src/pages/cancionero/index.astro:144` apunta a `http://192.168.68.244:4324` (IP y puerto antiguos).
- `scripts/export_data_for_web.py` exporta rutas absolutas de `presentaciones` a `web/data/presentaciones.json`.
- `docs/SDD/10-migracion-nuevo-pc.md` dice copiar units desde `config/systemd/user/` pero el contenido de esa carpeta no coincide con la arquitectura unificada actual.
- `.env` no está versionado y contiene valores destino-específicos (JWT secret, IP local, credenciales admin) que deben migrarse manualmente.

L3. Auditoría post-migración (2026-10-27): el commit `6e383fe` cubre T1-T4 (21 ficheros, +136/-152); T5 verificada localmente (build de `web/dist/` con node v24.22.1, healthcheck exit 0). Correcciones posteriores en `odd/tasks/migracion-post-auditoria.md`.
