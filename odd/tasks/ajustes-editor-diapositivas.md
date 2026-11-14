# Ajustes y controles del editor de diapositivas (CCE-M5-Web-Presentaciones)

**Objetivo:** Corregir el error 429 al seleccionar diapositivas y añadir controles de ajuste global (tamaño de letra por parte de la diapositiva), limpieza (canciones de prueba A/B, prefijo «l » en títulos de presentaciones) y manipulación directa por diapositiva (arrastrar imagen y cuadro de texto con el ratón) en el editor de diapositivas.

**Branch:** por decidir (rama de feature si `main` está ocupada; el histórico reciente trabaja directo en `main`).

**Test runner:** `.venv/bin/python -m pytest -q -p no:cacheprovider` (Python) y `npm run build` (Astro, en `web/`).

## Specs

S1. (Bug) «"Demasiadas peticiones desde esta IP. Espera un momento." Aparece al seleccionar cualquier diapositiva, por ejemplo: "http://192.168.68.240:4323/editor-diapositivas/slides/102"»

S2. (Ajuste general) «Poder variar el tamaño de la letra. El tamaño de la letra de cada parte de la diapositiva (título, cuerpo, etc.) debe ser igual para todas las diapositivas. Por ejemplo, si selcciono tamaño 12 en el cuerpo de la diapositiva, se debe cambiar en todas las diapositivas el tamaño del cuerpo. Si selecciono tamaño 24 en los títulos, se debe cambiar en todos los títulos de diapositivas.» Partes: título, subtítulo, cita y cuerpo (contenido). Decisión L2: los tamaños se guardan en la base de datos y se respetan también al generar las presentaciones PPTX/PDF/HTML.

S3. (Ajuste general) «Eliminar las canciones de prueba (canción A y B).»

S4. (Ajuste general) «En los títulos de las Presentaciones, no quiero que se lea "l XXXII Domingo del Tiempo Ordinario", sino "XXXII Domingo del Tiempo Ordinario". Esto aplica a TODAS las presentaciones.»

S5. (Ajuste particular) «Poder variar el tamaño y posición de la imagen, clicando y arrastrando con el ratón en el cuadro de la imagen.» — afecta solo a la diapositiva seleccionada. Decisión L2: posición y tamaño se guardan por diapositiva y se respetan al generar PPTX/PDF/HTML.

S6. (Ajuste particular) «Poder variar el tamaño y posición del cuadro de texto, clicando y arrastrando con el ratón en el cuadro de texto.» — afecta solo a la diapositiva seleccionada. Decisión L2: posición y tamaño se guardan por diapositiva y se respetan al generar PPTX/PDF/HTML.

## Tasks

| ID | Spec | Descripción | Ruta (superficies) | Estado | Commit |
|---|---|---|---|---|---|
| T1 | S1 | Corregir el 429: excluir assets del editor (`__ilustraciones`, `__lema`) del limitador IP y cargar miniaturas con `loading="lazy"` | Inline (padre): `src/web_admin/api.py`, `scripts/editor_diapositivas_server.py` | in_progress | |
| T2 | S2 | Tamaños de letra globales por parte (título, subtítulo, cita, cuerpo): tabla de ajustes + panel en el editor + vista previa + propagación a `pptx_renderer`, `html_renderer`, `pdf_renderer` | Worker 2 (background): `scripts/editor_diapositivas_server.py`, `src/generators/presentacion/`, `src/db_manager.py`, `data/schema_slides.sql`, `data/schema_full.sql`, `tests/unit/` | pending | |
| T3 | S3 | Eliminar las canciones de prueba (Canción A y B) y sus diapositivas auto-creadas: DB viva (con backup), `web/data/canciones.json` regenerado, seed `data/schema.sql` y `data/seeds/db.empty.sqlite3` limpios | Worker 1 (background): `data/schema.sql`, `src/scrapers/`, `scripts/` (limpieza + regeneración), `tests/unit/` | pending | |
| T4 | S4 | Quitar el prefijo «l » de `lecturas.celebracion` en la DB viva y normalizar los dos scrapers (koinonia, ciudadredonda); verificación en todas las presentaciones | Worker 1 (background, tras T3 en la misma sesión): `src/scrapers/`, `scripts/`, `tests/unit/` | pending | |
| T5 | S5 | Arrastrar con el ratón para variar tamaño y posición de la imagen de la diapositiva seleccionada (guardado por diapositiva + generadores) | Worker 3 (tras Worker 2): junto con T6, mismo mecanismo | pending | |
| T6 | S6 | Arrastrar con el ratón para variar tamaño y posición del cuadro de texto de la diapositiva seleccionada (guardado por diapositiva + generadores) | Worker 3 (tras Worker 2): `scripts/editor_diapositivas_server.py`, `src/generators/presentacion/`, `src/db_manager.py`, `src/web_admin/matching_engine.py`, `data/schema_slides.sql`, `data/schema_full.sql`, `tests/unit/` | pending | |
| T7 | S4 | Regenerar TODAS las presentaciones existentes (PPTX/HTML/PDF) con datos limpios y ajustes aplicados; verificación final de la suite completa | Inline (padre) al cerrar, con el código final | pending | |

## Log

L1. «Sigamos mejorando el proyecto de CCE-M5-Web-Presentaciones. Ahora mismo estamos en un momento de mejora del proyecto, me gustaría implementar los siguientes controles en la creación de las diapositivas: 0. Corrección de errores: ahora mismo tengo este fallo que tengo que solucionar "detail    "Demasiadas peticiones desde esta IP. Espera un momento.". Aparece al seleccionar cualquier diapositiva, por ejemplo: "http://192.168.68.240:4323/editor-diapositivas/slides/102" / 1. Ajustes generales, que afectan a todas las diapositivas. 1.1. Poder variar el tamaño de la letra. El tamaño de la letra de cada parte de la diapositiva (título, cuerpo, etc.) debe ser igual para todas las diapositivas. Por ejemplo, si selcciono tamaño 12 en el cuerpo de la diapositiva, se debe cambiar en todas las diapositivas el tamaño del cuerpo. Si selecciono tamaño 24 en los títulos, se debe cambiar en todos los títulos de diapositivas. / 1.2. Eliminar las canciones de prueba (canción A y B). / 1.3. En los títulos de las Presentaciones, no quiero que se lea "l XXXII Domingo del Tiempo Ordinario", sino "XXXII Domingo del Tiempo Ordinario". Esto aplica a TODAS las presentaciones. / 2. Ajustes particulares, que afecten solo una diapositiva que está selccionada. 2.1 Poder variar el tamaño y posición de la imagen, clicando y arrastrando con el ratón en el cuadro de la imagen. / 2.2 Poder variar el tamaño y posición del cuadro de texto, clicando y arrastrando con el ratón en el cuadro de texto.»

L2. Decisión de producto (pregunta del orquestador, respuesta del usuario: opción «Editor + presentaciones generadas»): los controles visuales de S2/S5/S6 se guardan en la base de datos y el generador PPTX/PDF/HTML los respeta al crear las presentaciones que se proyectan (WYSIWYG completo).
