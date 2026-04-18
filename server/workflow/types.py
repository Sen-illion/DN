from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import BranchStatus, GameStatus, ImageTaskStatus, TextNodeStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OptionRef:
    index: int
    label: str
    branch_id: str


@dataclass
class ImageDeps:
    prev_scene_image: str | None = None
    character_refs: list[str] = field(default_factory=list)
    scene_anchor: str | None = None
    new_scene_first_image: str | None = None


@dataclass
class TextNode:
    game_id: str
    text_id: str
    scene_id: int
    image_index_in_scene: int
    branch_id: str
    parent_text_id: str | None
    content: str
    options: list[OptionRef]
    status: str = TextNodeStatus.PENDING.value
    choice_index: int | None = None
    is_scene_entry: bool = False
    anchor_image_task_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass
class ImageTask:
    game_id: str
    anchor_text_id: str
    scene_id: int
    branch_id: str
    deps: ImageDeps
    status: str = ImageTaskStatus.PENDING.value
    retry_count: int = 0
    error: str | None = None
    result_url: str | None = None
    cancel_requested: bool = False
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass
class BranchState:
    game_id: str
    branch_id: str
    scene_id: int
    status: str = BranchStatus.ACTIVE.value
    current_text_id: str | None = None
    last_anchor_text_id: str | None = None
    last_scene_image_id: str | None = None
    depth: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data


@dataclass
class GameState:
    game_id: str
    active_branch_id: str
    current_scene_id: int
    turn_in_scene: int
    scene_switch_threshold: int
    status: str = GameStatus.ACTIVE.value
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
