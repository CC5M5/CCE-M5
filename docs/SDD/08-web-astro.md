# 8. Web Astro

## 8.1. Tecnología

- Astro 4.16 (SSG).
- React para componentes interactivos (`BuscadorCanciones`, `FiltroMomentos`, `VisorAcordes`).
- Tailwind CSS para estilos.
- Lucide React para iconos.

## 8.2. Rutas

| Ruta | Descripción |
|---|---|
| `/` | Página principal con presentación más reciente. |
| `/presentacion/` | Listado de presentaciones. |
| `/presentacion/YYYY-MM-DD/` | Presentación específica con enlaces de descarga. |
| `/cancionero/` | Listado alfabético del cancionero. |
| `/cancionero/[slug]/` | Detalle de canción con acordes. |
| `/musicos/` | Listado de hojas de músicos. |
| `/musicos/YYYY-MM-DD/` | Hoja de músicos de una fecha. |
| `/lecturas/YYYY-MM-DD/` | Lecturas de una fecha. |
| `/comentarios/` | Formulario de comentarios. |
| `/sobre/` | Información del proyecto. |

## 8.3. Datos estáticos

- `web/src/lib/db.js` lee JSON de `web/data/`:
  - `canciones.json`
  - `cancion_momentos.json`
  - `presentaciones.json`
  - `comentarios.json`
- Estos JSON se generan con `scripts/export_data_for_web.py`.

## 8.4. Build

- Requiere **Node ≥ 22**. Build verificado con Node 24.22.1 (migración 2026-10-27, `web/dist/` 165 archivos).
- `.nvmrc` fija 22.23.3 como referencia para nvm; el node del sistema (`/usr/bin/node`) también funciona.
- `BASE_PATH` y `SITE_URL` vienen de variables de entorno.
- Local: `BASE_PATH=/`, `SITE_URL=http://<IP_LOCAL>:4321`.
- GitHub Pages: `BASE_PATH=/CCE-M5/`, `SITE_URL=https://cc5m5.github.io`.

## 8.5. Integración con assets de presentaciones

- El workflow de GitHub Actions copia `presentaciones/` y `presentaciones_html/` a `web/public/` antes del build.
- Los enlaces en Astro normalizan rutas absolutas locales a rutas relativas a `BASE_PATH`.

