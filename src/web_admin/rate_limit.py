"""Rate limiting simple en memoria para el panel de administración.

Soporta dos backends:
- In-memory (default): válido para una única instancia / LAN.
- Redis: requerido si el admin se replica o se expone a Internet.

Variables de entorno:
  CCE_ADMIN_RATE_LIMIT_MAX_ATTEMPTS (default 5)
  CCE_ADMIN_RATE_LIMIT_WINDOW_SECONDS (default 300)
  CCE_ADMIN_RATE_LIMIT_BLOCK_SECONDS (default 900)
  CCE_ADMIN_REDIS_URL (opcional, ej: redis://localhost:6379/0)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request

from src.config import settings

DEFAULT_MAX_ATTEMPTS = settings.rate_limit_max_attempts
DEFAULT_WINDOW_SECONDS = settings.rate_limit_window_seconds
DEFAULT_BLOCK_SECONDS = settings.rate_limit_block_seconds


class _Storage(Protocol):
    """Protocolo mínimo para backend de rate limiting."""

    def is_blocked(self, key: str) -> bool: ...

    def record_failure(self, key: str) -> None: ...

    def record_success(self, key: str) -> None: ...


@dataclass
class _Bucket:
    attempts: int = 0
    first_attempt_at: float = 0.0
    blocked_until: float = 0.0


class _MemoryStorage:
    """Backend en memoria (por defecto)."""

    def __init__(
        self,
        max_attempts: int,
        window_seconds: float,
        block_seconds: float,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds
        self._buckets: dict[str, _Bucket] = {}

    def _now(self) -> float:
        return time.monotonic()

    def is_blocked(self, key: str) -> bool:
        bucket = self._buckets.get(key)
        if not bucket:
            return False
        now = self._now()
        if bucket.blocked_until and now < bucket.blocked_until:
            return True
        if bucket.first_attempt_at and now - bucket.first_attempt_at > self.window_seconds:
            bucket.attempts = 0
            bucket.first_attempt_at = 0.0
            bucket.blocked_until = 0.0
        return False

    def record_failure(self, key: str) -> None:
        now = self._now()
        bucket = self._buckets.setdefault(key, _Bucket())
        if not bucket.first_attempt_at or now - bucket.first_attempt_at > self.window_seconds:
            bucket.attempts = 1
            bucket.first_attempt_at = now
            bucket.blocked_until = 0.0
        else:
            bucket.attempts += 1
            if bucket.attempts >= self.max_attempts:
                bucket.blocked_until = now + self.block_seconds

    def record_success(self, key: str) -> None:
        self._buckets.pop(key, None)


class _RedisStorage:
    """Backend Redis para rate limiting. Requiere `redis>=4.0`."""

    def __init__(
        self,
        url: str,
        max_attempts: int,
        window_seconds: float,
        block_seconds: float,
    ):
        from redis import Redis

        self._client = Redis.from_url(url)
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.block_seconds = block_seconds

    def _key(self, key: str, suffix: str) -> str:
        return f"cce-m5:ratelimit:{key}:{suffix}"

    def is_blocked(self, key: str) -> bool:
        block_until = self._client.get(self._key(key, "block_until"))
        return bool(block_until and float(block_until) > time.time())

    def record_failure(self, key: str) -> None:
        pipe = self._client.pipeline()
        attempts_key = self._key(key, "attempts")
        first_key = self._key(key, "first_attempt")
        pipe.get(attempts_key)
        pipe.get(first_key)
        results = pipe.execute()

        attempts = int(results[0] or 0)
        first = float(results[1] or 0)
        now = time.time()

        if not first or now - first > self.window_seconds:
            attempts = 1
            first = now
        else:
            attempts += 1

        pipe.setex(attempts_key, int(self.window_seconds) + 1, str(attempts))
        pipe.setex(first_key, int(self.window_seconds) + 1, str(first))
        if attempts >= self.max_attempts:
            pipe.setex(
                self._key(key, "block_until"),
                int(self.block_seconds) + 1,
                str(now + self.block_seconds),
            )
        pipe.execute()

    def record_success(self, key: str) -> None:
        pipe = self._client.pipeline()
        pipe.delete(self._key(key, "attempts"))
        pipe.delete(self._key(key, "first_attempt"))
        pipe.delete(self._key(key, "block_until"))
        pipe.execute()


class LoginRateLimiter:
    """Limitador de intentos de login por IP/username.

    Usa Redis si se define CCE_ADMIN_REDIS_URL; en caso contrario, memoria local.
    """

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        block_seconds: float = DEFAULT_BLOCK_SECONDS,
        storage: _Storage | None = None,
    ):
        if storage is None:
            redis_url = settings.redis_url
            if redis_url:
                storage = _RedisStorage(redis_url, max_attempts, window_seconds, block_seconds)
            else:
                storage = _MemoryStorage(max_attempts, window_seconds, block_seconds)
        self._storage = storage

    @staticmethod
    def _key(request: Request, username: str) -> str:
        client = request.client.host if request.client else "unknown"
        return f"{client}:{username.lower()}"

    def is_blocked(self, request: Request, username: str) -> bool:
        return self._storage.is_blocked(self._key(request, username))

    def record_failure(self, request: Request, username: str) -> None:
        self._storage.record_failure(self._key(request, username))

    def record_success(self, request: Request, username: str) -> None:
        self._storage.record_success(self._key(request, username))

    def check_or_raise(self, request: Request, username: str) -> None:
        if self.is_blocked(request, username):
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos fallidos. Espera unos minutos.",
            )

    def __call__(self, request: Request, username: str) -> None:
        self.check_or_raise(request, username)



class IPRateLimiter:
    """Rate limiting simple por IP para todo el tráfico HTTP."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._storage = _MemoryStorage(max_requests, window_seconds, block_seconds=window_seconds)

    def _key(self, request: Request) -> str:
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    def is_allowed(self, request: Request) -> bool:
        return not self._storage.is_blocked(self._key(request))

    def record(self, request: Request) -> None:
        self._storage.record_failure(self._key(request))

    def check_or_raise(self, request: Request) -> None:
        if not self.is_allowed(request):
            raise HTTPException(
                status_code=429,
                detail="Demasiadas peticiones desde esta IP. Espera un momento.",
            )
        self.record(request)
