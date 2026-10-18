"""Tests para el proxy de comentarios (/comentarios)."""

import urllib.error
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


@pytest.mark.asyncio
async def test_comentario_sin_token_devuelve_503(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "")
    with pytest.raises(HTTPException) as exc_info:
        await crear_comentario(_payload())
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_comentario_ok(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "fake-token")

    class Resp:
        def read(self):
            return b'{"id": 123}'

    def fake_urlopen(req, timeout=None):
        assert "issues" in req.full_url
        return MagicMock(__enter__=MagicMock(return_value=Resp()), __exit__=MagicMock(return_value=False))

    with patch("urllib.request.urlopen", fake_urlopen):
        result = await crear_comentario(_payload())

    assert result["success"] is True


@pytest.mark.asyncio
async def test_comentario_github_error(monkeypatch):
    monkeypatch.setattr("src.web_admin.api.GITHUB_TOKEN_COMENTARIOS", "fake-token")

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    with patch("urllib.request.urlopen", fake_urlopen), pytest.raises(HTTPException) as exc_info:
        await crear_comentario(_payload())

    assert exc_info.value.status_code == 502


def test_comentario_validacion_email_invalido():
    with pytest.raises(ValueError):
        ComentarioRequest(
            nombre="Ana",
            email="no-es-email",
            tipo="sugerencia",
            mensaje="Mensaje",
        )
