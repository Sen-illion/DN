from __future__ import annotations

from pathlib import Path

from .ids import parse_text_id
from .types import ImageDeps


def should_trigger_image(last_anchor_text_id: str | None, current_text_id: str) -> bool:
    current = parse_text_id(current_text_id)
    if not last_anchor_text_id:
        return current.image_index_in_scene == 1

    last = parse_text_id(last_anchor_text_id)
    if current.scene_id != last.scene_id:
        return current.image_index_in_scene == 1
    return current.image_index_in_scene - last.image_index_in_scene == 2



def collect_character_refs(game_id: str) -> list[str]:
    refs: list[str] = []
    main_ref = Path("initial") / "main_character" / game_id / "main_character.png"
    if main_ref.exists():
        refs.append(str(main_ref).replace("\\", "/"))
    support_dir = Path("initial") / "character_references" / game_id
    if support_dir.exists():
        for item in sorted(support_dir.glob("*.png")):
            refs.append(str(item).replace("\\", "/"))
    return refs



def build_image_deps(
    game_id: str,
    *,
    prev_scene_image: str | None,
    scene_anchor: str | None,
    new_scene_first_image: str | None = None,
) -> ImageDeps:
    return ImageDeps(
        prev_scene_image=prev_scene_image,
        character_refs=collect_character_refs(game_id),
        scene_anchor=scene_anchor,
        new_scene_first_image=new_scene_first_image,
    )
