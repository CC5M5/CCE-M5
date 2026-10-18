# Auditoría Técnica — CCE-M5-Web-Presentaciones (Fase 2)
**Fecha:** 2026-10-18  
**Auditor:** OpenClaw main  
**Ruta del proyecto:** `/home/pciath/proyectos/CCE-M5-Web-Presentaciones`  
**Objetivo:** Segunda pasada de auditoría buscando mejoras más profundas: calidad de código, mantenibilidad, seguridad, assets, tests y deuda técnica oculta.

> **Metodología:** Solo lectura e inspección. No se ha modificado código, base de datos ni configuración.

---

## 1. Resumen Ejecutivo de la Fase 2

La primera auditoría identificó problemas de infraestructura, documentación y reproducibilidad. Esta segunda pasada confirma que existen **problemas estructurales adicionales** que explican por qué el proyecto "falla más de lo que gusta":

1. **Deuda técnica significativa en el código Python**: 20 archivos usan `except Exception:` que silencia errores, 12 archivos hacen magia con `sys.path.insert`, y 14 archivos configuran `logging.basicConfig` por su cuenta.
2. **Archivos legacy/demo sin limpiar**: existen generadores antiguos y scripts de demostración que confunden el pipeline real.
3. **Frontend Astro con dependencias muertas**: `better-sqlite3` y componentes duplicados (`VisorAcordes.astro` y `VisorAcordes.jsx`) que no se usan.
4. **Repositorio muy pesado**: 2,4 GB totales, 783 MB solo en `.git`, archivos binarios grandes trackeados (PPTX/PDF de 5-38 MB).
5. **Seguridad operativa mejorable**: `.env` recién creado pero aún no en `.gitignore`, secretos antiguos posiblemente en historial git.
6. **Tests inexistentes**: solo 3 tests en un archivo.

---

## 2. Hallazgos Detallados

### 2.1. Calidad y mantenibilidad del código Python

#### 2.1.1. Excepciones genéricas silenciadas

**Métrica:** 20 archivos Python contienen `except Exception:`.

Algunos ejemplos problemáticos:
- `src/canciones_manager.py`: el `auto_rebuild_tras_cancion()` se ejecuta dentro de `try/except Exception: pass`, lo que oculta errores de regeneración.
- `src/rebuild_web.py`: todo el rebuild web se atrapa con `except subprocess.CalledProcessError` y `except Exception`, devolviendo solo una línea de error.
- `src/web_admin/workflow_engine.py`: múltiples handlers envuelven todo en `try/except Exception` y devuelven el traceback como string.

**Impacto:** errores reales se ocultan o se degradan a mensajes genéricos. Depurar problemas de generación o publicación es muy difícil.

#### 2.1.2. Magia de `sys.path.insert`

**Métrica:** 12 archivos Python usan `sys.path.insert` o `sys.path.append`.

Esto indica que `src/` no está estructurado como un paquete Python instalable. Cada script debe "hackear" el path para importar módulos.

**Archivos afectados:**
- `scripts/run_admin_api.py`
- `scripts/editor_diapositivas_server.py`
- `scripts/editor_acordes_server.py`
- `scripts/generar_semana.py`
- `src/generators/generar_desde_composicion.py`
- `src/web_admin/workflow_engine.py`
- `src/auto_rebuild_presentaciones.py`

**Impacto:** fragilidad en imports, dificultad para tests, confusión sobre cuál es el entry point correcto.

#### 2.1.3. Logging desordenado

**Métrica:** 14 archivos llaman `logging.basicConfig`.

Esto crea handlers duplicados cuando varios módulos se importan juntos. El resultado es log duplicado o configuraciones que se sobrescriben.

**Archivos afectados:**
- `src/db_manager.py`
- `src/generators/presentacion_fieles.py`
- `src/generators/pdf_musicos.py`
- `src/scrapers/blogspot_scraper.py`
- `src/scrapers/koinonia_scraper.py`
- `src/scrapers/ciudadredonda_scraper.py`
- `src/matching_engine.py`
- `scripts/generar_semana.py`
- `scripts/init_db.py`
- Varios `demo_*.py`

#### 2.1.4. Funciones y archivos muy largos

| Archivo | Líneas |
|---|---|
| `src/generators/presentacion_html.py` | 1534 |
| `scripts/editor_diapositivas_server.py` | 1498 |
| `src/web_admin/workflow_engine.py` | 795 |
| `src/matching_engine.py` | 728 |
| `src/parsers/acordes_parser_v3.py` | 685 |
| `src/web_admin/api.py` | 486 |
| `src/generators/generar_desde_composicion.py` | 402 |

