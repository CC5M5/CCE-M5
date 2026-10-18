"""Tests para src/web_admin/database.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.web_admin import database as db


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "admin_test.sqlite3"


@pytest.fixture
def db_path(tmp_db_path: Path) -> Path:
    db.init_admin_schema(tmp_db_path)
    return tmp_db_path


def test_init_admin_schema_creates_tables(tmp_db_path: Path) -> None:
    db.init_admin_schema(tmp_db_path)
    conn = db._connection(tmp_db_path)
    tables = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "admin_users" in tables
    assert "workflow_runs" in tables
    assert "workflow_logs" in tables
    assert "workflow_backups" in tables


def test_user_crud(db_path: Path) -> None:
    user_id = db.create_user(
        "testuser", "hashed", full_name="Test User", role="viewer", db_path=db_path
    )
    assert user_id == 1

    user = db.get_user_by_username("testuser", db_path=db_path)
    assert user is not None
    assert user.username == "testuser"
    assert user.full_name == "Test User"
    assert user.role == "viewer"
    assert user.is_active is True

    by_id = db.get_user_by_id(user_id, db_path=db_path)
    assert by_id is not None
    assert by_id.username == "testuser"

    db.update_user(user_id, full_name="Updated", role="admin", is_active=False, db_path=db_path)
    updated = db.get_user_by_id(user_id, db_path=db_path)
    assert updated is not None
    assert updated.full_name == "Updated"
    assert updated.role == "admin"
    assert updated.is_active is False

    db.set_user_password(user_id, "newhash", db_path=db_path)
    with_pass = db.get_user_by_id(user_id, db_path=db_path)
    assert with_pass is not None
    assert with_pass.password_hash == "newhash"

    db.delete_user(user_id, db_path=db_path)
    assert db.get_user_by_id(user_id, db_path=db_path) is None


def test_count_admins_and_list_users(db_path: Path) -> None:
    db.create_user("admin1", "h", role="admin", db_path=db_path)
    db.create_user("admin2", "h", role="admin", db_path=db_path)
    db.create_user("viewer1", "h", role="viewer", db_path=db_path)

    assert db.count_admins(db_path=db_path) == 2
    users = db.list_users(db_path=db_path)
    assert len(users) == 3
    usernames = {u["username"] for u in users}
    assert usernames == {"admin1", "admin2", "viewer1"}

    # Desactivar un admin reduce el conteo
    db.update_user(1, is_active=False, db_path=db_path)
    assert db.count_admins(db_path=db_path) == 1


def test_workflow_lifecycle(db_path: Path) -> None:
    wid = db.create_workflow_run("2026-01-01", created_by="tester", db_path=db_path)
    assert wid == 1

    run = db.get_workflow_run(wid, db_path=db_path)
    assert run is not None
    assert run["fecha_domingo"] == "2026-01-01"
    assert run["status"] == "init"
    assert run["steps_data"] == {}

    latest = db.get_latest_workflow_run("2026-01-01", db_path=db_path)
    assert latest is not None
    assert latest["id"] == wid

    db.update_workflow_step(
        wid, status="running", current_step="fetch_lectures", db_path=db_path
    )
    updated = db.get_workflow_run(wid, db_path=db_path)
    assert updated["status"] == "running"
    assert updated["current_step"] == "fetch_lectures"

    db.add_workflow_log(wid, "fetch_lectures", "todo OK", db_path=db_path)
    logs = db.get_workflow_logs(wid, db_path=db_path)
    assert len(logs) == 1
    assert logs[0]["message"] == "todo OK"

    listed = db.list_workflow_runs(db_path=db_path)
    assert len(listed) == 1


def test_workflow_steps_helpers(db_path: Path) -> None:
    assert db.step_index("init") == 0
    assert db.step_index("fetch_lectures") == 1
    assert db.step_index("desconocido") == -1

    assert db.next_step("init") == "fetch_lectures"
    assert db.next_step("done") is None

    wid = db.create_workflow_run("2026-02-01", db_path=db_path)
    db.goto_workflow_step(wid, "verify_lectures", db_path=db_path)
    run = db.get_workflow_run(wid, db_path=db_path)
    assert run["current_step"] == "verify_lectures"
    assert run["status"] == "verify_lectures"

    with pytest.raises(ValueError):
        db.goto_workflow_step(wid, "paso_inexistente", db_path=db_path)


def test_supersede_and_backups(db_path: Path) -> None:
    old = db.create_workflow_run("2026-03-01", db_path=db_path)
    new = db.create_workflow_run("2026-03-01", db_path=db_path)

    db.supersede_workflow_run(old, new, db_path=db_path)
    old_run = db.get_workflow_run(old, db_path=db_path)
    assert old_run["superseded_by"] == new
    assert old_run["status"] == "superseded"

    db.create_backup_record(new, "2026-03-01", "/tmp/backup.zip", ["a.pptx", "b.pdf"], db_path=db_path)
    backups = db.get_backups_for_date("2026-03-01", db_path=db_path)
    assert len(backups) == 1
    assert backups[0]["backup_path"] == "/tmp/backup.zip"
    assert backups[0]["original_paths"] == ["a.pptx", "b.pdf"]
