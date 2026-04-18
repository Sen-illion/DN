from __future__ import annotations

import threading
import time
from dataclasses import dataclass

try:
    import redis as redis_lib
except Exception:
    redis_lib = None


@dataclass
class LeaseResult:
    acquired: bool
    value: str | None = None


class InMemoryLeaseStore:
    def __init__(self):
        self._values: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def acquire(self, key: str, value: str, ttl_seconds: int) -> LeaseResult:
        now = time.time()
        with self._lock:
            self._cleanup(now)
            existing = self._values.get(key)
            if existing:
                return LeaseResult(acquired=False, value=existing[0])
            self._values[key] = (value, now + ttl_seconds)
            return LeaseResult(acquired=True, value=value)

    def release(self, key: str) -> None:
        with self._lock:
            self._values.pop(key, None)

    def mark_completed(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._values[key] = (value, time.time() + ttl_seconds)

    def get(self, key: str) -> str | None:
        with self._lock:
            self._cleanup(time.time())
            existing = self._values.get(key)
            return existing[0] if existing else None

    def _cleanup(self, now: float) -> None:
        expired = [key for key, (_, deadline) in self._values.items() if deadline <= now]
        for key in expired:
            self._values.pop(key, None)


class RedisLeaseStore(InMemoryLeaseStore):
    def __init__(self, client=None):
        super().__init__()
        self.client = client

    @classmethod
    def from_settings(cls, settings):
        if redis_lib is None:
            return cls(client=None)
        try:
            client = redis_lib.Redis.from_url(settings.broker_url)
            client.ping()
            return cls(client=client)
        except Exception:
            return cls(client=None)

    def acquire(self, key: str, value: str, ttl_seconds: int) -> LeaseResult:
        if self.client is None:
            return super().acquire(key, value, ttl_seconds)
        ok = self.client.set(key, value, nx=True, ex=ttl_seconds)
        if ok:
            return LeaseResult(acquired=True, value=value)
        existing = self.client.get(key)
        return LeaseResult(acquired=False, value=existing.decode('utf-8') if existing else None)

    def release(self, key: str) -> None:
        if self.client is None:
            super().release(key)
            return
        self.client.delete(key)

    def mark_completed(self, key: str, value: str, ttl_seconds: int) -> None:
        if self.client is None:
            super().mark_completed(key, value, ttl_seconds)
            return
        self.client.set(key, value, ex=ttl_seconds)

    def get(self, key: str) -> str | None:
        if self.client is None:
            return super().get(key)
        value = self.client.get(key)
        return value.decode('utf-8') if value else None