Aunque no hay funciones extremadamente largas, los archivos sí son grandes. `presentacion_html.py` mezcla renderizado HTML, PPTX, PDF, utilidades de texto, colores, ilustraciones y conexión a BD. Esto viola el principio de responsabilidad única.

#### 2.1.5. Código duplicado

- `MOMENTOS_ES`, `MOMENTOS_KEY`, `MOMENTO_A_KEY` aparecen en al menos 3 lugares:
  - `src/generators/presentacion_html.py`
  - `src/web_admin/workflow_engine.py`
  - `scripts/generar_semana.py`
- Funciones de utilidad de fechas y normalización de texto están repetidas entre generadores.
- `_canciones_asignadas()` existe en `src/generators/composicion_catalogo.py`, `src/auto_rebuild_presentaciones.py` y posiblemente en otros módulos.

### 2.2. Archivos legacy, demo y no usados

| Archivo | Estado |
|---|---|
| `src/generators/presentacion_fieles.py` | Legacy, posiblemente no usado |
| `src/generators/presentacion_master.py` | Legacy, referencia a ruta absoluta `/home/pciath/proyectos/CCE-M5-Web-Presentaciones/...` |
| `src/generators/demo_presentacion.py` | Demo |
| `scripts/demo_blogspot.py` | Demo |
| `scripts/demo_koinonia.py` | Demo |
| `scripts/demo_matching.py` | Demo |
| `scripts/demo_pdf_musicos.py` | Demo |
| `scripts/generar_semana.py` | Pipeline antiguo, aún referenciado pero el workflow real pasa por el panel admin |

**Impacto:** riesgo de que alguien ejecute el generador antiguo y sobrescriba una presentación con formato diferente. Dificulta entender cuál es el pipeline real.

### 2.3. Frontend Astro

#### 2.3.1. Dependencias muertas

- `better-sqlite3` está en `web/package.json` pero **no se usa en `web/src/`**. El acceso a datos se hace mediante JSON exportados (`web/data/*.json`).
- `@types/better-sqlite3` también es innecesaria.

#### 2.3.2. Componentes duplicados

- Existen dos `VisorAcordes`:
  - `web/src/components/VisorAcordes.astro` (usado en producción)
  - `web/src/components/VisorAcordes.jsx` (¿legacy? ¿usado en alguna página?)

Esto genera confusión sobre cuál es el componente activo y doble mantenimiento.

#### 2.3.3. Carpeta admin obsoleta en web/src/components/admin

- `web/src/components/admin/` existe pero parece vacía u obsoleta. El admin real vive en `src/web_admin/static/admin/`.

#### 2.3.4. Fetch desde frontend estático

- `web/src/pages/cancionero/index.astro` y `FormularioComentarios.jsx` hacen `fetch()`. En un site estático puro esto puede fallar o causar problemas de CORS/hydration.

### 2.4. Assets, datos y Git

#### 2.4.1. Repositorio muy pesado

| Directorio | Tamaño |
|---|---|
| `.git/` | 783 MB |
| `backups/` | 309 MB |
| `web/dist/` | 146 MB |
| `web/public/` | 142 MB |
| `presentaciones_html/` | 112 MB |
| `data/ilustraciones/` | 66 MB |
| `presentaciones/` | 45 MB |

**Total:** 2,4 GB.

#### 2.4.2. Archivos binarios grandes trackeados

| Archivo | Tamaño |
|---|---|
| `data/templates/274_Domingo_21_06_2026.pptx` | 38 MB |
| `presentaciones/2026-09-13_presentacion.pptx` | 16 MB |
| `presentaciones_html/2026-09-13_presentacion/2026-09-13_presentacion.pdf` | 13 MB |
| `borradores/2026-09-27_presentacion.pdf` | 11 MB |
| `presentaciones/2026-09-20_presentacion.pptx` | 7,1 MB |

**Impacto:** clonado lento, GitHub Pages build más lento, difícil migrar a otro PC.

#### 2.4.3. Duplicación de assets

Los mismos PPTX/PDF aparecen en:
- `presentaciones/`
- `presentaciones_html/`
- `web/public/presentaciones/` (copia build)
- `web/dist/presentaciones/` (output build)

Esto es necesario para el build, pero aumenta el tamaño del repo.

#### 2.4.4. Snapshots sueltos

