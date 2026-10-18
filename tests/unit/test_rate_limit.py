"""Tests para el rate limiting de login del admin."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request

from src.web_admin.rate_limit import LoginRateLimiter, _MemoryStorage


class FakeRequest:
    def __init__(self, host="127.0.0.1"):
        self.client = MagicMock()
        self.client.host = host


def test_memory_storage_blocks_after_max_attempts():
    storage = _MemoryStorage(max_attempts=3, window_seconds=60, block_seconds=60)
    assert storage.is_blocked("alice") is False
    storage.record_failure("alice")
    storage.record_failure("alice")
    assert storage.is_blocked("alice") is False
    storage.record_failure("alice")
    assert storage.is_blocked("alice") is True
    storage.record_success("alice")
    assert storage.is_blocked("alice") is False


def test_limiter_uses_ip_and_username():
    limiter = LoginRateLimiter(storage=_MemoryStorage(2, 60, 60))
    req = FakeRequest(host="10.0.0.1")
    limiter.record_failure(req, "user1")
    limiter.record_failure(req, "user1")
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_or_raise(req, "user1")
    assert exc_info.value.status_code == 429

    # Otro usuario en la misma IP no está bloqueado
    limiter.check_or_raise(req, "user2")


def test_limiter_success_resets_failures():
    storage = _MemoryStorage(2, 60, 60)
    limiter = LoginRateLimiter(storage=storage)
    req = FakeRequest()
    limiter.record_failure(req, "u")
    limiter.record_success(req, "u")
    limiter.check_or_raise(req, "u")  # no lanza
