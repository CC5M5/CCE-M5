"""Capa de acceso a datos para el panel de administración.

Reaprovecha db.sqlite3 del proyecto y añade las tablas necesarias para
usuarios, workflow manual y backups.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.web_admin.config import DB_PATH

logger = logging.getLogger(__name__)


def _connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=30.0, isolation_level="DEFERRED")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_admin_schema(db_path: Optional[Path] = None) -> None:
    """Crea las tablas de administración si no existen."""
    with _connection(db_path) as conn:
        with conn:
            conn.executescript(
                """
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

                CREATE TABLE IF NOT EXISTS workflow_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    step TEXT NOT NULL,
                    level TEXT NOT NULL DEFAULT 'info',
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
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

                CREATE INDEX IF NOT EXISTS idx_workflow_runs_fecha ON workflow_runs(fecha_domingo);
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
                CREATE INDEX IF NOT EXISTS idx_workflow_logs_workflow ON workflow_logs(workflow_id);
                """
            )
    logger.info("Esquema de administración inicializado en %s", db_path or DB_PATH)


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: int
    username: str
    password_hash: str
    full_name: Optional[str]
    role: str
    is_active: bool


def get_user_by_username(username: str, db_path: Optional[Path] = None) -> Optional[User]:
    with _connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE username = ?", (username,)
        ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )


def create_user(
    username: str,
    password_hash: str,
    full_name: Optional[str] = None,
    role: str = "viewer",
    db_path: Optional[Path] = None,
) -> int:
    with _connection(db_path) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO admin_users (username, password_hash, full_name, role, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, password_hash, full_name, role, _now()),
            )
            return int(cur.lastrowid)


def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[User]:
    with _connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM admin_users WHERE id = ?", (user_id,)
        ).fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            full_name=row["full_name"],
            role=row["role"],
            is_active=bool(row["is_active"]),
        )


def update_user(
    user_id: int,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db_path: Optional[Path] = None,
) -> None:
    with _connection(db_path) as conn:
        with conn:
            fields = []
            values = []
            if full_name is not None:
                fields.append("full_name = ?")
                values.append(full_name)
            if role is not None:
                fields.append("role = ?")
                values.append(role)
            if is_active is not None:
                fields.append("is_active = ?")
                values.append(1 if is_active else 0)
            if not fields:
                return
            fields.append("updated_at = ?")
            values.append(_now())
            values.append(user_id)
            conn.execute(
                f"UPDATE admin_users SET {', '.join(fields)} WHERE id = ?",
                values,
            )


def set_user_password(
    user_id: int,
    password_hash: str,
    db_path: Optional[Path] = None,
) -> None:
    with _connection(db_path) as conn:
        with conn:
            conn.execute(
                "UPDATE admin_users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, _now(), user_id),
            )


def delete_user(user_id: int, db_path: Optional[Path] = None) -> None:
    with _connection(db_path) as conn:
        with conn:
            conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))


def count_admins(db_path: Optional[Path] = None) -> int:
    with _connection(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM admin_users WHERE role = 'admin' AND is_active = 1"
        ).fetchone()
        return row["c"] if row else 0


def list_users(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    with _connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, username, full_name, role, is_active, created_at FROM admin_users"
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

WORKFLOW_STEPS = [
    "init",
    "fetch_lectures",
    "verify_lectures",
    "propose_songs",
    "verify_songs",
    "generate_assets",
    "publish",
    "done",
]


def step_index(step: str) -> int:
    try:
        return WORKFLOW_STEPS.index(step)
    except ValueError:
        return -1


def next_step(step: str) -> Optional[str]:
    idx = step_index(step)
    if idx < 0 or idx >= len(WORKFLOW_STEPS) - 1:
        return None
    return WORKFLOW_STEPS[idx + 1]


def goto_workflow_step(
    workflow_id: int,
    target_step: str,
    db_path: Optional[Path] = None,
) -> None:
    """Mueve el workflow a un paso arbitrario conservando steps_data."""
    if target_step not in WORKFLOW_STEPS:
        raise ValueError(f"Paso no válido: {target_step}")
    with _connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status = ?, current_step = ?, updated_at = ?
                WHERE id = ?
                """,
                (target_step, target_step, _now(), workflow_id),
            )