- `data/db.sqlite3.snapshot.20261008_000845` (2,5 MB)
- `data/db.sqlite3-wal.snapshot.20261008_000845` (218 KB)

Son archivos de backup manuales que ensucian el directorio de datos.

#### 2.4.5. `.gitignore` incompleto

Aunque ignora algunos generados, hay cosas que debería incluir:
- `.env` **no está en `.gitignore`** (acabo de crearlo; si no se añade, se podría commitear accidentalmente).
- `data/*.snapshot.*` no se ignoran.
- `backups/` no se ignora (aunque quizás se quiera mantener).
- `web/public/presentaciones_html/` y `web/public/presentaciones/` ya se ignoran correctamente.

### 2.5. Seguridad

#### 2.5.1. `.env` recién creado

- He movido secretos de systemd a `.env`, pero **`.env` no está en `.gitignore`**. Hay riesgo real de que se suba a git en un commit futuro.

#### 2.5.2. Historial de git

- El `.env` anterior ya contenía un token `ghp_Wp…xgMe` que estaba en el repositorio.
- Es posible que haya secretos antiguos en el historial de commits (necesitaría `git log -S 'ghp_'` para confirmar).

#### 2.5.3. Permisos de archivos

- `.env` tiene permisos `-rw-rw-r--` (grupo puede leer). Debería ser `-rw-------`.

#### 2.5.4. CORS del admin API

- `src/web_admin/api.py` permite orígenes locales (`localhost:4321`, `192.168.68.244:4321/4324`). Para uso doméstico es aceptable, pero no está documentado.

#### 2.5.5. Sin rate limiting

- El login y la API no tienen rate limiting. Con la contraseña por defecto `1234` esto es un riesgo si la IP es accesible.

### 2.6. Tests y calidad

#### 2.6.1. Tests casi inexistentes

- Solo existe `tests/unit/test_auto_rebuild_presentaciones.py` (3 tests).
- No hay tests del parser de acordes, del generador, del admin API, del workflow, ni del build Astro.

#### 2.6.2. Sin linter ni formateador

- No hay `ruff`, `black`, `flake8`, `mypy`, `pre-commit` configurado.
- No hay type checking.
- Esto explica la proliferación de `sys.path.insert`, `except Exception` y duplicaciones.

#### 2.6.3. Scripts auxiliares sueltos

Existen 17 scripts en `scripts/`, algunos con responsabilidades solapadas:
- 4 `demo_*.py`
- 3 `descargar/actualizar_*ilustraciones*.py`
- `generar_semana.py` (legacy)
- `corregir_acordes_desde_origen.py` (one-off?)

### 2.7. Estado de systemd

- `cce-m5-pipeline.service` sigue apareciendo como `failed` aunque está deshabilitado. El estado "failed" persiste hasta que se haga `systemctl --user reset-failed` o se borre el drop-in residual.
- Existe un drop-in `/home/pciath/.config/systemd/user/cce-m5-pipeline.service.d/mission-control-token.conf` con la variable de Mission Control.

---

## 3. Recomendaciones Adicionales (más allá de la Fase 1)

### 3.1. Calidad de código

| # | Acción | Prioridad |
|---|---|---|
| 1 | Crear un paquete Python (`pyproject.toml`) para eliminar `sys.path.insert`. | Alta |
| 2 | Configurar logging centralizado en `src/log_config.py` y quitar `logging.basicConfig` de todos los módulos. | Alta |
| 3 | Refactorizar `src/generators/presentacion_html.py` en módulos más pequeños (`render_html.py`, `render_pptx.py`, `render_pdf.py`, `slides_data.py`). | Media |
| 4 | Extraer constantes compartidas (`MOMENTOS_ES`, `MOMENTOS_KEY`, etc.) a `src/constants.py`. | Media |
| 5 | Reemplazar `except Exception: pass` por excepciones específicas + logging. | Media |

### 3.2. Limpieza de archivos

| # | Acción | Prioridad |
|---|---|---|
| 6 | Mover `presentacion_fieles.py`, `presentacion_master.py`, `demo_presentacion.py` y los `demo_*.py` a una carpeta `archive/` o eliminarlos. | Media |
| 7 | Marcar `scripts/generar_semana.py` como legacy y documentar que no debe usarse. | Media |
| 8 | Eliminar `web/src/components/admin/` si está vacía/u obsoleta. | Baja |
| 9 | Eliminar dependencias `better-sqlite3` y `@types/better-sqlite3` del frontend. | Baja |
| 10 | Decidir cuál `VisorAcordes` se usa y eliminar/renombrar el otro. | Baja |

