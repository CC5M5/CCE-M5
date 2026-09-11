# Spec 03: Modelo de Datos

## Diagrama Entidad-Relación

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   lecturas   │       │presentaciones│       │  canciones   │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ fecha        │◄──────│ fecha_domingo│       │ titulo       │
│ domingo      │       │ lectura_id   │──────►│ titulo_url   │
│ temporada    │       │ canciones_json│      │ letra_con_acordes│
│ ciclo        │       │ evento_especial│     │ letra_sin_acordes│
│ color_liturgico│     │ ruta_pptx    │       │ acordes_json │
│ primera_lectura_cita│ ruta_pdf_fieles│     │ tono         │
│ primera_lectura_texto│ ruta_pdf_musicos│   │ momento_liturgico│
│ salmo_cita   │       │ ruta_web     │       │ temas (JSON) │
│ salmo_texto  │       │ estado       │       │ referencias_biblicas (JSON)│
│ segunda_lectura_cita│ fecha_creacion│       │ enlace_audio │
│ segunda_lectura_texto│ fecha_publicacion│  │ enlace_alternativo│
│ evangelio_cita│      └──────────────┘       │ fuente       │
│ evangelio_texto│                             │ fecha_creacion│
│ fuente_scraping│                             └──────────────┘
│ fecha_scraping │
└──────────────┘

┌──────────────┐       ┌──────────────┐
│ comentarios  │       │   temas      │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ presentacion_id│◄────│ nombre       │
│ autor        │       │ descripcion  │
│ texto        │       └──────────────┘
│ fecha        │
│ estado       │       ┌──────────────┐
│ respuesta    │       │canciones_temas│
└──────────────┘       ├──────────────┤
                       │ cancion_id   │──┐
                       │ tema_id      │◄─┘
                       └──────────────┘
