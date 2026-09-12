#!/usr/bin/env python3
"""
Gestor de base de datos SQLite para CCE-M5-Web-Presentaciones
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", DEFAULT_PROJECT_DIR))
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
SCHEMA_PATH = DATA_DIR / "schema.sql"


def create_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Crea y configura una conexión SQLite lista para usar."""
    target = db_path or DB_PATH
    conn = sqlite3.connect(
        str(target),
        timeout=30.0,
        isolation_level="DEFERRED",
    )
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    _validate_integrity(conn)
    return conn


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    """Aplica PRAGMAs de seguridad y rendimiento."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA trusted_schema=OFF")


def _validate_integrity(conn: sqlite3.Connection) -> None:
    """Ejecuta PRAGMA integrity_check al inicio."""
    row = conn.execute("PRAGMA integrity_check").fetchone()
    result = row[0] if row else "unknown"
    if result != "ok":
        raise sqlite3.DatabaseError(f"integrity_check falló: {result}")
    logger.debug("integridad de la base de datos verificada: ok")


def _load_schema_sql() -> str:
    """Carga el esquema desde data/schema.sql si existe."""
    if SCHEMA_PATH.exists():
        return SCHEMA_PATH.read_text(encoding="utf-8")
    return ""


def _ensure_schema_version(conn: sqlite3.Connection) -> None:
    """Crea la tabla de control de migraciones."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER NOT NULL,
                aplicada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(version)
            )
            """
        )


def init_database(db_path: Optional[Path] = None) -> None:
    """Inicializa la base de datos con el esquema, índices y control de versiones."""
    target = db_path or DB_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with create_connection(target) as conn:
        _ensure_schema_version(conn)

        schema_sql = _load_schema_sql()
        if schema_sql:
            conn.executescript(schema_sql)
        else:
            _create_default_schema(conn)
            _create_default_indexes(conn)

        logger.info("Base de datos inicializada: %s", target)


def _create_default_schema(conn: sqlite3.Connection) -> None:
    """Crea las tablas por defecto cuando no existe schema.sql."""
    with conn:
        # Lecturas dominicales
        conn.execute(
            """
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
            )
            """
        )

        # Canciones del cancionero
        conn.execute(
            """
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
            )
            """
        )

        # Presentaciones generadas
        conn.execute(
            """
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
            )
            """
        )

        # Comentarios/aprobaciones
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comentarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                presentacion_id INTEGER,
                autor TEXT,
                texto TEXT,
                estado TEXT DEFAULT 'pendiente',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (presentacion_id) REFERENCES presentaciones(id)
            )
            """
        )

        # Log de automatizaciones
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS automation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agente TEXT NOT NULL,
                tarea TEXT NOT NULL,
                estado TEXT NOT NULL,
                mensaje TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _create_default_indexes(conn: sqlite3.Connection) -> None:
    """Crea índices por defecto cuando no existe schema.sql."""
    with conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas(fecha)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canciones_momento ON canciones(momento_liturgico)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canciones_titulo ON canciones(titulo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_presentaciones_fecha ON presentaciones(fecha_domingo)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_presentaciones_lectura ON presentaciones(lectura_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_comentarios_presentacion ON comentarios(presentacion_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_automation_log_agente_fecha ON automation_log(agente, fecha)")


def get_connection() -> sqlite3.Connection:
    """Retorna una conexión configurada a la base de datos."""
    return create_connection()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
