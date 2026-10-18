# Auditoría Técnica — CCE-M5-Web-Presentaciones
**Fecha:** 2026-10-18  
**Auditor:** OpenClaw main  
**Ruta del proyecto:** `/home/pciath/proyectos/CCE-M5-Web-Presentaciones`  
**Objetivo:** Diagnosticar los puntos técnicos que provocan inestabilidad, preparar el proyecto para migración a otro PC y proponer mejoras en la documentación de diseño de software (SDD).

> **Metodología:** Solo lectura e inspección. No se ha modificado código, base de datos ni configuración.

---

## 1. Resumen Ejecutivo

El proyecto funciona **porque ha sido curado a mano semana a semana**, no porque la arquitectura sea robusta. Existen problemas críticos en cuatro áreas principales:

1. **Confusión en puertos/servicios**: el panel de administración y el editor de diapositivas tienen asignaciones de puerto inconsistentes en systemd, scripts y skill.
2. **Deuda técnica creciente**: múltiples generadores (`presentacion_fieles`, `presentacion_master`, `presentacion_html`, `generar_desde_composicion`, `generar_semana`) coexisten, algunos aparentemente sin uso, sin un único pipeline claro.
3. **Dependencia dura del entorno**: rutas absolutas, versiones de Node hardcodeadas, secretos en unidades systemd y sin gestión reproducible del entorno Python.
4. **Documentación y especificaciones desfasadas**: las specs mantienen decisiones obsoletas (Mission Control, formato 16:9, OpenCode, PostgreSQL futuro) que ya no reflejan el sistema real (4:3, panel web propio, SQLite).

**Riesgo principal para la migración:** si se copia el proyecto a otro PC tal cual, varios servicios no arrancarán, el panel admin no servirá y el workflow semanal se romperá por la incompatibilidad entre el servicio `cce-m5-pipeline.service` (apunta a un script de Mission Control que ya no se usa) y el panel web propio.

---

## 2. Hallazgos Críticos (por qué "falla más de lo que gusta")

### 2.1. Caos de puertos y servicios systemd

| Servicio | Puerto esperado | Puerto real / fallo |
|---|---|---|
| `cce-m5-admin.service` | 4323 (skill) | **4324** en systemd, y el proceso **falla en loop** (`status=3`) |
| `cce-m5-editor-diapositivas.service` | 4324 (skill) | **4323** en systemd, y el proceso **falla en loop** (`status=1`) |
| `cce-m5-web.service` | 4321 | **no existe la unidad systemd**; el puerto 4321 lo sirve un `python3 -m http.server` lanzado manualmente por `src/rebuild_web.py` |
| `cce-m5-pipeline.service` | — | **Falló** (`failed`). Apunta a un trigger de Mission Control (`MC_URL=http://192.168.68.244:4000`) cuando el workflow real ya pasa por el panel web propio |

**Evidencia:**
```text
● cce-m5-admin.service ... Active: activating (auto-restart) (Result: exit-code)
● cce-m5-editor-diapositivas.service ... Active: activating (auto-restart) (Result: exit-code)
LISTEN 0 5 0.0.0.0:4321 users:(("python3",pid=3784437,fd=3))
```

**Impacto:**
- En el nuevo PC, si se replican estos units, el admin panel y el editor de diapositivas no funcionarán.
- El servicio web (4321) no se reinicia automáticamente al arrancar el equipo; si muere, la web local desaparece hasta el próximo rebuild manual.
- El trigger semanal de Mission Control sigue configurado aunque el workflow real ya no lo usa.

### 2.2. Múltiples generadores y falta de pipeline único

Se han detectado al menos **5 generadores**:

1. `src/generators/presentacion_fieles.py`
2. `src/generators/presentacion_master.py`
3. `src/generators/presentacion_html.py` (actual, usado por `generar_desde_composicion`)
4. `src/generators/generar_desde_composicion.py` (orquesta la generación final)
5. `scripts/generar_semana.py` (pipeline end-to-end antiguo)

Además hay `demo_presentacion.py` y `pdf_musicos.py`. Esto genera:
- Duplicidad de lógica.
- Riesgo de que alguien ejecute el script antiguo y sobrescriba una presentación con un formato distinto.
- Dificultad para saber cuál es la fuente de verdad del pipeline semanal.

