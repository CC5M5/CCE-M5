"""Tests para src.web_admin.rate_limit.py."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from src.web_admin.rate_limit import LoginRateLimiter, _MemoryStorage


def fake_request(host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "client": (host, 12345),
        "headers": [],
    }
    return Request(scope)


def test_memory_storage_allows_initial_attempts() -> None:
    storage = _MemoryStorage(max_attempts=3, window_seconds=60, block_seconds=120)
    assert storage.is_blocked("user1") is False


def test_memory_storage_blocks_after_max_attempts(monkeypatch) -> None:
    storage = _MemoryStorage(max_attempts=3, window_seconds=60, block_seconds=120)
    storage.record_failure("user1")
    assert storage.is_blocked("user1") is False
    storage.record_failure("user1")
    assert storage.is_blocked("user1") is False
    storage.record_failure("user1")
    assert storage.is_blocked("user1") is True


def test_memory_storage_success_resets() -> None:
    storage = _MemoryStorage(max_attempts=3, window_seconds=60, block_seconds=120)
    storage.record_failure("user1")
    storage.record_failure("user1")
    storage.record_success("user1")
    assert storage.is_blocked("user1") is False


def test_memory_storage_window_resets(monkeypatch) -> None:
    storage = _MemoryStorage(max_attempts=3, window_seconds=60, block_seconds=120)
    storage.record_failure("user1")
    storage.record_failure("user1")

    now = time.monotonic()
    monkeypatch.setattr(storage, "_now", lambda: now + 61)
    assert storage.is_blocked("user1") is False

    # El siguiente fallo debe empezar una nueva ventana
    storage.record_failure("user1")
    assert storage.is_blocked("user1") is False


def test_login_rate_limiter_check_or_raise() -> None:
    storage = _MemoryStorage(max_attempts=2, window_seconds=60, block_seconds=120)
    limiter = LoginRateLimiter(storage=storage)

    req = fake_request()
    limiter.check_or_raise(req, "alice")

    storage.record_failure(limiter._key(req, "alice"))
    storage.record_failure(limiter._key(req, "alice"))

    with pytest.raises(HTTPException) as exc:
        limiter.check_or_raise(req, "alice")
    assert exc.value.status_code == 429


def test_login_rate_limiter_record_success() -> None:
    storage = _MemoryStorage(max_attempts=2, window_seconds=60, block_seconds=120)
    limiter = LoginRateLimiter(storage=storage)

    req = fake_request()
    storage.record_failure(limiter._key(req, "bob"))
    storage.record_failure(limiter._key(req, "bob"))
    limiter.record_success(req, "bob")
    assert storage.is_blocked(limiter._key(req, "bob")) is False


def test_login_rate_limiter_uses_redis_when_env(monkeypatch) -> None:
    import importlib
    from unittest.mock import patch

    fake_redis = MagicMock()
    fake_redis.get.return_value = None
    monkeypatch.setenv("CCE_ADMIN_REDIS_URL", "redis://localhost:6379/0")

    fake_module = MagicMock()
    fake_module.Redis.from_url.return_value = fake_redis

    # Recargar src.config primero para que settings.redis_url se actualice
    from src import config as core_config
    from src.web_admin import rate_limit as rl_mod

    importlib.reload(core_config)
    importlib.reload(rl_mod)

    with patch.dict("sys.modules", {"redis": fake_module}):
        limiter = rl_mod.LoginRateLimiter()
        req = fake_request()
        assert limiter.is_blocked(req, "charlie") is False
        limiter.record_failure(req, "charlie")
        assert fake_redis.pipeline.called
