# 5. Pipeline Semanal

## 5.1. Visión general

El flujo semanal se ejecuta desde el panel de administración (`/admin/`). Es **manual paso a paso**: el usuario debe pulsar *Validar y continuar* en cada paso.

## 5.2. Pasos del workflow

| # | Paso | Descripción | Handler |
|---|---|---|---|
| 1 | `init` | Crear workflow para una fecha. | `handle_init` |
| 2 | `fetch_lectures` | Obtener lecturas de Koinonia → Ciudad Redonda → manual. | `handle_fetch_lectures` |
| 3 | `verify_lectures` | Mostrar lecturas al usuario para confirmar/corregir. | `handle_verify_lectures` |
| 4 | `propose_songs` | Generar propuestas con `MatchingEngine`. | `handle_propose_songs` |
| 5 | `verify_songs` | Seleccionar/ajustar canciones por momento. | `handle_verify_songs` |
| 6 | `generate_assets` | Generar PPTX, PDFs y HTML Reveal.js. | `handle_generate_assets` |
| 7 | `publish` | Exportar JSON, build Astro y subir a GitHub. | `handle_publish` |
| 8 | `done` | Workflow completado. | — |

## 5.3. Reglas del matching

- Se extraen temas de las lecturas.
- Para cada momento se filtran canciones por `cancion_momentos`.
- Se calcula un score con `data/matching_config.json`.
- Si no hay propuestas por matching, se usa fallback por momento litúrgico y luego cualquier canción disponible.
- Momentos explícitamente vacíos se respetan (no se fuerza matching).

## 5.4. Generación de assets

1. `asegurar_composicion()` crea/actualiza `presentacion_slides`.
2. `GeneradorDesdeComposicion().generar_desde_presentacion(fecha)` genera el bundle.
3. Se copian archivos a `presentaciones/` y `presentaciones_html/`.
4. Se actualiza `presentaciones.estado = 'generado'`.

## 5.5. Publicación

1. `export_data_for_web.py` genera `web/data/*.json`.
2. `sync_presentaciones_html.py` copia assets a `web/public/`.
3. `npm run build` (Node ≥ 22) genera `web/dist/`.
4. `git add` + `git commit` + `git push origin main`.
5. GitHub Actions ejecuta `.github/workflows/deploy.yml` y publica en Pages.

## 5.6. Backups automáticos

Antes de regenerar una fecha existente, el workflow copia los archivos actuales a `backups/YYYY-MM-DD_TIMESTAMP/` y registra el backup en `workflow_backups`.

