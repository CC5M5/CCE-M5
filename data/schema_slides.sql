-- Esquema de catálogo de diapositivas para CCE-M5-Web-Presentaciones
-- Fase A: catálogo general + variantes por subtipo/tiempo litúrgico.
-- Las diapositivas generales se modifican por tipo base.
-- Las presentaciones pasadas conservan su propia versión (JSON/PPTX/PDF).

-- Tipos de diapositiva canónicos. Tabla de dominio para validar.
CREATE TABLE IF NOT EXISTS slides_tipos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    orden INTEGER NOT NULL DEFAULT 0,
    requiere_cancion INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO slides_tipos (id, nombre, descripcion, orden, requiere_cancion) VALUES
('portada', 'Portada', 'Título de la celebración y fecha', 1, 0),
('entrada', 'Entrada', 'Canción de entrada', 2, 1),
('paso', 'Diapositiva de paso', 'Fondo + ilustración sin texto entre momentos', 3, 0),
('perdon', 'Perdón', 'Acto penitencial / bendición del agua', 4, 0),
('gloria', 'Gloria', 'Canción del Gloria o texto fijo', 5, 1),
('transicion_palabra', 'Transición Palabra', 'Separador antes de la Liturgia de la Palabra', 6, 0),
('primera_lectura', 'Primera Lectura', 'Primera lectura bíblica', 7, 0),
('salmo', 'Salmo', 'Salmo responsorial', 8, 0),
('segunda_lectura', 'Segunda Lectura', 'Segunda lectura bíblica', 9, 0),
('aleluya', 'Aleluya', 'Canto de aleluya', 10, 1),
('evangelio', 'Evangelio', 'Evangelio del día', 11, 0),
('transicion_eucaristia', 'Transición Eucaristía', 'Separador antes de la Liturgia Eucarística', 12, 0),
('credo', 'Credo', 'Credo de la asamblea', 13, 0),
('ofertorio', 'Ofertorio', 'Canción de ofertorio', 14, 1),
('santo', 'Santo', 'Santo / Prefacio', 15, 1),
('padre_nuestro', 'Padre Nuestro', 'Oración del Señor', 16, 1),
('paz', 'Paz', 'Rito de la paz', 17, 1),
('comunion', 'Comunión', 'Canción de comunión', 18, 1),
('maria', 'Canto a María', 'Canto a la Virgen', 19, 1),
('despedida', 'Despedida', 'Canción de despedida / ¡Id en paz!', 20, 1);

-- Catálogo maestro de diapositivas.
-- Una diapositiva base pertenece a un tipo y puede tener varias variantes.
CREATE TABLE IF NOT EXISTS slides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT NOT NULL,
    subtipo TEXT NOT NULL DEFAULT 'general',
    titulo TEXT NOT NULL,
    contenido TEXT NOT NULL DEFAULT '',
    cita TEXT DEFAULT '',
    subtitulo TEXT DEFAULT '',
    imagen TEXT DEFAULT '',
    color_liturgico TEXT DEFAULT '',  -- vacío = todos los colores
    es_default INTEGER DEFAULT 0,     -- 1 = variante por defecto para (tipo, subtipo, color_liturgico)
    activo INTEGER DEFAULT 1,
    notas TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tipo) REFERENCES slides_tipos(id)
);

-- Presentaciones semanales y sus diapositivas activas.
-- Cada entrada apunta a una slide del catálogo (o a una copia si se personalizó).
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
    personalizado INTEGER DEFAULT 0,  -- 1 = editado a mano para esa semana
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id) ON DELETE CASCADE,
    FOREIGN KEY (slide_id) REFERENCES slides(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_slides_tipo ON slides(tipo);
CREATE INDEX IF NOT EXISTS idx_slides_subtipo ON slides(subtipo);
CREATE INDEX IF NOT EXISTS idx_slides_color ON slides(color_liturgico);
CREATE INDEX IF NOT EXISTS idx_slides_default ON slides(tipo, subtipo, color_liturgico, es_default);
CREATE INDEX IF NOT EXISTS idx_presentacion_slides_presentacion ON presentacion_slides(presentacion_id, numero);
