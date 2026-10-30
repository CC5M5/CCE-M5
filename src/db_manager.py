#!/usr/bin/env python3
"""
Gestor de base de datos SQLite para CCE-M5-Web-Presentaciones
"""

import re
import sqlite3
from pathlib import Path

from src.config import settings
from src.log_config import get_logger

logger = get_logger(__name__)

DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
PROJECT_DIR = settings.project_dir
DATA_DIR = settings.data_dir
DB_PATH = settings.db_path
SCHEMA_PATH = DATA_DIR / "schema.sql"


def create_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Crea y configura una conexión SQLite lista para usar.

    No ejecuta PRAGMA integrity_check: ese check es costoso y se hace una
    única vez en ``init_database`` (auditoría H4/M, 2026-11-01).
    """
    target = db_path or DB_PATH
    conn = sqlite3.connect(
        str(target),
        timeout=30.0,
        isolation_level="DEFERRED",
    )
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    """Aplica PRAGMAs de seguridad y rendimiento."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA trusted_schema=OFF")


def _validate_integrity(conn: sqlite3.Connection) -> None:
    """Ejecuta PRAGMA integrity_check (una vez, al inicializar)."""
    row = conn.execute("PRAGMA integrity_check").fetchone()
    result = row[0] if row else "unknown"
    if result != "ok":
        raise sqlite3.DatabaseError(f"integrity_check falló: {result}")
    logger.debug("integridad de la base de datos verificada: ok")


def _load_schema_sql() -> str:
    """Carga el esquema desde data/schema.sql si existe.

    El dump de sqlite3.iterdump() usa CREATE TABLE/INDEX sin IF NOT EXISTS
    y INSERT INTO con valores fijos. Lo post-procesamos para que sea
    idempotente: las tablas e indices se crean solo si no existen y los
    inserts se ignoran cuando ya hay una fila con la misma PK.
    """
    if SCHEMA_PATH.exists():
        raw = SCHEMA_PATH.read_text(encoding="utf-8")
        transformed = re.sub(
            r"CREATE TABLE\s+(?!IF\s+NOT\s+EXISTS\b)",
            "CREATE TABLE IF NOT EXISTS ",
            raw,
            flags=re.IGNORECASE,
        )
        transformed = re.sub(
            r"CREATE INDEX\s+(?!IF\s+NOT\s+EXISTS\b)",
            "CREATE INDEX IF NOT EXISTS ",
            transformed,
            flags=re.IGNORECASE,
        )
        transformed = transformed.replace('INSERT INTO "', 'INSERT OR IGNORE INTO "')
        return transformed
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


def init_database(db_path: Path | None = None) -> None:
    """Inicializa la base de datos con el esquema, índices y control de versiones."""
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)

    with create_connection(target) as conn:
        _validate_integrity(conn)
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
            )
            """
        )

        # Migración: añadir celebracion si la tabla ya existía sin ella.
        _add_column_if_missing(conn, "lecturas", "celebracion", "TEXT")

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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_canciones_momento ON canciones(momento_liturgico)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_canciones_titulo ON canciones(titulo)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_presentaciones_fecha ON presentaciones(fecha_domingo)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_presentaciones_lectura ON presentaciones(lectura_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_comentarios_presentacion ON comentarios(presentacion_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_automation_log_agente_fecha ON automation_log(agente, fecha)"
        )


_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_sql_identifier(name: str) -> str:
    """Valida un identificador SQL simple (sin comillas, sin espacios)."""
    if not _SQL_IDENTIFIER_RE.match(name):
        raise ValueError(f"Identificador SQL no válido: {name!r}")
    return name


def _add_column_if_missing(
    conn: sqlite3.Connection,
    tabla: str,
    columna: str,
    tipo: str,
) -> None:
    """Añade una columna a una tabla si no existe (migración ligera).

    Los identificadores se validan contra una lista cerrada antes de
    interpolarse en SQL (auditoría B15, 2026-11-01).
    """
    tabla = _validate_sql_identifier(tabla)
    columna = _validate_sql_identifier(columna)
    tipo = _validate_sql_identifier(tipo)

    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (tabla,),
    ).fetchone()
    if existe is None:
        raise sqlite3.DatabaseError(f"La tabla {tabla!r} no existe")

    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({tabla})").fetchall()}
    if columna not in cols:
        conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {tipo}")
        logger.info("Migración: añadida columna %s a %s", columna, tabla)


def get_connection() -> sqlite3.Connection:
    """Retorna una conexión configurada a la base de datos."""
    return create_connection()


if __name__ == "__main__":
    init_database()
