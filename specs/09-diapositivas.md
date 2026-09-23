# Spec 09: Catálogo de Diapositivas y Editor

## Objetivo

Crear un catálogo maestro de diapositivas litúrgicas reutilizables, con variantes por subtipo y una variante por defecto seleccionable. El catálogo se edita a través de un servidor web local y alimenta la generación de presentaciones semanales.

## Decisiones de diseño

- Cada diapositiva base es **general**: modificar la base afecta a futuras presentaciones; las pasadas conservan su versión histórica (JSON/PPTX/PDF).
- Las variantes se identifican por `(tipo, subtipo)`. La variante `es_default = 1` se usa cuando no se especifica otra.
- El color litúrgico de la diapositiva base es solo para previsualización; la generación final aplica el color del domingo correspondiente.
- Las diapositivas de paso (`tipo = paso`) son neutras: fondo + ilustración, sin título ni contenido.
- La marca `--- DIAPOSITIVA ---` en una línea aparte divide una diapositiva base en N slides numeradas.

## Esquema de datos

### `slides_tipos`

Tabla de dominio con los tipos canónicos de diapositiva.

```sql
CREATE TABLE IF NOT EXISTS slides_tipos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    orden INTEGER NOT NULL DEFAULT 0,
    requiere_cancion INTEGER DEFAULT 0
);
```

Tipos actuales (orden litúrgico):

| ID | Nombre | Orden | Requiere canción |
|---|---|---|---|
| `portada` | Portada | 1 | 0 |
| `entrada` | Entrada | 2 | 1 |
| `paso` | Diapositiva de paso | 3 | 0 |
| `perdon` | Perdón | 4 | 0 |
| `gloria` | Gloria | 5 | 1 |
| `transicion_palabra` | Liturgia de la Palabra | 6 | 0 |
| `primera_lectura` | Primera Lectura | 7 | 0 |
| `salmo` | Salmo Responsorial | 8 | 0 |
| `segunda_lectura` | Segunda Lectura | 9 | 0 |
| `aleluya` | Aleluya | 10 | 1 |
| `evangelio` | Evangelio | 11 | 0 |
| `transicion_eucaristia` | Liturgia Eucarística | 12 | 0 |
| `credo` | Credo | 13 | 0 |
| `ofertorio` | Ofertorio | 14 | 1 |
| `santo` | Santo | 15 | 1 |
| `padre_nuestro` | Padre Nuestro | 16 | 1 |
| `paz` | Paz | 17 | 1 |
| `comunion` | Comunión | 18 | 1 |
| `maria` | Canto a María | 19 | 1 |
| `despedida` | Despedida / ¡Id en paz! | 20 | 1 |

### `slides`

Catálogo maestro de diapositivas.

```sql
CREATE TABLE IF NOT EXISTS slides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    subtipo TEXT NOT NULL DEFAULT 'general',
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL DEFAULT '',
    cita TEXT DEFAULT '',
    subtitulo TEXT DEFAULT '',
    imagen TEXT DEFAULT '',
    color_liturgico TEXT DEFAULT '',
    es_default INTEGER DEFAULT 0,
    activo INTEGER DEFAULT 1,
    notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo) REFERENCES slides_tipos(id)
);
```

Reglas:

- Solo una slide puede tener `es_default = 1` por combinación `(tipo, subtipo)`.
- `subtipo` puede ser:
  - `general` para lecturas, transiciones y textos fijos.
  - `cancion_<id>` para momentos musicales vinculados al cancionero.
  - `texto_fijo` para textos litúrgicos fijos (credo, santo, etc.).
  - Variantes específicas (`acto_penitencial`, `bendicion_agua`, etc.).
- `color_liturgico` es informativo/preview; la generación final usa el color del domingo.

### `presentacion_slides`

Composición semanal de una presentación. Cada fila apunta a una slide del catálogo (o a una copia personalizada si `personalizado = 1`).

```sql
CREATE TABLE IF NOT EXISTS presentacion_slides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presentacion_id INTEGER NOT NULL,
    slide_id INTEGER,
    numero INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    subtipo TEXT DEFAULT 'general',
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL DEFAULT '',
    cita TEXT DEFAULT '',
    subtitulo TEXT DEFAULT '',
    imagen TEXT DEFAULT '',
    momento TEXT DEFAULT '',
    activo INTEGER DEFAULT 1,
    personalizado INTEGER DEFAULT 0,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (slide_id) REFERENCES slides(id)
);
```

