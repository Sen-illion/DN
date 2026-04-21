# -*- coding: utf-8 -*-
"""Pure business triggers (no I/O, no globals).

These functions decide *what should happen* given current narrative state.
They do not enqueue jobs, write the DB, or call workers; callers in api.py
or workers do that. Keeping them pure makes them trivially unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .ids import (
    IMAGE_GAP_SII,
    format_text_id,
    next_anchor_after_scene_switch,
    parse_text_id,
    should_trigger_image,
)


@dataclass(frozen=True)
class ImageTriggerDecision:
    """Result of evaluating whether the next text should kick off an image."""
    should_trigger: bool
    anchor_text_id: Optional[str]  # the text the image will be anchored on
    reason: str


def evaluate_image_trigger(
    last_anchor_text_id: Optional[str],
    current_text_id: str,
) -> ImageTriggerDecision:
    """Map raw IDs to a structured trigger decision.

    Rules:
      - No prior anchor in this scene (first text after a switch / very first
        text): trigger immediately and use current_text_id as the anchor.
      - Same scene, gap == 2: trigger and use current_text_id as the anchor.
      - Otherwise: do not trigger.
    """
    cur_scene, _ = parse_text_id(current_text_id)

    if not last_anchor_text_id:
        return ImageTriggerDecision(True, current_text_id, "first-anchor-in-scene")

    last_scene, _ = parse_text_id(last_anchor_text_id)
    if last_scene != cur_scene:
        return ImageTriggerDecision(True, current_text_id, "scene-switched-reset")

    if should_trigger_image(last_anchor_text_id, current_text_id):
        return ImageTriggerDecision(True, current_text_id, "gap-equals-2")

    return ImageTriggerDecision(False, None, "gap-not-yet")


@dataclass(frozen=True)
class ChoicePruneDecision:
    """Output of on_user_choice: which branches to keep / abandon."""
    chosen_branch_id: str
    abandoned_branch_ids: List[str]


def on_user_choice(
    parent_text_id: str,
    sibling_branch_ids: List[str],
    chosen_branch_id: str,
) -> ChoicePruneDecision:
    """Compute the set of branches to abandon after a user choice.

    Pure: callers persist the abandonment + cancel jobs.
    Raises ValueError if chosen_branch_id is not in sibling_branch_ids.
    """
    if chosen_branch_id not in sibling_branch_ids:
        raise ValueError(
            f"chosen_branch_id={chosen_branch_id!r} not in siblings={sibling_branch_ids!r}"
        )
    abandoned = [b for b in sibling_branch_ids if b != chosen_branch_id]
    return ChoicePruneDecision(chosen_branch_id, abandoned)


@dataclass(frozen=True)
class SceneSwitchPlan:
    """What prepare_next_scene will request the workers to produce."""
    from_scene: int
    to_scene: int
    next_anchor_text_id: str  # S01 of the new scene


def plan_scene_switch(from_scene: int) -> SceneSwitchPlan:
    """Return the plan for switching from `from_scene` to `from_scene + 1`.

    Caller (scene_worker) is responsible for actually generating the candidate
    options + first text + first image; this function only produces the IDs.
    """
    if from_scene < 1 or from_scene >= 9:
        raise ValueError(f"cannot switch from scene {from_scene}: out of [1..8]")
    to_scene = from_scene + 1
    return SceneSwitchPlan(
        from_scene=from_scene,
        to_scene=to_scene,
        next_anchor_text_id=next_anchor_after_scene_switch(to_scene),
    )


def should_prepare_next_scene(rounds_in_scene: int, min_rounds: int, max_rounds: int) -> bool:
    """Trigger pre-generation of the next scene once we've had >= min_rounds.

    Hard-capped by max_rounds (the system MUST start preparing by then even
    if user has not finished the current scene).
    """
    if rounds_in_scene < 0:
        return False
    return rounds_in_scene >= min_rounds or rounds_in_scene >= max_rounds
