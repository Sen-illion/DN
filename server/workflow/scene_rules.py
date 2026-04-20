from __future__ import annotations

from .ids import next_text_id
from .types import BranchState, OptionRef


def should_prepare_scene(turn_in_scene: int, threshold: int) -> bool:
    return turn_in_scene >= threshold



def next_scene_id(current_scene_id: int) -> int:
    return min(9, current_scene_id + 1)



def build_scene_option_refs(branch_id: str, labels: list[str]) -> list[OptionRef]:
    return [
        OptionRef(index=index, label=label, branch_id=f"{branch_id}.s{index + 1}")
        for index, label in enumerate(labels)
    ]



def create_scene_entry_branch(game_id: str, branch_id: str, scene_id: int, depth: int) -> BranchState:
    return BranchState(
        game_id=game_id,
        branch_id=branch_id,
        scene_id=scene_id,
        current_text_id=next_text_id(scene_id, None),
        depth=depth,
    )
