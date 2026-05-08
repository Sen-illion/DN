import json
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path


_LIMIT_ENV = {
    "llm": "DN_LLM_MAX_CONCURRENCY",
    "image": "DN_IMAGE_MAX_CONCURRENCY",
}

_DEFAULT_LIMIT = {
    "llm": 2,
    "image": 1,
}

_PRIORITY_ORDER = {
    "high": 0,
    "normal": 1,
    "low": 2,
}

_GATES = {}
_GATE_LOCK = threading.Lock()
_LOG_LOCK = threading.Lock()
_LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "provider_events.jsonl"
_THREAD_STATE = threading.local()
_BACKOFFS = {}
_BACKOFF_LOCK = threading.Lock()


def _get_low_priority_reserve(kind: str, limit: int) -> int:
    raw = os.getenv(f"DN_{kind.upper()}_LOW_PRIORITY_RESERVE", "").strip()
    try:
        reserve = int(raw) if raw else 1
    except ValueError:
        reserve = 1
    if limit <= 1:
        return 0
    return max(0, min(limit - 1, reserve))


class PriorityGate:
    def __init__(self, limit: int, low_priority_reserve: int = 0):
        self.limit = limit
        self.low_priority_reserve = max(0, min(limit - 1, low_priority_reserve))
        self.inflight = 0
        self.waiting = {name: 0 for name in _PRIORITY_ORDER}
        self.cond = threading.Condition()

    def acquire(self, priority: str):
        with self.cond:
            self.waiting[priority] += 1
            try:
                while True:
                    effective_limit = self.limit
                    if priority == "low" and self.low_priority_reserve > 0:
                        effective_limit = max(1, self.limit - self.low_priority_reserve)
                    has_capacity = self.inflight < effective_limit
                    blocked_by_higher = any(
                        self.waiting[name] > 0
                        for name, rank in _PRIORITY_ORDER.items()
                        if rank < _PRIORITY_ORDER[priority]
                    )
                    if has_capacity and not blocked_by_higher:
                        self.inflight += 1
                        return
                    self.cond.wait()
            finally:
                self.waiting[priority] -= 1

    def release(self):
        with self.cond:
            if self.inflight > 0:
                self.inflight -= 1
            self.cond.notify_all()

    def snapshot(self):
        with self.cond:
            return {
                "limit": self.limit,
                "low_priority_reserve": self.low_priority_reserve,
                "inflight": self.inflight,
                "waiting": dict(self.waiting),
            }


def _normalize_priority(priority: str | None) -> str:
    if not priority:
        return getattr(_THREAD_STATE, "provider_priority", "high")
    priority = str(priority).strip().lower()
    return priority if priority in _PRIORITY_ORDER else "high"


def _get_limit(kind: str) -> int:
    env_name = _LIMIT_ENV.get(kind, "")
    raw = os.getenv(env_name, "").strip() if env_name else ""
    try:
        value = int(raw) if raw else _DEFAULT_LIMIT.get(kind, 1)
    except ValueError:
        value = _DEFAULT_LIMIT.get(kind, 1)
    return max(1, value)


def _get_gate(kind: str) -> PriorityGate:
    with _GATE_LOCK:
        state = _GATES.get(kind)
        limit = _get_limit(kind)
        if state is None or state["limit"] != limit:
            state = {
                "limit": limit,
                "gate": PriorityGate(limit, _get_low_priority_reserve(kind, limit)),
            }
            _GATES[kind] = state
        return state["gate"]


def get_provider_snapshot(kind: str) -> dict:
    gate = _get_gate(kind)
    snapshot = gate.snapshot()
    snapshot["kind"] = kind
    return snapshot


def set_provider_backoff(
    kind: str,
    provider: str,
    wait_seconds: float,
    reason: str,
    request_type: str = "",
    **extra,
) -> float:
    wait_seconds = max(0.0, float(wait_seconds))
    if wait_seconds <= 0:
        return 0.0
    now = time.time()
    until = now + wait_seconds
    key = (kind, provider)
    with _BACKOFF_LOCK:
        current = _BACKOFFS.get(key)
        previous_until = current["until"] if current else 0.0
        if until <= previous_until:
            return max(0.0, previous_until - now)
        _BACKOFFS[key] = {
            "until": until,
            "reason": reason,
            "request_type": request_type,
        }
    log_provider_event(
        kind,
        provider,
        request_type or "shared",
        "shared_backoff_set",
        wait_seconds=round(wait_seconds, 2),
        reason=reason,
        **extra,
    )
    return wait_seconds


def wait_for_provider_backoff(kind: str, provider: str, request_type: str = "") -> int:
    key = (kind, provider)
    total_wait = 0.0
    while True:
        with _BACKOFF_LOCK:
            current = _BACKOFFS.get(key)
            if not current:
                return int(total_wait * 1000)
            remaining = current["until"] - time.time()
            if remaining <= 0:
                _BACKOFFS.pop(key, None)
                return int(total_wait * 1000)
        sleep_s = min(max(remaining, 0.0), 5.0)
        time.sleep(sleep_s)
        total_wait += sleep_s


def log_provider_event(kind: str, provider: str, request_type: str, status: str, **extra) -> None:
    payload = {
        "ts": time.time(),
        "kind": kind,
        "provider": provider,
        "request_type": request_type,
        "status": status,
        "thread": threading.current_thread().name,
    }
    payload.update(extra)
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False)
        with _LOG_LOCK:
            with _LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except Exception:
        pass


@contextmanager
def provider_priority(priority: str):
    previous = getattr(_THREAD_STATE, "provider_priority", "high")
    _THREAD_STATE.provider_priority = _normalize_priority(priority)
    try:
        yield
    finally:
        _THREAD_STATE.provider_priority = previous


def set_provider_priority(priority: str) -> None:
    _THREAD_STATE.provider_priority = _normalize_priority(priority)


@contextmanager
def provider_request_slot(kind: str, provider: str, request_type: str, priority: str | None = None, **metadata):
    gate = _get_gate(kind)
    resolved_priority = _normalize_priority(priority)
    shared_backoff_wait_ms = wait_for_provider_backoff(kind, provider, request_type=request_type)
    queued_at = time.time()
    gate.acquire(resolved_priority)
    started_at = time.time()
    queue_wait_ms = int((started_at - queued_at) * 1000)
    log_provider_event(
        kind,
        provider,
        request_type,
        "acquired",
        priority=resolved_priority,
        queue_wait_ms=queue_wait_ms,
        shared_backoff_wait_ms=shared_backoff_wait_ms,
        concurrency_limit=_get_limit(kind),
        **metadata,
    )
    try:
        yield {
            "queued_at": queued_at,
            "started_at": started_at,
            "queue_wait_ms": queue_wait_ms,
            "shared_backoff_wait_ms": shared_backoff_wait_ms,
            "priority": resolved_priority,
        }
    finally:
        gate.release()