### 2.3. Hardcodeo de rutas, versiones y secretos

**Rutas absolutas hardcodeadas:**
- `/home/pciath/.nvm/versions/node/v22.23.3/bin` en `src/rebuild_web.py`, `cce-m5-admin.service`, `cce-m5-editor-diapositivas.service`.
- `/home/pciath/proyectos/CCE-M5-Web-Presentaciones` en múltiples módulos.
- `192.168.68.244` en CORS, `SITE_URL` y frontend.

**Secretos en texto plano en unidades systemd:**
```ini
Environment="CCE_ADMIN_JWT_SECRET=cambia-esta-clave-en-produccion"
Environment="CCE_ADMIN_DEFAULT_USER=rafael.torres"
Environment="CCE_ADMIN_DEFAULT_PASSWORD=1234"
```

**Versiones de Node fijas y no documentadas:**
- El build Astro requiere Node 22.23.3; Node 24 rompe Astro 4.16/4.19.
- `.nvmrc` no está en la raíz del proyecto; el usuario debe saber manualmente qué versión instalar.

### 2.4. Inconsistencias en la base de datos y migraciones

- `data/schema.sql` no incluye `cancion_momentos`, `html_visual`, `estructura_json`, `schema_version`, ni las tablas del admin (`admin_users`, `workflow_runs`, `workflow_logs`, `workflow_backups`).
- Las tablas reales existen en `db.sqlite3` pero están dispersas entre `schema.sql`, `schema_slides.sql` y creaciones ad-hoc en `init_admin_schema()`.
- No existe un sistema de migraciones (p. ej. Alembic, yoyo, o un simple `migrations/`). Al migrar a otro PC, recrear la BD desde los scripts actuales generará una base de datos incompleta.

### 2.5. Tests casi inexistentes y entorno no reproducible