### 3.3. Seguridad

| # | Acción | Prioridad |
|---|---|---|
| 11 | Añadir `.env` a `.gitignore` inmediatamente. | Crítica |
| 12 | Revisar historial git por secretos expuestos (`git log -S 'ghp_'`). | Alta |
| 13 | Cambiar permisos de `.env` a `600`. | Alta |
| 14 | Cambiar `CCE_ADMIN_DEFAULT_PASSWORD` y `CCE_ADMIN_JWT_SECRET`. | Alta |
| 15 | Añadir rate limiting básico al login (`slowapi` o decorador manual). | Media |

### 3.4. Assets y Git

| # | Acción | Prioridad |
|---|---|---|
| 16 | Añadir `.env`, `data/*.snapshot.*`, `backups/*` a `.gitignore` (o decidir qué backups sí se quieren en git). | Alta |
| 17 | Considerar `git-lfs` para PPTX/PDF grandes o mover templates/historial fuera del repo. | Media |
| 18 | Limpiar snapshots sueltos de `data/`. | Baja |
| 19 | Ejecutar `git filter-repo` o `BFG Repo-Cleaner` si se confirman secretos en el historial. | Baja |
| 20 | Hacer `systemctl --user reset-failed` para limpiar el estado failed del pipeline. | Baja |

### 3.5. Tests y calidad

| # | Acción | Prioridad |
|---|---|---|
| 21 | Instalar `pytest`, `ruff`, `mypy` y añadirlos a `requirements-dev.txt`. | Alta |
| 22 | Añadir tests mínimos del parser de acordes (5-10 casos representativos). | Media |
| 23 | Añadir test de generación del JSON intermedio para una fecha fija. | Media |
| 24 | Configurar `pre-commit` con `ruff` y `mypy`. | Baja |

---

## 4. Conclusión de la Fase 2

El proyecto tiene **más problemas estructurales de los visibles a primera vista**:

- El código Python funciona pero está lejos de ser mantenible: magia de paths, excepciones silenciadas, logging duplicado, archivos muy largos y código duplicado.
- El frontend Astro tiene dependencias muertas y componentes duplicados.
- El repositorio es muy pesado por binarios grandes y duplicaciones.
- La seguridad operativa necesita atención inmediata (`.env` no ignorado, permisos, secretos por defecto).
- Los tests son inexistentes.

**La prioridad inmediata** debería ser:
1. Añadir `.env` a `.gitignore` y ajustar permisos.
2. Revisar historial git por secretos.
3. Crear `pyproject.toml` para eliminar `sys.path.insert`.
4. Configurar logging centralizado.
5. Instalar herramientas de calidad (`ruff`, `mypy`, `pytest`).

Estas acciones son **no destructivas** y mejorarían mucho la estabilidad y la experiencia de migración.

---

## 5. Correcciones Aplicadas (2026-10-18)

Se aplicaron las 6 recomendaciones urgentes/críticas. Todo el trabajo fue no destructivo: no se tocó la base de datos, ni presentaciones generadas, ni servicios en producción.

### 5.1. Seguridad operativa

| Acción | Resultado |
|---|---|
| Revisar `.gitignore` | `.env` ya estaba ignorado. |
| Cambiar permisos de `.env` | `-rw-------` (600). |
| Revisar historial git por secretos | No se encontraron tokens reales (`ghp_` era solo documentación de formato). |
| Limpiar estado failed de systemd | `systemctl --user reset-failed cce-m5-pipeline.service`. Estado actual: sin unidades CCE en failed. |

### 5.2. Paquete Python (`pyproject.toml`)

- Creado `pyproject.toml` con:
  - metadatos del proyecto,
  - dependencias directas (igual que `requirements.txt`),
  - dependencias opcionales `dev` (`pytest`, `ruff`, `mypy`),
  - scripts de consola (`cce-m5-admin-api`, `cce-m5-init-db`, etc.),
  - configuración de `ruff` y `mypy`,
  - configuración de `pytest`.
- Creados `__init__.py` en `src/`, `src/api/`, `src/generators/`, `src/parsers/`, `src/scrapers/` y `src/web_admin/`.
- Instalado el paquete en modo editable en el `.venv` del proyecto.
- Validación: imports principales funcionan sin `sys.path.insert`.

### 5.3. Logging centralizado

