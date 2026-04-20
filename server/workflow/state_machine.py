from __future__ import annotations

from .enums import ImageTaskStatus, TextNodeStatus

_TEXT_TRANSITIONS = {
    TextNodeStatus.PENDING.value: {TextNodeStatus.GENERATING.value, TextNodeStatus.ABANDONED.value},
    TextNodeStatus.GENERATING.value: {
        TextNodeStatus.READY.value,
        TextNodeStatus.FAILED.value,
        TextNodeStatus.ABANDONED.value,
    },
    TextNodeStatus.READY.value: {
        TextNodeStatus.CONSUMED.value,
        TextNodeStatus.ABANDONED.value,
    },
    TextNodeStatus.CONSUMED.value: set(),
    TextNodeStatus.ABANDONED.value: set(),
    TextNodeStatus.FAILED.value: set(),
}

_IMAGE_TRANSITIONS = {
    ImageTaskStatus.PENDING.value: {ImageTaskStatus.QUEUED.value, ImageTaskStatus.ABANDONED.value},
    ImageTaskStatus.QUEUED.value: {ImageTaskStatus.GENERATING.value, ImageTaskStatus.ABANDONED.value},
    ImageTaskStatus.GENERATING.value: {
        ImageTaskStatus.READY.value,
        ImageTaskStatus.FAILED.value,
        ImageTaskStatus.ABANDONED.value,
    },
    ImageTaskStatus.READY.value: set(),
    ImageTaskStatus.FAILED.value: set(),
    ImageTaskStatus.ABANDONED.value: set(),
}


def ensure_text_transition(old_status: str, new_status: str) -> None:
    allowed = _TEXT_TRANSITIONS.get(old_status, set())
    if new_status not in allowed and old_status != new_status:
        raise ValueError(f"invalid TextNode transition: {old_status} -> {new_status}")



def ensure_image_transition(old_status: str, new_status: str) -> None:
    allowed = _IMAGE_TRANSITIONS.get(old_status, set())
    if new_status not in allowed and old_status != new_status:
        raise ValueError(f"invalid ImageTask transition: {old_status} -> {new_status}")
