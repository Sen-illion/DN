from __future__ import annotations

from enum import Enum


class TextNodeStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    CONSUMED = "consumed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class ImageTaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    ABANDONED = "abandoned"


class BranchStatus(str, Enum):
    ACTIVE = "active"
    ABANDONED = "abandoned"
    COMPLETED = "completed"


class GameStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