## Editor local (Fase B)

- Servidor Flask en `scripts/editor_diapositivas_server.py`.
- Puerto `4323`, bind `0.0.0.0`, accesible en `http://192.168.68.244:4323`.
- Listado lateral por tipo canónico.
- Formulario de edición:
  - Tipo (selector).
  - Subtipo / variante.
  - Checkbox `es_default`.
  - Título, subtítulo, cita.
  - Color litúrgico (solo para preview).
  - Contenido (textarea).
  - Botón "Dividir aquí" inserta `--- DIAPOSITIVA ---`.
  - Selector de imagen con miniaturas desde `data/ilustraciones/catalogo.json`.
  - Notas internas.
  - Botones "Guardar y commitear" y "Duplicar".
- Preview 4:3 a la derecha con el mismo aspecto visual del generador final:
  - Interlineado compacto (`line-height: 1.25`, `1.22` para canciones).
  - Negrita con `**texto**` o `** texto **`.
  - División automática por `--- DIAPOSITIVA ---` mostrando `(1/N)`, `(2/N)`...
- Guardar actualiza `data/db.sqlite3` y ejecuta `git commit` + `git push`.

## Armado de presentación semanal (Fase C)

### Requisitos funcionales

1. **Vista de selección semanal**: listar presentaciones existentes y crear nuevas por fecha de domingo.
2. **Propuesta automática**:
   - Leer lectura del domingo y canciones asignadas.
   - Para cada momento litúrgico, buscar la slide base con `tipo` correspondiente y `es_default = 1`.
   - Si el momento requiere canción, usar la canción asignada para seleccionar la variante `cancion_<id>` si existe.
3. **Selector de variantes**: permitir al usuario cambiar la variante (`subtipo`) de cada momento.
4. **Orden y visibilidad**:
   - Reordenar slides por drag-and-drop o botones.
   - Activar/desactivar slides individuales.
5. **Diapositivas de paso**: insertar automáticamente las transiciones litúrgicas (`transicion_palabra`, `transicion_eucaristia`) y slides de paso neutras entre momentos, siguiendo el orden canónico.
6. **Guardar composición**: almacenar la secuencia en `presentacion_slides` con `numero`, `slide_id`, `tipo`, `subtipo`, etc.
7. **Vista previa**: mostrar la presentación completa en el aspecto final 4:3 antes de generar.

### Orden canónico de momentos

```
1. portada
2. entrada
3. transicion_palabra
4. perdon
5. paso (neutro)
6. gloria
7. primera_lectura
8. salmo
9. segunda_lectura
10. aleluya
11. evangelio
12. transicion_eucaristia
13. credo
14. paso (neutro)
15. ofertorio
16. paso (neutro)
17. santo
18. paso (neutro)
19. padre_nuestro
20. paso (neutro)
21. paz
22. paso (neutro)
23. comunion
24. paso (neutro)
25. maria
26. paso (neutro)
27. despedida
28. portada (despedida / ¡Id en paz!)
```

## Generación final (Fase D)

- Leer `presentacion_slides` para la fecha seleccionada.
- Aplicar overrides personalizados (`contenido_override`, `imagen_override`) si los hubiera.
- Para cada slide base, expandir `--- DIAPOSITIVA ---` en N slides numeradas.
- Aplicar el color litúrgico del domingo (desde `lecturas.color_liturgico`).
- Generar PPTX, HTML y PDF en `presentaciones_html/YYYY-MM-DD_presentacion/`.
- Copiar assets y actualizar la web Astro.
- Hacer `git commit` + `push`.

## Archivos relacionados

- `data/schema_slides.sql` — Esquema del catálogo.
- `data/db.sqlite3` — Base de datos con el catálogo y composiciones.
- `scripts/importar_slides_catalogo.py` — Importación desde presentaciones históricas.
- `scripts/editor_diapositivas_server.py` — Editor local Flask.
- `src/generators/presentacion_html.py` — Generador final de presentaciones (a adaptar).
- `scripts/generar_semana.py` — Pipeline semanal (a adaptar).