- Únicamente hay **1 archivo de test**: `tests/unit/test_auto_rebuild_presentaciones.py` (3 tests).
- No hay tests de los generadores de PPTX/HTML/PDF, del parser de acordes, del panel admin, del build Astro ni del workflow.
- `pytest` no está instalado en el Python del sistema; no se sabe si está en `.venv` sin inspeccionar `requirements.txt` (no figura).
- `requirements.txt` es mínima y no versiona dependencias: `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, etc. Esto hace que dos instalaciones del proyecto en fechas distintas puedan tener versiones incompatibles.

### 2.6. Frontend Astro: dependencias, cache y rutas

- `web/package.json` usa `astro@^4.16.19` y fija `node>=20`, pero el build real necesita Node 22.23.3.
- El `db.js` de Astro hace `cache = null` de por vida; si el JSON exportado cambia mientras corre el dev server, no se recarga.
- Las rutas en `index.astro` hacen `.replace(/^.*presentaciones_html\//, ...)` asumiendo rutas locales; si `BASE_PATH` cambia o el path no contiene `presentaciones_html/`, el enlace falla.
- El build en GitHub Actions hace `rm -rf ./src/pages/admin ./src/pages/admin.astro` cada vez, lo cual es una solución temporal que ensucia el build.

### 2.7. Documentación y especificaciones obsoletas

Las specs en `/specs/` contienen decisiones que ya no se aplican:

| Spec | Estado real | Problema |
|---|---|---|
| `00-proyecto.md` | Formato 16:9 | El sistema ahora genera **4:3**. |
| `02-arquitectura.md` | Mission Control + OpenCode | El workflow real usa panel web propio (`web_admin`) y OpenClaw main. |
| `02-arquitectura.md` | SQLite → PostgreSQL futuro | Sigue en SQLite; no hay plan de migración real. |
| `03-datos.md` | `momento_liturgico` 1:N | El modelo real es N:M (`cancion_momentos`) y el campo `momento_liturgico` quedó obsoleto. |
| `06-web.md` | Comentarios vía GitHub Issues API | No hay evidencia de implementación; `comentarios.json` parece mock/vacío. |
| `09-diapositivas.md` | Puerto 4323 editor | systemd usa 4323 para editor; skill dice 4323 editor y 4324 admin, pero el admin API real corre en 4323. |

### 2.8. Gestión de assets e ilustraciones descontrolada

- `data/ilustraciones/catalogo.json` y `catalogo_extendido.json` coexisten; no está claro cuál es el maestro.
- Hay scripts sueltos para descargar ilustraciones (`descargar_ilustraciones.py`, `descargar_mas_ilustraciones.py`, `actualizar_catalogo_ilustraciones.py`).
- `web/public/fano_preview.png` (916 KB) está trackeada en git aunque es un asset generado.
- `.gitignore` intenta ignorar `data/ilustraciones/*.png`, pero hay muchos PNGs probablemente ya trackeados.

---

## 3. Áreas Técnicas a Mejorar

### 3.1. Backend / Python

1. **Unificar el pipeline semanal**: eliminar `generar_semana.py` antiguo o marcarlo como legacy; dejar `generar_desde_composicion.py` + `workflow_engine.py` como única ruta.
2. **Migraciones de base de datos**: crear un `migrations/` con los esquemas completos (base + slides + admin + cancion_momentos + columnas añadidas) o un único `schema_full.sql` que reproduzca la BD real.
3. **Eliminar imports `sys.path.insert`**: reestructurar `src` como paquete Python (`pyproject.toml` o `setup.py`) para evitar magia de paths.
4. **Logging centralizado y configurado**: actualmente cada módulo configura `logging.basicConfig`, lo que puede duplicar handlers.
5. **Versionado de dependencias**: congelar `requirements.txt` y añadir `requirements-dev.txt` con `pytest`, `ruff`, `mypy`.
6. **Añadir tests mínimos**: parser de acordes, composición de slides, generación de JSON intermedio y endpoints críticos del admin.

### 3.2. Frontend / Astro

1. **Fijar Node 22.23.3**: añadir `.nvmrc` y documentar que Node 24 no funciona.
2. **Refrescar cache de `db.js`**: invalidar el cache cuando los JSON cambian, o leerlos en cada build (Astro ya lo hace, el problema es en dev).
3. **Evitar `rm -rf` en el build de CI**: separar la página de admin en una ruta que Astro excluya limpiamente o moverla fuera de `web/src/pages`.
4. **Revisar todas las rutas hardcodeadas**: `192.168.68.244`, `/home/pciath/...` y `BASE_PATH` deben venir de variables de entorno.
5. **Optimizar imágenes**: `fano_preview.png` y similares deben ir a git-lfs o generarse en build.

### 3.3. Infraestructura y despliegue

1. **Corregir los puertos systemd**:
   - `cce-m5-admin.service` → puerto **4323**.
   - `cce-m5-editor-diapositivas.service` → puerto **4324**.
2. **Crear unidad para el servicio web en 4321**: no depender de un `http.server` lanzado manualmente desde `rebuild_web.py`.
3. **Eliminar o desactivar `cce-m5-pipeline.service`**: el workflow ya no pasa por Mission Control.
4. **Gestionar secretos fuera de systemd**: usar `.env` (no commiteado) + `python-dotenv`, o variables de entorno inyectadas por el usuario.
5. **Añadir healthchecks**: cada servicio debe exponer `/health` y systemd usar `ExecStartPost`/`Restart=` con logs claros.

### 3.4. Datos y reproducibilidad

1. **Esquema único de verdad**: unificar `schema.sql` + `schema_slides.sql` + tablas admin en `schema_full.sql` con `PRAGMA foreign_keys` y `WAL`.
2. **Backup automático de la BD**: antes de cualquier operación destructiva (importar catálogo, rebuild, etc.).
3. **Borrar snapshots sueltos**: hay archivos `data/db.sqlite3.snapshot.*` y `.wal.snapshot.*` que ensucian el repo.
4. **Auditoría de presentaciones**: `presentaciones/` y `presentaciones_html/` crecen mucho (2,4 GB totales). Establecer una política de archivado o git-lfs.

### 3.5. Seguridad

1. **JWT secret por defecto visible en systemd**.
2. **Contraseña por defecto `1234`** hardcodeada en la unidad.
3. **CORS permite `localhost:4321` y la IP local**; en producción pública debería restringirse.
4. **No hay rate limiting** en el login ni en la API.
5. **La BD SQLite contiene usuarios y contraseñas hasheadas**; aunque no es grave, el fichero no debería publicarse en GitHub Pages (el workflow copia `data/db.sqlite3`? No, exporta a JSON, pero conviene verificar que no queda expuesto en `web/dist`).

---

## 4. Mejoras al SDD (Software Design Description)

El SDD actual está fragmentado en `specs/`, `README.md` y la skill `cce-m5-presentacion-generator`. Para que sea útil y mantenible se recomienda reescribirlo con esta estructura:

### 4.1. Estructura propuesta del SDD

```
docs/SDD/
├── 01-introduccion.md              # Alcance, stakeholders, definiciones
├── 02-arquitectura-actual.md       # Diagrama real: servicios, BD, flujo
├── 03-componentes.md               # src/: responsabilidad de cada módulo
├── 04-modelo-datos.md              # Esquema unificado y relaciones
├── 05-pipeline-semanal.md          # Flujo admin panel paso a paso
├── 06-generacion-presentaciones.md # JSON intermedio, PPTX, HTML, PDF
├── 07-cancionero-y-acordes.md      # Parser, html_visual, momentos
├── 08-web-astro.md                 # Build, rutas, base_path, Node
├── 09-despliegue.md                # systemd, GitHub Actions, secrets
├── 10-migracion-nuevo-pc.md        # Checklist de migración
└── 11-operacion-y-troubleshooting.md # Logs, healthchecks, FAQs
```

### 4.2. Contenido mínimo que debe incluir

1. **Diagrama de arquitectura actualizado** que refleje:
   - Panel admin propio (FastAPI + HTML estático).
   - Editor de diapositivas (Flask, 4324).
   - Cancionero web (Astro en 4321).
   - Editor de acordes (Flask, 4322).
   - SQLite como única base de datos.
   - GitHub Pages como destino público.
2. **Tabla de puertos y servicios canonizada**, con los units systemd correctos.
3. **Decisión explícita del formato 4:3** y por qué se abandonó el 16:9 de las specs originales.
4. **Contrato del JSON intermedio** generado en `presentaciones_html/YYYY-MM-DD_presentacion/*.json`.
5. **Flujo de datos del parser de acordes**: entrada `letra_con_acordes` → `estructura_json` → `html_visual` → `letra_sin_acordes`.
6. **Reglas del catálogo de slides**: `slides_tipos`, `slides`, `presentacion_slides`, `subtipo`, `es_default`.
7. **Procedimiento de migración de PC**: lista de dependencias, versiones, variables de entorno y orden de arranque.

### 4.3. Archivos a actualizar o depurar

- **Borrar/actualizar** `specs/02-arquitectura.md`, `specs/03-datos.md`, `specs/05-presentacion.md` y `specs/06-web.md`.
- **Mantener vivos** `specs/01-requisitos.md` y `specs/07-cancionero.md` actualizándolos.
- **Mover** la skill `cce-m5-presentacion-generator` a que referencie el SDD en lugar de duplicar lógica.
- **Añadir** un `CHANGELOG.md` o `DECISIONES.md` para registrar por qué se tomaron decisiones (4:3, Node 22, abandono de Mission Control).

---

## 5. Recomendaciones para la Migración a otro PC

Antes de copiar el repositorio, se recomienda ejecutar estas acciones en el PC origen y destino:

### 5.1. Preparar el PC origen

1. **Congelar dependencias**:
   ```bash
   cd /home/pciath/proyectos/CCE-M5-Web-Presentaciones
   .venv/bin/python -m pip freeze > requirements.lock.txt
   echo "22.23.3" > web/.nvmrc
   ```
2. **Limpiar el repo**:
   - Mover snapshots sueltos de `data/` a `backups/` o eliminarlos.
   - Borrar `__pycache__`, `web/dist`, `web/node_modules`.
   - Verificar que `data/db.sqlite3` no incluya información sensible no intencionada.
3. **Exportar un dump de la BD**:
   ```bash
   .venv/bin/python - <<'PY'
   import sqlite3, json
   conn = sqlite3.connect('data/db.sqlite3')
   schema = ''.join(row[1] for row in conn.execute("SELECT * FROM sqlite_master WHERE sql IS NOT NULL"))
   open('data/db_schema_full.sql','w').write(schema)
   PY
   ```
4. **Documentar secretos**: listar qué variables de entorno son necesarias (`CCE_ADMIN_JWT_SECRET`, `CCE_ADMIN_DEFAULT_PASSWORD`, IP local, etc.).

### 5.2. Setup en el PC destino

1. Instalar Node 22.23.3 (via nvm) y Python 3.13.
2. Clonar el repo y crear `.venv`:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock.txt
   ```
3. Instalar dependencias Astro:
   ```bash
   cd web
   npm install
   ```
4. Restaurar base de datos desde `data/db.sqlite3` (o schema + datos).
5. Copiar las unidades systemd y **corregir puertos**:
   - `cce-m5-admin.service` → puerto 4323.
   - `cce-m5-editor-diapositivas.service` → puerto 4324.
   - Crear `cce-m5-web.service` para servir `web/dist` en 4321.
6. Ejecutar un pipeline de prueba con una fecha pasada (modo borrador) antes de tocar datos reales.

---

## 6. Plan de Acción Priorizado

### Fase 0 — Estabilidad inmediata (antes de migrar)

| # | Acción | Prioridad |
|---|---|---|
| 1 | Corregir puertos en systemd (`admin→4323`, `editor→4324`). | Crítica |
| 2 | Crear unidad systemd para el servidor web en 4321. | Crítica |
| 3 | Mover secretos de systemd a `.env` + `python-dotenv`. | Alta |
| 4 | Desactivar/eliminar `cce-m5-pipeline.service` de Mission Control. | Alta |
| 5 | Congelar `requirements.txt` y añadir `.nvmrc` con Node 22.23.3. | Alta |

### Fase 1 — Documentación y reproducibilidad

| # | Acción | Prioridad |
|---|---|---|
| 6 | Crear `docs/SDD/` con la estructura propuesta. | Alta |
| 7 | Generar `schema_full.sql` que reproduzca la BD real. | Alta |
| 8 | Escribir `docs/MIGRACION.md` paso a paso. | Media |
| 9 | Actualizar `specs/` marcando qué decisiones están obsoletas. | Media |

### Fase 2 — Calidad y limpieza

| # | Acción | Prioridad |
|---|---|---|
| 10 | Eliminar o renombrar generadores no usados. | Media |
| 11 | Refactorizar `src` como paquete Python (`pyproject.toml`). | Media |
| 12 | Añadir tests mínimos para parser, composición y admin. | Media |
| 13 | Limpiar snapshots, `__pycache__` y assets grandes del repo. | Media |

### Fase 3 — Robustez

| # | Acción | Prioridad |
|---|---|---|
| 14 | Añadir `/health` a cada servicio y healthchecks systemd. | Baja-Media |
| 15 | Implementar rate limiting y CORS restringido. | Baja |
| 16 | Automatizar backups de la BD antes de operaciones destructivas. | Baja |

---

## 7. Conclusión

El proyecto CCE-M5-Web-Presentaciones **no está roto en su funcionalidad principal** (genera presentaciones semanales y publica en GitHub Pages), pero sí tiene una **arquitectura operativa frágil** que explica por qué "falla más de lo que gusta":

- Los servicios locales no están bien atados (puertos mezclados, web sin unidad systemd, trigger de Mission Control obsoleto).
- La falta de un SDD unificado y actualizado provoca que cada sesión tenga que redescubrir cómo funciona el sistema.
- La deuda técnica acumulada (múltiples generadores, rutas absolutas, tests insuficientes) hace que cualquier cambio sea arriesgado.

**La migración a otro PC es factible**, pero requiere primero estabilizar la configuración de servicios, documentar el entorno y congelar dependencias. Si se migra "tal cual", es muy probable que el panel de administración, el editor de diapositivas y el workflow semanal no funcionen.

---

*Fin del informe.*
