from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedTextId:
    scene_id: int
    image_index_in_scene: int


def parse_text_id(text_id: str) -> ParsedTextId:
    value = str(text_id or "").strip()
    if len(value) != 3 or not value.isdigit():
        raise ValueError(f"invalid text_id: {text_id}")
    scene_id = int(value[0])
    image_index = int(value[1:])
    if not 1 <= scene_id <= 9:
        raise ValueError(f"invalid scene_id in text_id: {text_id}")
    if not 1 <= image_index <= 99:
        raise ValueError(f"invalid image index in text_id: {text_id}")
    return ParsedTextId(scene_id=scene_id, image_index_in_scene=image_index)


def next_text_id(scene_id: int, current_ii: int | None) -> str:
    next_ii = 1 if current_ii is None else current_ii + 1
    if next_ii > 99:
        raise ValueError("scene text index exceeds 99")
    if not 1 <= int(scene_id) <= 9:
        raise ValueError("scene_id must be between 1 and 9")
    return f"{int(scene_id)}{next_ii:02d}"


def text_pk(game_id: str, text_id: str) -> str:
    return f"{game_id}_{text_id}"


def image_task_pk(game_id: str, anchor_text_id: str) -> str:
    return f"{game_id}_{anchor_text_id}_image"