```

## Tablas Detalladas

### Tabla: `lecturas`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| fecha | DATE | NOT NULL, UNIQUE | Fecha de la celebración |
| domingo | TEXT | | "XXIV Domingo del Tiempo Ordinario" |
| temporada | TEXT | | Adviento, Navidad, Cuaresma, Pascua, Tiempo Ordinario |
| ciclo | TEXT | | A, B, C |
| color_liturgico | TEXT | | Verde, Violeta, Blanco, Rojo, Rosa |
| primera_lectura_cita | TEXT | | "Eclo 27,30-28,7" |
| primera_lectura_texto | TEXT | | Texto completo primera lectura |
| salmo_cita | TEXT | | "Sal 102(103)" |
| salmo_texto | TEXT | | Texto completo salmo |
| salmo_respuesta | TEXT | | "El Señor es compasivo y misericordioso" |
| segunda_lectura_cita | TEXT | | "Rom 14,7-9" (nullable) |
| segunda_lectura_texto | TEXT | | Texto completo (nullable) |
| evangelio_cita | TEXT | | "Mt 18,21-35" |
| evangelio_texto | TEXT | | Texto completo evangelio |
| fuente_scraping | TEXT | DEFAULT 'koinonia' | Origen de los datos |
| fecha_scraping | DATETIME | | Cuándo se obtuvo |

### Tabla: `canciones`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| titulo | TEXT | NOT NULL | Título de la canción |
| titulo_url | TEXT | UNIQUE | Slug para URLs (ej: "a-tu-amparo-y-proteccion") |
| letra_con_acordes | TEXT | | Letra completa CON acordes (formato original Blogspot) |
| letra_sin_acordes | TEXT | | Letra SIN acordes (para presentaciones) |
| acordes_json | JSON | | Estructura: `[{"acorde": "Do", "linea": 1, "posicion": 0}]` |
| tono | TEXT | | Tono principal: Do, Re, Mi, Fa, Sol, La, Si |
| momento_liturgico | TEXT | | ENTRADA, GLORIA, ALELUYA, COMUNION, etc. |
| temas | JSON | | Lista: ["perdon", "esperanza", "comunidad"] |
| referencias_biblicas | JSON | | Lista: ["Sal 103", "Mt 18"] |
| enlace_audio | TEXT | | URL YouTube/Spotify |
| enlace_alternativo | TEXT | | URL versión alternativa (ej: Betania Music) |
| fuente | TEXT | DEFAULT 'CCE M5 Music' | Origen de la canción |
| fecha_creacion | DATETIME | DEFAULT CURRENT_TIMESTAMP | |

### Tabla: `presentaciones_semanales`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| fecha_domingo | DATE | NOT NULL, UNIQUE | Fecha de la celebración |
| lectura_id | INTEGER | FK → lecturas.id | Referencia a lecturas |
| canciones_json | JSON | | `{"entrada": 5, "gloria": 12, ...}` |
| evento_especial | TEXT | | "Confirmación de Pedro" (nullable) |
| ruta_pptx | TEXT | | Path al archivo PPTX |
| ruta_pdf_fieles | TEXT | | Path al PDF para fieles |
| ruta_pdf_musicos | TEXT | | Path al PDF para músicos (con acordes) |
| ruta_web | TEXT | | URL en GitHub Pages |
| estado | TEXT | DEFAULT 'borrador' | borrador, confirmada, publicada, archivada |
| fecha_creacion | DATETIME | DEFAULT CURRENT_TIMESTAMP | |
| fecha_publicacion | DATETIME | | Cuándo se publicó |

### Tabla: `temas`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| nombre | TEXT | NOT NULL, UNIQUE | "perdon", "esperanza", "amor", etc. |
| descripcion | TEXT | | Descripción del tema |

### Tabla: `canciones_temas` (relación many-to-many)

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| cancion_id | INTEGER | FK → canciones.id | |
| tema_id | INTEGER | FK → temas.id | |

### Tabla: `comentarios`

| Campo | Tipo | Constraints | Descripción |
|-------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | Identificador único |
| presentacion_id | INTEGER | FK → presentaciones_semanales.id | |
| autor | TEXT | | Nombre del comentarista |
| email | TEXT | | Email (para respuesta) |
| texto | TEXT | NOT NULL | Contenido del comentario |
| fecha | DATETIME | DEFAULT CURRENT_TIMESTAMP | |
| estado | TEXT | DEFAULT 'pendiente' | pendiente, aprobado, rechazado |
| respuesta | TEXT | | Respuesta del moderador |

## Esquema JSON para `acordes_json`

```json
{
  "version": "1.0",
  "tono_base": "Do",
  "lineas": [
    {
      "numero": 1,
      "tipo": "acordes",
      "texto": "Do    Sol    Lam    Fa"
    },
    {
      "numero": 2,
      "tipo": "letra",
      "texto": "A TU AMPARO Y PROTECCIÓN,"
    },
    {
      "numero": 3,
      "tipo": "acordes",
      "texto": "Do          Sol    Fa    Sol"
    },
    {
      "numero": 4,
      "tipo": "letra",
      "texto": "MADRE DE DIOS, ACUDIMOS."
    }
  ],
  "estructura_parsed": [
    {
      "linea_letra": 2,
      "acordes": [
        {"acorde": "Do", "posicion": 0},
        {"acorde": "Sol", "posicion": 6},
        {"acorde": "Lam", "posicion": 13},
        {"acorde": "Fa", "posicion": 20}
      ]
    }
  ]
}
```

## Esquema JSON para `canciones_json` (en presentaciones)

```json
{
  "seleccion": {
    "entrada": {"cancion_id": 5, "nombre": "Al encuentro", "tono": "Do"},
    "perdon": {"cancion_id": 15, "nombre": "Perdónanos, Señor", "tono": "Re"},
    "gloria": {"cancion_id": 18, "nombre": "Gloria de Nazaret", "tono": "Mi"},
    "salmo": {"cancion_id": 25, "nombre": "Salmo responsorial", "tono": "La"},
    "aleluya": {"cancion_id": 29, "nombre": "Aleluya de la Tierra", "tono": "Sol"},
    "ofertorio": {"cancion_id": 53, "nombre": "Pongo mi vida", "tono": "Do"},
    "santo": {"cancion_id": 46, "nombre": "Santo, santo, santo", "tono": "Re"},
    "padre_nuestro": {"cancion_id": 69, "nombre": "Padre nuestro", "tono": "Mi"},
    "paz": {"cancion_id": 70, "nombre": "La Paz te doy", "tono": "Fa"},
    "comunion": {"cancion_id": 80, "nombre": "Como Tus brazos", "tono": "Sol"},
    "canto_a_maria": {"cancion_id": 100, "nombre": "Junto a ti María", "tono": "La"},
    "despedida": {"cancion_id": 105, "nombre": "Cristo vive", "tono": "Do"}
  },
  "notas": "Celebración normal, sin eventos especiales"
}
```

## Seed Inicial de Temas

```sql
INSERT INTO temas (nombre, descripcion) VALUES
('perdon', 'Perdón, reconciliación, misericordia'),
('esperanza', 'Esperanza, confianza, futuro'),
('amor', 'Amor fraternal, caridad, comunidad'),
('fe', 'Fe, creencia, confianza en Dios'),
('alabanza', 'Alabanza, glorificación, adoración'),
('comunidad', 'Comunidad, hermandad, unidad'),
('servicio', 'Servicio, entrega, seguimiento'),
('paz', 'Paz, reconciliación, armonía'),
('mision', 'Misión, evangelización, testimonio'),
('maria', 'Virgen María, maternidad, protección'),
('eucaristia', 'Eucaristía, pan, comunión'),
('conversion', 'Conversión, cambio, nuevo comienzo'),
('gratitud', 'Gracia, gratitud, bendición'),
('luz', 'Luz, verdad, guía'),
('camino', 'Camino, peregrinaje, jornada');
```

## Índices Recomendados

```sql
CREATE INDEX idx_lecturas_fecha ON lecturas(fecha);
CREATE INDEX idx_canciones_momento ON canciones(momento_liturgico);
CREATE INDEX idx_canciones_tono ON canciones(tono);
CREATE INDEX idx_presentaciones_fecha ON presentaciones_semanales(fecha_domingo);
CREATE INDEX idx_presentaciones_estado ON presentaciones_semanales(estado);
CREATE INDEX idx_comentarios_estado ON comentarios(estado);
```
