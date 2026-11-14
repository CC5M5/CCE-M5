"""Tests para src/web_admin/rate_limit.py."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from src.web_admin.rate_limit import LoginRateLimiter, _MemoryStorage


class FakeRequest:
    def __init__(self, host: str = "127.0.0.1"):
        self.client = type("Client", (), {"host": host})()


class FakePathRequest:
    """Petición falsa con ruta, para probar el middleware de rate limit IP."""

    def __init__(self, path: str, host: str = "127.0.0.1"):
        self.url = type("URL", (), {"path": path})()
        self.client = type("Client", (), {"host": host})()


def test_memory_storage_block_after_max() -> None:
    storage = _MemoryStorage(max_attempts=2, window_seconds=300, block_seconds=900)
    key = "127.0.0.1:user"
    storage.record_failure(key)
    assert not storage.is_blocked(key)
    storage.record_failure(key)
    assert storage.is_blocked(key)


def test_memory_storage_success_resets() -> None:
    storage = _MemoryStorage(max_attempts=2, window_seconds=300, block_seconds=900)
    key = "127.0.0.1:user"
    storage.record_failure(key)
    storage.record_success(key)
    assert not storage.is_blocked(key)


def test_login_rate_limiter_raises_when_blocked() -> None:
    storage = _MemoryStorage(max_attempts=2, window_seconds=300, block_seconds=900)
    req = FakeRequest()
    key = LoginRateLimiter._key(req, "user")
    storage.record_failure(key)
    storage.record_failure(key)
    assert storage.is_blocked(key)
    limiter = LoginRateLimiter(storage=storage)
    try:
        limiter.check_or_raise(req, "user")
        raise AssertionError("Debería haber lanzado 429")
    except HTTPException as exc:
        assert exc.status_code == 429


def test_login_rate_limiter_not_blocked() -> None:
    storage = _MemoryStorage(max_attempts=5, window_seconds=300, block_seconds=900)
    limiter = LoginRateLimiter(storage=storage)
    req = FakeRequest()
    limiter.check_or_raise(req, "user")  # no raise


def test_login_rate_limiter_call() -> None:
    storage = _MemoryStorage(max_attempts=5, window_seconds=300, block_seconds=900)
    limiter = LoginRateLimiter(storage=storage)
    req = FakeRequest()
    limiter(req, "user")  # no raise


def _llamar_middleware(api, path: str):
    """Invoca el middleware de rate limit IP con una petición falsa."""

    async def call_next(request):
        return "ok"

    return asyncio.run(api.ip_rate_limit_middleware(FakePathRequest(path), call_next))


def test_ip_middleware_excluye_assets_del_editor(monkeypatch) -> None:
    """Los assets del editor (miniaturas y lema) no consumen cuota del limitador IP.

    Regresión del bug 429: la página del editor cargaba 123 miniaturas y el
    limitador global (120/min) bloqueaba la selección de cualquier diapositiva.
    """
    from src.web_admin import api
    from src.web_admin.rate_limit import IPRateLimiter

    limiter = IPRateLimiter(max_requests=1, window_seconds=60)
    monkeypatch.setattr(api, "_ip_rate_limiter", limiter)

    assert _llamar_middleware(api, "/editor-diapositivas/__ilustraciones/a/b.png") == "ok"
    assert _llamar_middleware(api, "/editor-diapositivas/__lema/lema_somos_uno.jpg") == "ok"

    # Las páginas del editor sí consumen cuota (max_requests=1: la petición
    # que alcanza el máximo aún pasa y la siguiente queda bloqueada).
    assert _llamar_middleware(api, "/editor-diapositivas/slides/102") == "ok"
    assert _llamar_middleware(api, "/editor-diapositivas/slides/102") == "ok"
    bloqueada = _llamar_middleware(api, "/editor-diapositivas/slides/102")
    assert isinstance(bloqueada, JSONResponse)
    assert bloqueada.status_code == 429


def test_ip_middleware_exclusiones_previas_se_mantienen(monkeypatch) -> None:
    """Las exclusiones existentes (/health, /admin, /static) siguen sin consumir cuota."""
    from src.web_admin import api
    from src.web_admin.rate_limit import IPRateLimiter

    limiter = IPRateLimiter(max_requests=1, window_seconds=60)
    monkeypatch.setattr(api, "_ip_rate_limiter", limiter)

    assert _llamar_middleware(api, "/health") == "ok"
    assert _llamar_middleware(api, "/admin/panel") == "ok"
    assert _llamar_middleware(api, "/static/app.js") == "ok"

    # Ninguna exclusión consumió cuota: la primera petición real aún pasa.
    assert _llamar_middleware(api, "/editor-diapositivas/slides/1") == "ok"
