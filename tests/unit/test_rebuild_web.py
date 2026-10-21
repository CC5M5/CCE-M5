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
