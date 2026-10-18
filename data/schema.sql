-- Esquema de base de datos SQLite para CCE-M5-Web-Presentaciones
-- Actualizado para reflejar el schema real de producción

-- Tabla de lecturas dominicales extraidas de Koinonia
CREATE TABLE IF NOT EXISTS lecturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    domingo TEXT NOT NULL,
    celebracion TEXT,
    temporada TEXT NOT NULL,
    ciclo TEXT,
    color_liturgico TEXT NOT NULL,
    primera_lectura_cita TEXT,
    primera_lectura_texto TEXT,
    salmo_cita TEXT,
    salmo_antifona TEXT,
    salmo_texto TEXT,
    segunda_lectura_cita TEXT,
    segunda_lectura_texto TEXT,
    evangelio_cita TEXT,
    evangelio_texto TEXT,
    fuente_scraping TEXT DEFAULT 'koinonia',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(fecha)
);

-- Tabla de canciones del cancionero escolapio
CREATE TABLE IF NOT EXISTS canciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    titulo_url TEXT,
    letra_con_acordes TEXT,
    letra_sin_acordes TEXT,
    acordes_json TEXT,
    estructura_json TEXT,
    html_visual TEXT,
    html_original TEXT,
    tono TEXT,
    momento_liturgico TEXT,
    temas TEXT,
    referencias_biblicas TEXT,
    enlace_audio TEXT,
    enlace_alt TEXT,
    fuente TEXT DEFAULT 'blogspot',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Momentos litúrgicos asignados a canciones
CREATE TABLE IF NOT EXISTS cancion_momentos (
    cancion_id INTEGER NOT NULL,
    momento_liturgico TEXT NOT NULL,
    PRIMARY KEY (cancion_id, momento_liturgico),
    FOREIGN KEY (cancion_id) REFERENCES canciones(id) ON DELETE CASCADE
);

-- Slides del catálogo
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
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de presentaciones generadas semanalmente
CREATE TABLE IF NOT EXISTS presentaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_domingo DATE NOT NULL,
    lectura_id INTEGER,
    canciones_json TEXT,
    evento_especial TEXT,
    ruta_pptx TEXT,
    ruta_pdf_fieles TEXT,
    ruta_pdf_musicos TEXT,
    ruta_web TEXT,
    estado TEXT DEFAULT 'borrador',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
);

-- Presentación compuesta por slides
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
    FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id) ON DELETE CASCADE
);

-- Comentarios/aprobaciones
CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presentacion_id INTEGER,
    autor TEXT,
    texto TEXT,
    estado TEXT DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id)
);

-- Log de automatizaciones
CREATE TABLE IF NOT EXISTS automation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agente TEXT NOT NULL,
    tarea TEXT NOT NULL,
    estado TEXT NOT NULL,
    mensaje TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
