# seed-y-bundle-github

Objetivo: que la presentación 2026-11-01 aparezca en el listado y se vea (iframe con bundle) en GitHub Pages. Estrategia de entrega: commits directos a `main` (autorizados por el usuario). Runner de tests: `.venv/bin/python -m pytest -q -p no:cacheprovider` (n/a aquí: no hay código Python de app que cambie; la verificación es funcional/CI).

## Specs

- S1: El usuario autorizó "Ejecuta paso 1" (paso 1 = sincronizar el seed: `scripts/seed_sync.py --apply` desde la BD local, commit del seed y push a `main`), para que "2026-11-01 aparezca en el listado de GitHub". Criterio de aceptación: `data/seeds/db.empty.sqlite3` contiene la presentación `fecha_domingo='2026-11-01'` (id 165, estado `publicada`) con sus 28 `presentacion_slides`; `seed_sync.py --check` pasa; el listado en vivo `https://cc5m5.github.io/CCE-M5/presentacion/` muestra 2026-11-01 tras el redeploy de CI.
- S2: El usuario pidió el "fix del bundle cambiando el pipeline": el bundle HTML de 2026-11-01 debe llegar al build de CI para que `https://cc5m5.github.io/CCE-M5/presentacion/2026-11-01/` muestre la presentación embebida (hoy el iframe 404 porque `presentaciones_html/*` está gitignored y la CI solo copia el directorio vacío). Criterio de aceptación: el workflow de build genera los bundles desde `presentacion_slides` de la seed (una fecha con composición por vez, vía `src/generators/generar_desde_composicion.py --fecha <f>`), la CI pasa, y en el sitio en vivo `https://cc5m5.github.io/CCE-M5/presentaciones_html/2026-11-01_presentacion/index.html` responde 200 (no 404).
- S3: No tocar `web/dist` (build derivado), no commitear `data/db.sqlite3` ni backups, y no ampliar el alcance más allá de seed + pipeline.

## Tasks

- T1 (inline): `seed_sync.py --apply` + validación + commit del seed + push a main. S1. Commits: `69f7460` (fix WAL-consistencia de `_build_canonical_seed`) + commit del seed (ver L4).
- T2 (delegado): `.github/workflows/deploy.yml` — job `build`: instalar dependencias de WeasyPrint (mismo apt que `lint-and-test`) y nuevo paso "Generate presentacion bundles" que itera las fechas con `presentacion_slides` en la seed y ejecuta el generador por fecha; verificar en copia scratch (mktemp) simulando la CI; commit + push. S2. Commit: pendiente.
- T3 (delegado): verificador independiente (risk item 5: CI/deploy): re-ejecuta la simulación scratch en limpio y revisa el diff. S2.

## Log

- L1: "Ejecuta paso 1 y fix del bundle cambiando el pipeline." (usuario)
- L2: Diagnóstico previa investigación: `2026-11-01` existe solo en `data/db.sqlite3` local (gitignored); la CI usa `data/seeds/db.empty.sqlite3` (15 presentaciones, sin 2026-11-01); `presentaciones_html/*` gitignored → los bundles HTML no llegan al build; verificado 404 en vivo en el bundle de 2026-10-25.
- L3: El generador `src/generators/generar_desde_composicion.py --fecha <f>` reconstruye JSON+HTML+PPTX+PDF desde `presentacion_slides` (requiere `PYTHONPATH=src:scripts:.`; PDF vía WeasyPrint puro Python, en `requirements.lock.txt`; PPTX vía python-pptx). 7 fechas tienen composiciones en la BD local: 2026-09-13, 2026-09-20, 2026-10-04, 2026-10-11, 2026-10-18, 2026-10-25, 2026-11-01. `data/lemas/somos_uno.jpg` está versionado; `data/ilustraciones/*.png` está gitignored (el generador degrada con aviso si falta una ilustración).
- L4 (2026-10-31): Descubrimiento — el primer `--apply` produjo un seed incompleto porque `shutil.copy2` copia solo el archivo base y la BD local tiene un WAL sin checkpoint: faltaban las 2 filas borrador de `2026-10-22` y `2026-11-01` quedó `generado` en vez de `publicada`. Fix test-first: RED `test_build_canonical_seed_includes_uncheckpointed_wal_rows` (`assert 1 == 2`) → fix con la API de backup de SQLite en `_build_canonical_seed` (commit `69f7460`) → GREEN: `test_seed_sync.py` 7 passed; suite completa 296 passed. Re-`--apply`: seed fiel a la BD local en todas las tablas de contenido (18 presentaciones, `2026-11-01` id 165 estado `publicada` con 28 slides, 223 `presentacion_slides` totales, runtime tables limpiadas, `PRAGMA integrity_check` ok). `--check` sigue reportando desactualizado solo por las filas de runtime (admin_users, workflow_*) que la fuente tiene y el seed limpia por diseño.
