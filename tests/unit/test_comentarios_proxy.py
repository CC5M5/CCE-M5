"""Tests para el proxy de comentarios (/comentarios)."""

import json
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.web_admin.api import crear_comentario
from src.web_admin.models import ComentarioRequest


def _payload() -> ComentarioRequest:
    return ComentarioRequest(
        nombre="Ana",
        email="ana@ejemplo.com",
        tipo="sugerencia",
        presentacion="2026-01-01",
        mensaje="Mensaje de prueba",
    )


def _fake_request(host: str) -> SimpleNamespace:
    """Stub de Request con solo lo que usa IPRateLimiter._key."""
    return SimpleNamespace(client=SimpleNamespace(host=host))


def _ok_urlopen(host: str):
    """urlopen falso que registra el body del issue en _captured."""
    captured: dict = {}

    class Resp:
        def read(self):
            return b'{"id": 123}'

    def fake_urlopen(req, timeout=None):
        assert "issues" in req.full_url
        captured["body"] = json.loads(req.data)["body"]
        return MagicMock(
            __enter__=MagicMock(return_value=Resp()),
            __exit__=MagicMock(return_value=False),
        )

    return fake_urlopen, captured


@pytest.mark.asyncio
async def test_comentario_sin_token_devuelve_503(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "")
    with pytest.raises(HTTPException) as exc_info:
        await crear_comentario(_fake_request("10.0.0.1"), _payload())
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_comentario_ok(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "fake-token")
    fake_urlopen, captured = _ok_urlopen("10.0.0.2")

    with patch("urllib.request.urlopen", fake_urlopen):
        result = await crear_comentario(_fake_request("10.0.0.2"), _payload())

    assert result["success"] is True
    # El issue público no expone el email del visitante (S2).
    assert "ana@ejemplo.com" not in captured["body"]
    assert "Ana" in captured["body"]


@pytest.mark.asyncio
async def test_comentario_github_error(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "fake-token")

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    with (
        patch("urllib.request.urlopen", fake_urlopen),
        pytest.raises(HTTPException) as exc_info,
    ):
        await crear_comentario(_fake_request("10.0.0.3"), _payload())

    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_comentarios_rate_limit_por_ip(monkeypatch):
    """Máximo 5 comentarios por IP en la ventana (S2); el 6.º recibe 429."""
    from src.config import settings
    from src.web_admin.rate_limit import IPRateLimiter

    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "fake-token")
    monkeypatch.setattr(
        "src.web_admin.api._comentarios_limiter",
        IPRateLimiter(
            max_requests=settings.comentarios_rate_limit_max,
            window_seconds=3600.0,
        ),
    )
    fake_urlopen, _ = _ok_urlopen("10.0.0.4")

    with patch("urllib.request.urlopen", fake_urlopen):
        for _ in range(5):
            result = await crear_comentario(_fake_request("10.0.0.4"), _payload())
            assert result["success"] is True

        with pytest.raises(HTTPException) as exc_info:
            await crear_comentario(_fake_request("10.0.0.4"), _payload())
        assert exc_info.value.status_code == 429


def test_comentarios_rate_limit_default():
    from src.config import Settings

    s = Settings(_env_file=None)
    assert s.comentarios_rate_limit_max == 5


def test_comentario_validacion_email_invalido():
    with pytest.raises(ValueError):
        ComentarioRequest(
            nombre="Ana",
            email="no-es-email",
            tipo="sugerencia",
            mensaje="Mensaje",
        )
