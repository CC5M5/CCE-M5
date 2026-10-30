"""Tests para src/rebuild_web.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from src import rebuild_web


def test_rebuild_web_success(monkeypatch) -> None:
    runs = []

    def fake_run(cmd, **kwargs):
        runs.append(cmd)
        return MagicMock(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)

    result = rebuild_web.rebuild_web()
    assert result == "rebuild OK"
    assert any("export_data_for_web.py" in str(c) for c in runs)
    assert any("npm" in str(c) for c in runs)
    assert any(
        "systemctl" in str(c) and "--user" in str(c) and "cce-m5-web.service" in str(c)
        for c in runs
    )
    # Verifica que se leyeron las variables de entorno parametrizadas.
    assert rebuild_web.PROJECT_DIR.is_dir()
    assert rebuild_web.NODE_BIN


def test_rebuild_web_export_fails(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        if "export_data_for_web.py" in str(cmd):
            raise rebuild_web.subprocess.CalledProcessError(
                1, cmd, output="", stderr="export failed"
            )
        return MagicMock(returncode=0)

    monkeypatch.setattr("subprocess.run", fake_run)
    result = rebuild_web.rebuild_web()
    assert "ERROR rebuild" in result
    assert "export failed" in result


def test_rebuild_web_usa_python_del_ambiente(monkeypatch) -> None:
    """El export debe usar el interprete del entorno, no python3 del sistema."""
    runs = []

    def fake_run(cmd, **kwargs):
        runs.append(cmd)
        return MagicMock(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(rebuild_web.sys, "executable", "/falso/.venv/bin/python")

    rebuild_web.rebuild_web()
    export_cmds = [c for c in runs if "export_data_for_web.py" in str(c)]
    assert len(export_cmds) == 1
    assert export_cmds[0][0] == "/falso/.venv/bin/python"


def test_rebuild_web_sin_systemctl(monkeypatch) -> None:
    """Sin systemctl no es error: la build quedó lista en web/dist."""

    def fake_run(cmd, **kwargs):
        if "systemctl" in str(cmd):
            raise FileNotFoundError("systemctl no disponible")
        return MagicMock(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = rebuild_web.rebuild_web()
    assert result == "rebuild OK (sin reinicio: systemctl no disponible)"


def test_rebuild_web_error_reinicio(monkeypatch) -> None:
    """Fallo al reiniciar reporta el error, sin marcar el rebuild como fallido."""

    def fake_run(cmd, **kwargs):
        if "systemctl" in str(cmd):
            raise rebuild_web.subprocess.CalledProcessError(
                1, cmd, output="", stderr="Failed to restart cce-m5-web.service: unit not found"
            )
        return MagicMock(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("subprocess.run", fake_run)
    result = rebuild_web.rebuild_web()
    assert result == "rebuild OK con error al reiniciar web: unit not found"
