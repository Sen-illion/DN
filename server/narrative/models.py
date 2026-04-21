# -*- coding: utf-8 -*-
"""Dataclasses for the narrative v2 system + JSON Schema constants.

These are pure data containers; serialization helpers (`to_dict` /
`from_row`) are intentionally minimal so `store.py` can map them to
SQLite rows without circular deps.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Status enums (kept as bare string constants so SQLite text columns map 1:1)
# ---------------------------------------------------------------------------

class TextStatus:
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    CONSUMED = "consumed"
    ABANDONED = "abandoned"
    FAILED = "failed"

    ALL = (PENDING, GENERATING, READY, CONSUMED, ABANDONED, FAILED)
    TERMINAL = (CONSUMED, ABANDONED, FAILED)


class ImageStatus:
    PENDING = "pending"
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    ABANDONED = "abandoned"

    ALL = (PENDING, QUEUED, GENERATING, READY, FAILED, ABANDONED)
    TERMINAL = (READY, FAILED, ABANDONED)


class BranchStatus:
    ACTIVE = "active"
    ABANDONED = "abandoned"
    COMPLETED = "completed"

    ALL = (ACTIVE, ABANDONED, COMPLETED)
    TERMINAL = (ABANDONED, COMPLETED)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TextNode:
    game_id: str
    text_id: str                  # SII format, e.g. "011"
    scene_id: int                 # 1..9
    image_index_in_scene: int     # 1..9 (== int(text_id[2]))
    branch_id: str
    parent_text_id: Optional[str]
    content: str = ""
    options: List[str] = field(default_factory=list)
    status: str = TextStatus.PENDING
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    @property
    def pk(self) -> str:
        return f"{self.game_id}_{self.text_id}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageDeps:
    """Dependency bundle the image worker needs to render an anchor image."""
    prev_scene_image: Optional[str] = None      # url / path of last image in prior scene
    character_refs: List[str] = field(default_factory=list)
    scene_anchor: Optional[str] = None          # the scene's first/anchor image, if any

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImageTask:
    game_id: str
    anchor_text_id: str
    scene_id: int
    deps: ImageDeps = field(default_factory=ImageDeps)
    status: str = ImageStatus.PENDING
    retry_count: int = 0
    error: Optional[str] = None
    idempotency_key: str = ""
    branch_id: str = ""
    image_url: Optional[str] = None
    prompt: Optional[str] = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    @property
    def pk(self) -> str:
        return f"{self.game_id}_{self.anchor_text_id}_image"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class BranchState:
    game_id: str
    branch_id: str
    parent_branch_id: Optional[str]
    scene_id: int
    root_text_id: str
    status: str = BranchStatus.ACTIVE
    created_at: str = field(default_factory=_now_iso)

    @property
    def pk(self) -> str:
        return f"{self.game_id}_{self.branch_id}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# JSON Schema constants (informational; consumed by API docs / payload checks)
# ---------------------------------------------------------------------------

TEXT_NODE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "game_id", "text_id", "scene_id", "image_index_in_scene",
        "branch_id", "status", "created_at", "updated_at",
    ],
    "properties": {
        "game_id": {"type": "string"},
        "text_id": {"type": "string", "pattern": "^0[1-9][1-9]$"},
        "scene_id": {"type": "integer", "minimum": 1, "maximum": 9},
        "image_index_in_scene": {"type": "integer", "minimum": 1, "maximum": 9},
        "branch_id": {"type": "string"},
        "parent_text_id": {"type": ["string", "null"]},
        "content": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
        "status": {"type": "string", "enum": list(TextStatus.ALL)},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
    },
}

IMAGE_TASK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": [
        "game_id", "anchor_text_id", "scene_id", "deps",
        "status", "retry_count", "idempotency_key",
    ],
    "properties": {
        "game_id": {"type": "string"},
        "anchor_text_id": {"type": "string", "pattern": "^0[1-9][1-9]$"},
        "scene_id": {"type": "integer", "minimum": 1, "maximum": 9},
        "deps": {
            "type": "object",
            "properties": {
                "prev_scene_image": {"type": ["string", "null"]},
                "character_refs": {"type": "array", "items": {"type": "string"}},
                "scene_anchor": {"type": ["string", "null"]},
            },
        },
        "status": {"type": "string", "enum": list(ImageStatus.ALL)},
        "retry_count": {"type": "integer", "minimum": 0},
        "error": {"type": ["string", "null"]},
        "idempotency_key": {"type": "string"},
        "branch_id": {"type": "string"},
        "image_url": {"type": ["string", "null"]},
        "prompt": {"type": ["string", "null"]},
    },
}

BRANCH_STATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["game_id", "branch_id", "scene_id", "root_text_id", "status"],
    "properties": {
        "game_id": {"type": "string"},
        "branch_id": {"type": "string"},
        "parent_branch_id": {"type": ["string", "null"]},
        "scene_id": {"type": "integer", "minimum": 1, "maximum": 9},
        "root_text_id": {"type": "string", "pattern": "^0[1-9][1-9]$"},
        "status": {"type": "string", "enum": list(BranchStatus.ALL)},
        "created_at": {"type": "string", "format": "date-time"},
    },
}


# ---------------------------------------------------------------------------
# Serialization helpers shared by store.py
# ---------------------------------------------------------------------------

def options_to_json(opts: List[str]) -> str:
    return json.dumps(list(opts or []), ensure_ascii=False)


def options_from_json(s: Optional[str]) -> List[str]:
    if not s:
        return []
    try:
        return list(json.loads(s))
    except Exception:
        return []


def deps_to_json(deps: Optional[ImageDeps]) -> str:
    if deps is None:
        return json.dumps({}, ensure_ascii=False)
    return json.dumps(deps.to_dict(), ensure_ascii=False)


def deps_from_json(s: Optional[str]) -> ImageDeps:
    if not s:
        return ImageDeps()
    try:
        d = json.loads(s) or {}
    except Exception:
        return ImageDeps()
    return ImageDeps(
        prev_scene_image=d.get("prev_scene_image"),
        character_refs=list(d.get("character_refs") or []),
        scene_anchor=d.get("scene_anchor"),
    )
