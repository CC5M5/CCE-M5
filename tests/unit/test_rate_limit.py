"""Tests para src/web_admin/rate_limit.py."""

from __future__ import annotations

from fastapi import HTTPException
from src.web_admin.rate_limit import LoginRateLimiter, _MemoryStorage


class FakeRequest:
    def __init__(self, host: str = "127.0.0.1"):
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