- Creado `src/log_config.py` con `get_logger()` y configuración de root logger única.
- Reemplazados `logging.basicConfig` en módulos activos:
  - `src/db_manager.py`
  - `src/matching_engine.py`
  - `src/generators/pdf_musicos.py`
  - `src/scrapers/blogspot_scraper.py`
  - `src/scrapers/koinonia_scraper.py`
  - `src/scrapers/ciudadredonda_scraper.py`
- Quedan pendientes los archivos legacy/demo: `presentacion_fieles.py`, `demo_presentacion.py` y scripts `demo_*.py`.

### 5.4. Herramientas de calidad

- Creado `requirements-dev.txt` con `pytest`, `ruff`, `mypy`.
- Instalados en `.venv`:
  - `pytest 9.1.1`
  - `ruff 0.17.1`
  - `mypy 2.4.0`
- Tests existentes pasan: `3 passed in 0.08s`.
- `ruff check` en archivos modificados: solo quedan 2 advertencias menores preexistentes (`SIM102` en ciudadredonda, `E741` en blogspot).
- `mypy` detecta 20 errores preexistentes en `matching_engine.py`, `koinonia_scraper.py` y `ciudadredonda_scraper.py`; no se introdujeron en esta corrección.

### 5.5. Validación final

- `python3 -m pytest tests/ -q` → 3 passed.
- `systemctl --user list-units --failed | grep -i cce` → sin unidades en failed.
- Imports principales funcionan desde el paquete editable sin `sys.path.insert`.

### 5.5. Mejoras adicionales aplicadas (B, C y scripts)

#### 5.5.1. B: URLs hardcoded parametrizadas

- `src/web_admin/api.py`: los orígenes CORS ya no están hardcoded. Se cargan desde la variable de entorno `ADMIN_CORS_ORIGINS` (separados por comas) y se combinan con los orígenes locales por defecto.
- Añadida `ADMIN_CORS_ORIGINS=http://192.168.68.244:4321,http://192.168.68.244:4324` al `.env`.
- Los mensajes informativos de `scripts/editor_diapositivas_server.py` y `scripts/editor_acordes_server.py` siguen siendo documentación local; no son configuración real.

#### 5.5.2. C: `__init__.py` verificados

- Revisados todos los directorios bajo `src/`.
- Los únicos sin `__init__.py` son `src/web_admin/static/` y `src/web_admin/static/admin/` (contenido estático) y `src/cce_m5_web_presentaciones.egg-info/` (metadata de setuptools).
- **No se requieren cambios**.

#### 5.5.3. Limpieza de `sys.path.insert` en scripts

- Eliminados todos los `sys.path.insert` de `src/` y `scripts/`.
- Scripts corregidos:
  - `scripts/run_admin_api.py`
  - `scripts/editor_diapositivas_server.py`
  - `scripts/editor_acordes_server.py`
  - `scripts/init_db.py`
  - `scripts/generar_semana.py` (legacy, pero corregido)
  - `scripts/corregir_acordes_desde_origen.py`
  - `scripts/demo_koinonia.py`
  - `scripts/demo_matching.py`
  - `scripts/demo_pdf_musicos.py`
- Los imports ahora usan el paquete editable instalado en `.venv`.

#### 5.5.4. Limpieza frontend

- Eliminadas dependencias `better-sqlite3` y `@types/better-sqlite3` de `web/package.json` (no se usaban en `web/src/`).
- Eliminada carpeta vacía `web/src/components/admin/`.
- Verificado que `VisorAcordes.jsx` y `VisorAcordes.astro` se usan en páginas distintas, así que se mantienen ambos.

### 5.6. Validación final

- `grep -rln 'sys.path.insert' src/ scripts/` → **sin resultados**.
- `python3 -m py_compile scripts/*.py` → **OK**.
- `python3 -m pytest tests/ -q` → **3 passed in 0.03s**.
- `ruff check` sigue reportando 579 errores preexistentes; no se aplican autofixes masivos por precaución.
- `mypy src/` reporta 66 errores preexistentes.

### 5.7. Próximos pasos recomendados

Quedan tareas de media/baja prioridad:

1. Refactorizar `src/generators/presentacion_html.py` en módulos más pequeños.
2. Extraer constantes compartidas a `src/constants.py`.
3. Reemplazar `except Exception: pass` por excepciones específicas.
4. Mover archivos legacy/demo a `archive/`.
5. Añadir rate limiting al login del admin.
6. Aumentar cobertura de tests.
7. Considerar `git-lfs` para PPTX/PDF grandes.

---

*Informe actualizado tras aplicar correcciones y mejoras adicionales.*
