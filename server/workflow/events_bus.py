from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from server.events import publish as sse_publish

try:
    import ulid
except Exception:
    ulid = None


class WorkflowEventBus:
    def __init__(self, repository):
        self.repository = repository

    def new_event_id(self) -> str:
        if ulid is not None:
            return str(ulid.new())
        return uuid4().hex

    def emit(self, event_type: str, payload: dict[str, Any], *, publish_to_sse: bool = False) -> dict[str, Any]:
        event = dict(payload)
        event.setdefault("event_id", self.new_event_id())
        event.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        game_id = str(event.get("game_id") or "")
        self.repository.append_event(game_id, event_type, event)
        if publish_to_sse:
            sse_publish({"type": event_type, **event})
        return event
