CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

CREATE TABLE IF NOT EXISTS automation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agente TEXT NOT NULL,
            tarea TEXT NOT NULL,
            estado TEXT NOT NULL,
            mensaje TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

CREATE TABLE IF NOT EXISTS cancion_momentos (
        cancion_id INTEGER NOT NULL,
        momento_liturgico TEXT NOT NULL,
        PRIMARY KEY (cancion_id, momento_liturgico),
        FOREIGN KEY (cancion_id) REFERENCES canciones(id) ON DELETE CASCADE
    );

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
        , estructura_json TEXT, html_visual TEXT, html_original TEXT);

CREATE TABLE IF NOT EXISTS comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            presentacion_id INTEGER,
            autor TEXT,
            texto TEXT,
            estado TEXT DEFAULT 'pendiente',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id)
        );

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
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, celebracion TEXT, primera_lectura_libro TEXT, segunda_lectura_libro TEXT, evangelio_libro TEXT, salmo_libro TEXT,
            UNIQUE(fecha)
        );

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
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, lectura_json TEXT, notas TEXT, creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
        );

CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                aplicada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(version)
            );

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

CREATE TABLE IF NOT EXISTS slides_tipos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    orden INTEGER NOT NULL DEFAULT 0,
    requiere_cancion INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS workflow_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    fecha_domingo DATE NOT NULL,
                    backup_path TEXT NOT NULL,
                    original_paths TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
                );

CREATE TABLE IF NOT EXISTS workflow_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'info',
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
                );

CREATE TABLE IF NOT EXISTS workflow_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha_domingo DATE NOT NULL,
                    status TEXT NOT NULL DEFAULT 'init',
                    current_step TEXT NOT NULL DEFAULT 'init',
                    steps_data TEXT NOT NULL DEFAULT '{}',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    superseded_by INTEGER,
                    FOREIGN KEY (superseded_by) REFERENCES workflow_runs(id)
                );
