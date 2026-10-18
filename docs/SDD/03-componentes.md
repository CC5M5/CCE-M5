# 3. Componentes del Sistema

## 3.1. Módulos Python (`src/`)

| Módulo | Responsabilidad | Entradas | Salidas |
|---|---|---|---|
| `src/parsers/acordes_parser_v3.py` | Parsear `letra_con_acordes` en `estructura_json`, `html_visual`, `letra_sin_acordes` y `tono`. | Texto con acordes. | Estructura de líneas + HTML. |
| `src/canciones_manager.py` | CRUD de canciones + sincronización de momentos + regeneración de derivados. | Datos de canción. | Fila en `canciones` + `cancion_momentos`. |
| `src/auto_rebuild_presentaciones.py` | Crear slides `cancion_<id>` y regenerar presentaciones futuras afectadas. | `cancion_id`. | Slides + bundles actualizados. |
| `src/rebuild_web.py` | Exportar SQLite a JSON, `npm run build` y servir `web/dist` en 4321. | Cambios en BD. | `web/dist/` actualizado. |
| `src/matching_engine.py` | Proponer canciones según lecturas y momentos. | Lectura + configuración. | Ranking por momento. |
| `src/generators/composicion_catalogo.py` | Proponer y guardar la composición de slides para un domingo. | `fecha_domingo`, `canciones_json`. | Filas en `presentacion_slides`. |
| `src/generators/presentacion_html.py` | Renderizar presentación a JSON/HTML/PPTX/PDF desde composición. | `presentacion_slides` + lecturas. | Bundle en `presentaciones_html/`. |
| `src/generators/generar_desde_composicion.py` | Orquestar la generación final a partir de la composición guardada. | Fecha. | Bundle completo. |
| `src/generators/pdf_musicos.py` | Generar hoja de músicos A4 con acordes posicionados. | `canciones_json`. | PDF en `presentaciones/`. |
| `src/scrapers/koinonia_scraper.py` | Extraer lecturas de servicioskoinonia.org. | Fecha. | Diccionario compatible con `lecturas`. |
| `src/scrapers/ciudadredonda_scraper.py` | Fallback de lecturas. | Fecha. | Diccionario compatible con `lecturas`. |
| `src/web_admin/api.py` | API REST FastAPI del panel admin. | Peticiones HTTP. | JSON + UI estática. |
| `src/web_admin/workflow_engine.py` | Handlers de cada paso del workflow manual. | Workflow + payload. | Estado actualizado + logs. |
| `src/web_admin/database.py` | Acceso a datos de usuarios, workflows y backups. | SQL/parámetros. | Filas del admin. |
| `src/web_admin/auth.py` | JWT + bcrypt para login. | Credenciales. | Token / perfil. |

## 3.2. Scripts (`scripts/`)

| Script | Uso | Frecuencia |
|---|---|---|
| `run_admin_api.py` | Lanzar Admin API. | systemd |
| `editor_diapositivas_server.py` | Lanzar editor de diapositivas. | systemd |
| `editor_acordes_server.py` | Lanzar editor de acordes. | Manual |
| `export_data_for_web.py` | Exportar SQLite → JSON en `web/data/`. | Antes de cada build |
| `sync_presentaciones_html.py` | Copiar `presentaciones/` y `presentaciones_html/` a `web/public/`. | Build de Astro |
| `generar_semana.py` | Pipeline end-to-end antiguo. | **Legacy** |
| `importar_slides_catalogo.py` | Importar catálogo de slides desde `data/schema_slides.sql`. | Inicial / reset |
| `init_db.py` | Crear `db.sqlite3` desde `schema.sql`. | Inicial |

## 3.3. Aplicación web (`web/`)

| Directorio/Archivo | Responsabilidad |
|---|---|
| `web/src/pages/` | Rutas Astro: index, cancionero, presentación, músicos, lecturas, comentarios, sobre. |
| `web/src/components/` | Componentes React: `BuscadorCanciones`, `FiltroMomentos`, `VisorAcordes`. |
| `web/src/lib/db.js` | Carga de JSON exportado + funciones de acceso a datos. |
| `web/src/layouts/Layout.astro` | Layout común, meta tags, navegación, footer. |
| `web/src/styles/global.css` | Estilos globales incluyendo visor de acordes y colores litúrgicos. |
| `web/data/` | JSON exportados de SQLite. |
| `web/public/` | Assets estáticos y copias de `presentaciones/` + `presentaciones_html/`. |

## 3.4. Generadores de presentaciones

El sistema ha tenido varios generadores históricos. El actual y único que debe usarse es:

- **`src/generators/generar_desde_composicion.py`** → orquesta.
- **`src/generators/presentacion_html.py`** → renderiza JSON/HTML/PPTX/PDF.

Los demás (`presentacion_fieles.py`, `presentacion_master.py`, `generar_semana.py`) son **legacy** y deberían archivarse o eliminarse en una fase de limpieza.

