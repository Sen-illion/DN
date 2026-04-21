# -*- coding: utf-8 -*-
"""SII (Scene + Image-index) text_id codec and trigger predicates.

Format: 3-character string `"0SI"`
  - position 0: literal "0" (sentinel)
  - position 1: scene digit S in [1..9]
  - position 2: image-index digit I in [1..9]

Examples (from spec):
  - "011" = scene 1, image 1
  - "023" = scene 2, image 3
  - "099" = scene 9, image 9 (legal)
  - "100" = rejected (first char must be "0")
  - "009" = rejected (scene must be 1..9)

Trigger rule:
  - Same scene: trigger next image when current.I - last.I == 2
  - Cross scene: never triggers here; the scene-switch path owns the reset
    and re-anchors at "0S1" of the new scene.

Note: a scene can hold up to 9 image-indexed texts, which is enough for the
spec's "<= 6 rounds per scene" with gap-of-2 triggers (max 5 images / scene).
"""
from __future__ import annotations

from typing import Tuple

# Module-level constant for the "fire next image when gap == this" rule.
# Kept here (not in config.py) because it is part of the ID semantics, not a
# tunable threshold; config.py exposes IMAGE_GAP that aliases this.
IMAGE_GAP_SII = 2


class InvalidTextId(ValueError):
    """Raised when a text_id does not satisfy the SII format."""


def parse_text_id(tid: str) -> Tuple[int, int]:
    """Parse a 3-char `"0SI"` string into (scene, image_index)."""
    if not isinstance(tid, str):
        raise InvalidTextId(f"text_id must be str, got {type(tid).__name__}")
    if len(tid) != 3 or not tid.isdigit():
        raise InvalidTextId(f"text_id must be 3 digits, got {tid!r}")
    if tid[0] != "0":
        raise InvalidTextId(f"text_id must start with '0', got {tid!r}")
    scene = int(tid[1])
    ii = int(tid[2])
    if scene < 1 or scene > 9:
        raise InvalidTextId(f"scene must be 1..9, got {scene} from {tid!r}")
    if ii < 1 or ii > 9:
        raise InvalidTextId(f"image_index must be 1..9, got {ii} from {tid!r}")
    return scene, ii


def format_text_id(scene: int, ii: int) -> str:
    """Render (scene, image_index) as a 3-char `"0SI"` string with validation."""
    if not (1 <= scene <= 9):
        raise InvalidTextId(f"scene out of range: {scene}")
    if not (1 <= ii <= 9):
        raise InvalidTextId(f"image_index out of range: {ii}")
    return f"0{scene}{ii}"


def next_text_id(scene_id: int, current_ii: int) -> str:
    """Return SII for ii+1 within the same scene. No cross-scene roll-over."""
    return format_text_id(scene_id, current_ii + 1)


def should_trigger_image(last_anchor: str, current: str) -> bool:
    """Return True iff a new image task should be triggered for `current`.

    Same scene: trigger when current.I - last.I == IMAGE_GAP_SII (==2).
    Different scene: never trigger here; the scene-switch path owns the reset.
    """
    last_scene, last_ii = parse_text_id(last_anchor)
    cur_scene, cur_ii = parse_text_id(current)
    if last_scene != cur_scene:
        return False
    return (cur_ii - last_ii) == IMAGE_GAP_SII


def next_anchor_after_scene_switch(new_scene: int) -> str:
    """First anchor in a freshly-switched scene is always `"0S1"`."""
    return format_text_id(new_scene, 1)
