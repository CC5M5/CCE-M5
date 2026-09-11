-- Esquema de base de datos SQLite para CCE-M5-Web-Presentaciones
-- Creado: 2026-09-11
-- Fase: Fundacion

-- Tabla de lecturas dominicales extraidas de Koinonia
CREATE TABLE IF NOT EXISTS lecturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATE NOT NULL,
    domingo TEXT NOT NULL,
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
    tono TEXT,
    momento_liturgico TEXT,
    temas TEXT,
    referencias_biblicas TEXT,
    enlace_audio TEXT,
    enlace_alt TEXT,
    fuente TEXT DEFAULT 'blogspot',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Tabla de comentarios/aprobaciones
CREATE TABLE IF NOT EXISTS comentarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    presentacion_id INTEGER,
    autor TEXT,
    texto TEXT,
    estado TEXT DEFAULT 'pendiente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id)
);

-- Tabla de log de automatizaciones
CREATE TABLE IF NOT EXISTS automation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agente TEXT NOT NULL,
    tarea TEXT NOT NULL,
    estado TEXT NOT NULL,
    mensaje TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices para optimizacion
CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas(fecha);
CREATE INDEX IF NOT EXISTS idx_canciones_momento ON canciones(momento_liturgico);
CREATE INDEX IF NOT EXISTS idx_presentaciones_fecha ON presentaciones(fecha_domingo);
