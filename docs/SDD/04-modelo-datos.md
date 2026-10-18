# 4. Modelo de Datos

> **Fuente de verdad:** `data/schema_full.sql` (esquema completo exportado desde `data/db.sqlite3`). Los archivos `data/schema.sql` y `data/schema_slides.sql` son parciales y se mantienen por compatibilidad histórica.

## 4.1. Entidades principales

### `lecturas`
- Datos de la celebración de un domingo.
- Campos clave: `fecha`, `domingo`, `temporada`, `ciclo`, `color_liturgico`, `primera_lectura_*`, `salmo_*`, `segunda_lectura_*`, `evangelio_*`.
- `color_liturgico` aplica el color visual en la presentación final.

### `canciones`
- Cancionero escolapio.
- Campos clave:
  - `titulo`, `titulo_url` (slug).
  - `letra_con_acordes` (fuente original).
  - `letra_sin_acordes` (derivado).
  - `estructura_json` (representación parseada).
  - `html_visual` (HTML con acordes posicionados).
  - `tono`, `temas`, `referencias_biblicas`, `enlace_audio`.
- El campo `momento_liturgico` está en desuso; el modelo real es N:M vía `cancion_momentos`.

### `cancion_momentos`
- Relación N:M entre canciones y momentos litúrgicos.
- `momento_liturgico` incluye: `entrada`, `acto penitencial`, `gloria`, `salmo`, `aleluya`, `evangelio`, `credo`, `ofertorio`, `santo`, `padre_nuestro`, `paz`, `comunion`, `maria`, `despedida`, `general`.
- Normalización: `acto_penitencial` se trata como `perdon` en generación.

### `presentaciones`
- Presentación semanal.
- `fecha_domingo`, `lectura_id`, `canciones_json`, `estado`.
- Estados reales: `generado`, `publicada`, `publicado`.
- Rutas: `ruta_pptx`, `ruta_pdf_fieles`, `ruta_pdf_musicos`, `ruta_web`.

### `slides_tipos`
- Tabla de dominio con los tipos canónicos de diapositiva.
- Orden litúrgico fijo.

### `slides`
- Catálogo maestro de diapositivas.
- Clave por `(tipo, subtipo)`.
- `subtipo` puede ser `general`, `texto_fijo`, `cancion_<id>`, o variantes específicas.
- `es_default` indica la variante por defecto para un `(tipo, subtipo, color_liturgico)`.

### `presentacion_slides`
- Composición concreta de una presentación.
- Cada fila apunta a `slides.id` o es personalizada (`personalizado=1`).
- Orden por `numero`, activación por `activo`.

## 4.2. Formatos JSON

- **lecturas:** El scraper y el admin panel generan un diccionario con citas y textos completos. Ejemplo:
  ```json
  {
    "fecha": "2026-09-13",
    "temporada": "Tiempo Ordinario",
    "domingo": "XXIV",
    "color_liturgico": "verde",
    "primera_lectura": {
      "cita": "Eclo 27,30-28,7",
      "texto": "El que vigila su boca..."
    },
    "salmo": {
      "cita": "Sal 102(103)",
      "texto": "El Señor es compasivo...",
      "respuesta": "El Señor es compasivo y misericordioso"
    },
    "evangelio": {
      "cita": "Mt 18,21-35",
      "texto": "Entonces se le acercó Pedro..."
    }
  }
  ```

- **canciones_json:** Asignación final por momento. Ejemplo:
  ```json
  {
    "entrada": {"id": 5, "nombre": "Al encuentro", "tono": "Do"},
    "gloria": {"id": 18, "nombre": "Gloria de Nazaret", "tono": "Mi"},
    "comunion": {"id": 80, "nombre": "Como Tus brazos", "tono": "Sol"}
  }
  ```

## 4.3. Workflow y administración

### `admin_users`
- Usuarios del panel admin.
- `role`: `admin` o `viewer`.
- Contraseñas hasheadas con bcrypt.

### `workflow_runs`
- Instancia del workflow semanal por fecha.
- `status`/`current_step`: `init`, `fetch_lectures`, `verify_lectures`, `propose_songs`, `verify_songs`, `generate_assets`, `publish`, `done`.
- `steps_data`: JSON con lecturas, propuesta, asignación, etc.

### `workflow_logs`
- Logs por paso.

### `workflow_backups`
- Backups automáticos creados antes de regenerar una fecha existente.

## 4.4. Esquema completo

El archivo `data/schema_full.sql` contiene el esquema SQL completo exportado desde `data/db.sqlite3`. Debe usarse como referencia para:

- Migrar la BD a otro PC.
- Diagnosticar discrepancias con `data/schema.sql` (obsoleto) y `data/schema_slides.sql`.
- Crear bases de datos de test.