def create_workflow_run(
    fecha_domingo: str,
    created_by: Optional[str] = None,
    steps_data: Optional[Dict[str, Any]] = None,
    db_path: Optional[Path] = None,
) -> int:
    with _connection(db_path) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO workflow_runs (fecha_domingo, status, current_step, steps_data, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fecha_domingo,
                    "init",
                    "init",
                    json.dumps(steps_data or {}, ensure_ascii=False),
                    created_by,
                    _now(),
                ),
            )
            return int(cur.lastrowid)


def get_workflow_run(workflow_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    with _connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?", (workflow_id,)
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["steps_data"] = json.loads(data.get("steps_data") or "{}")
        return data


def get_latest_workflow_run(
    fecha_domingo: str, db_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    with _connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM workflow_runs
            WHERE fecha_domingo = ? AND superseded_by IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (fecha_domingo,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["steps_data"] = json.loads(data.get("steps_data") or "{}")
        return data


def list_workflow_runs(
    fecha_domingo: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    with _connection(db_path) as conn:
        if fecha_domingo:
            rows = conn.execute(
                """
                SELECT * FROM workflow_runs WHERE fecha_domingo = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (fecha_domingo, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM workflow_runs
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["steps_data"] = json.loads(data.get("steps_data") or "{}")
            result.append(data)
        return result


def update_workflow_step(
    workflow_id: int,
    status: str,
    current_step: str,
    steps_data: Optional[Dict[str, Any]] = None,
    completed_at: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> None:
    with _connection(db_path) as conn:
        with conn:
            if steps_data is not None:
                conn.execute(
                    """
                    UPDATE workflow_runs
                    SET status = ?, current_step = ?, steps_data = ?, updated_at = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (
                        status,
                        current_step,
                        json.dumps(steps_data, ensure_ascii=False),
                        _now(),
                        completed_at,
                        workflow_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE workflow_runs
                    SET status = ?, current_step = ?, updated_at = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (status, current_step, _now(), completed_at, workflow_id),
                )


def supersede_workflow_run(
    old_workflow_id: int, new_workflow_id: int, db_path: Optional[Path] = None
) -> None:
    with _connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                UPDATE workflow_runs
                SET superseded_by = ?, status = 'superseded', updated_at = ?
                WHERE id = ?
                """,
                (new_workflow_id, _now(), old_workflow_id),
            )


def add_workflow_log(
    workflow_id: int,
    step: str,
    message: str,
    level: str = "info",
    db_path: Optional[Path] = None,
) -> None:
    with _connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO workflow_logs (workflow_id, step, level, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (workflow_id, step, level, message, _now()),
            )


def get_workflow_logs(
    workflow_id: int, db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    with _connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM workflow_logs WHERE workflow_id = ?
            ORDER BY created_at DESC
            """,
            (workflow_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Backups
# ---------------------------------------------------------------------------


def create_backup_record(
    workflow_id: int,
    fecha_domingo: str,
    backup_path: str,
    original_paths: List[str],
    db_path: Optional[Path] = None,
) -> int:
    with _connection(db_path) as conn:
        with conn:
            cur = conn.execute(
                """
                INSERT INTO workflow_backups (workflow_id, fecha_domingo, backup_path, original_paths, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    fecha_domingo,
                    backup_path,
                    json.dumps(original_paths, ensure_ascii=False),
                    _now(),
                ),
            )
            return int(cur.lastrowid)


def get_backups_for_date(
    fecha_domingo: str, db_path: Optional[Path] = None
) -> List[Dict[str, Any]]:
    with _connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM workflow_backups WHERE fecha_domingo = ?
            ORDER BY created_at DESC
            """,
            (fecha_domingo,),
        ).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["original_paths"] = json.loads(data.get("original_paths") or "[]")
            result.append(data)
        return result
