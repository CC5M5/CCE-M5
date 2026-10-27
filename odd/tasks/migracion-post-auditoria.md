# Correcciones post-auditoría de la migración CCE-M5-Web-Presentaciones

**Objetivo:** Aplicar las recomendaciones del veredicto de la auditoría read-only de 2026-10-27 y dejar actualizada la documentación (spec, SDD, tareas, plantillas de unidades).

**Branch:** `fix/migracion-post-auditoria` (desde `main`).

**Delivery strategy:** `single-pr` — un único PR al final; push/PR/merge son decisión del usuario.

**Test runner:** `.venv/bin/python scripts/healthcheck.py`, `git diff --cached`, grep de referencias obsoletas. Sin cambios de código Python: no aplica pytest.

## Specs

S1. Recomendación 1 del veredicto: "Revertir o re-exportar las 5 entradas viejas de `web/data/presentaciones.json` a rutas relativas." — Las 5 entradas legacy (id 137/2026-10-25, 2026-10-04, 2026-09-27, 2026-09-20, 2026-09-13) vuelven a sus valores relativos commiteados; se conserva la entrada nueva `id 165` (2026-11-01) con rutas relativas correctas. Nota: el re-export no es viable porque `_relativize` del exportador solo convierte absolutas bajo el directorio del proyecto actual; las rutas `/home/pciath` no califican y se dejan tal cual.
S2. Recomendación 2 del veredicto: "Recuperar/copiar los archivos faltantes de `presentaciones/` desde el PC origen." — Sin acceso al PC origen en este alcance; decisión: aceptar las referencias huérfanas y documentarlo (los 5 archivos legacy no existen localmente, `presentaciones/` está vacío).
S3. Recomendación 3 del veredicto: "Limpiar `.env.example` para eliminar `/home/pciath`, `192.168.68.244` y puertos legacy." — BLOQUEADA: la política de seguridad de Gentle AI deniega el acceso a `.env.example`; pendiente de decisión explícita del usuario.
S4. Recomendación 4 del veredicto: "Actualizar referencias `Node 22.23.3` / `nvm` en `docs/SDD/08-web-astro.md`, `docs/SDD/09-despliegue.md`, `docs/SDD/10-migracion-nuevo-pc.md`, `docs/SDD/11-operacion-y-troubleshooting.md` y en las plantillas/unidades instaladas." — Evidencia: el build de `web/dist/` (165 archivos) se hizo en este PC con `node v24.22.1` el 2026-10-27; el node real del destino es `/usr/bin/node`; nvm no existe en este PC.
S5. Recomendación 5 del veredicto: "Anotar el commit `6e383fe` en `odd/tasks/migracion-portable.md`."
S6. Solicitud del usuario, verbatim: "Además modifica toda la documentación (spec, SDD, etc.) según se requiera para dejarlo todo actualizado." — Barrido de referencias obsoletas (`/home/pciath`, `192.168.68.244`, `nvm`, `22.23.3`) en README y docs/SDD, además de las específicas de S4.

## Tasks

| ID | Spec | Descripción | Ruta | Estado | Commit |
|---|---|---|---|---|---|
| T1 | S1 | Restaurar las 7 líneas de rutas absolutas `/home/pciath` a sus valores relativos commiteados en `web/data/presentaciones.json`, conservando la entrada `id 165`. | `web/data/presentaciones.json` | completed | work-unit (hash en L4) |
| T2 | S2 | Documentar la aceptación de las referencias huérfanas (sin acceso al PC origen) en el Log de este documento. | `odd/tasks/migracion-post-auditoria.md` | completed | work-unit (hash en L4) |
| T3 | S3 | Limpiar `.env.example` (path `/home/pciath`, IP `.244`, puertos legacy 4322/4324). | `.env.example` | blocked (acceso bloqueado por política de seguridad) | — |
| T4 | S4 | Eliminar el PATH nvm muerto de `config/systemd/user/cce-m5-admin.service` (líneas 8 y 10) y `config/systemd/user/cce-m5-healthcheck.service` (línea 8); `CCE_NODE_BIN=/usr/bin`; replicar en las unidades instaladas `~/.config/systemd/user/` y `daemon-reload`. | `config/systemd/user/`, `~/.config/systemd/user/` | completed | work-unit (hash en L4) |
| T5 | S4,S6 | Actualizar SDD `05-pipeline-semanal.md` (Node ≥ 22), `08-web-astro.md` (Node ≥ 22 verificado con 24.22.1), `09-despliegue.md` (`CCE_NODE_BIN=/usr/bin`), `10-migracion-nuevo-pc.md` (nvm opcional, troubleshooting), `11-operacion-y-troubleshooting.md` (rebuild manual), más `specs/09-diapositivas.md` (IP destino). | `docs/SDD/05-*.md`, `docs/SDD/08-*.md`, `docs/SDD/09-*.md`, `docs/SDD/10-*.md`, `docs/SDD/11-*.md`, `specs/09-diapositivas.md` | completed | work-unit (hash en L4) |
| T6 | S5 | Anotar `6e383fe` en la columna Commit de T1–T4 y la evidencia local de T5 en `odd/tasks/migracion-portable.md`, más entrada de Log de la auditoría. | `odd/tasks/migracion-portable.md` | completed | work-unit (hash en L4) |

## Log

L1. "Implementa las recomendaciones de la sección Veredict. Además modifica toda la documentación (spec, SDD, etc.) según se requiera para dejarlo todo actualizado."

L2. Evidencia de decisión sobre S1: `scripts/export_data_for_web.py::_relativize` solo convierte rutas absolutas que están bajo el `project_dir` actual (`path.relative_to(project_dir)`); las rutas legacy `/home/pciath/...` no califican y se exportan sin cambio. Por eso la corrección es quirúrgica (restaurar los valores commiteados), no un re-export. La BD `data/db.sqlite3` sigue conteniendo las rutas absolutas del origen para las 5 entradas (p. ej. id 137 `ruta_pdf_musicos`); un re-export futuro las conservará absolutas. Limpieza de la BD: fuera de alcance (mutación de datos, requiere autorización).

L3. (T2, S2) Aceptación documentada de referencias huérfanas: `presentaciones/` está vacío en este PC y los 5 archivos legacy (PDF/PPTX de 2026-09-13 a 2026-10-25) no existen localmente; el PC origen no está disponible. Se conservan las rutas relativas restauradas para portabilidad; no se crean archivos placeholder. Recuperar los archivos del origen es trabajo futuro con alcance propio.

L4. (evidencia, 2026-10-27) Checks parent del work unit: `web/data/presentaciones.json` JSON válido (16 entradas); diff staged `+16/-0` con 0 ocurrencias de `/home/pciath`; baseline `581c49d` también 0 (sin regresión); 4 unidades (plantillas + instaladas) sin nvm, admin con `CCE_NODE_BIN=/usr/bin`; `systemctl --user daemon-reload` OK; servicios `cce-m5-admin`/`cce-m5-web` `active`; barrido de referencias obsoletas: 0 en `docs/SDD/`, `README.md`, `specs/` (excluidas las intencionadas: `.github/workflows/deploy.yml:103` y `web/.nvmrc` como referencia CI/nvm); `scripts/healthcheck.py` exit 0 (4 endpoints 200). Verificador independiente `gentle-ai-verify`: NO DISPONIBLE (dos failures idénticas por infraestructura: el modelo local `llama.cpp/Qwen38-MTP-Vision-64K` no emite first run event); reportado como unavailable sin reintentos.
