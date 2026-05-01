import copy
import json
from pathlib import Path
from typing import Any


ICLORA_WIDGET_INPUTS: dict[str, list[str | None]] = {
    "UNETLoader": ["unet_name", "weight_dtype"],
    "VAELoader": ["vae_name"],
    "DualCLIPLoader": ["clip_name1", "clip_name2", "type"],
    "LoraLoader": ["lora_name", "strength_model", "strength_clip"],
    "CLIPTextEncode": ["text"],
    "RandomNoise": ["noise_seed", None],
    "KSamplerSelect": ["sampler_name"],
    "BasicScheduler": ["scheduler", "steps", "denoise"],
    "FluxGuidance": ["guidance"],
    "EmptySD3LatentImage": ["width", "height", "batch_size"],
    "ModelSamplingFlux": ["max_shift", "base_shift", "width", "height"],
    "SaveImage": ["filename_prefix"],
}


def load_workflow(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_api_workflow(workflow: dict[str, Any]) -> bool:
    return "nodes" not in workflow and all(isinstance(value, dict) and "class_type" in value for value in workflow.values())


def format_iclora_prompt(row: dict[str, Any]) -> str:
    prompt = str(row.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(f"Sample {row.get('id', '<missing id>')} has empty prompt")
    if "[MOVIE-SHOTS]" in prompt:
        return prompt

    characters = row.get("characters") or []
    if isinstance(characters, str):
        characters = [characters]
    character_text = ", ".join(str(character).strip() for character in characters if str(character).strip())
    if not character_text:
        character_text = "the main character"
    scene = str(row.get("scene", "")).strip() or "the story world"
    context = str(row.get("story_context", "")).strip()
    context_text = f" with continuity from {context}" if context else ""

    return (
        f"[MOVIE-SHOTS] {prompt}, "
        f"[SCENE-1] establishing shot in {scene}{context_text}, cinematic lighting, "
        f"[SCENE-2] {character_text} in a clear character action, consistent identity and framing, "
        f"[SCENE-3] cinematic resolution of the moment, coherent visual continuity."
    )


def replace_prompt_seed_and_prefix(workflow: dict[str, Any], prompt: str, seed: int, filename_prefix: str | None = None) -> dict[str, Any]:
    data = copy.deepcopy(workflow)
    if is_api_workflow(data):
        for node in data.values():
            class_type = node.get("class_type")
            inputs = node.setdefault("inputs", {})
            if class_type == "CLIPTextEncode":
                inputs["text"] = prompt
            elif class_type == "RandomNoise":
                inputs["noise_seed"] = seed
            elif class_type in {"KSampler", "KSamplerAdvanced"}:
                inputs["seed"] = seed
            elif class_type == "SaveImage" and filename_prefix:
                inputs["filename_prefix"] = filename_prefix
        return data

    for node in data.get("nodes", []):
        widgets = node.get("widgets_values") or []
        node_type = node.get("type")
        if node_type == "CLIPTextEncode" and widgets:
            widgets[0] = prompt
        elif node_type == "RandomNoise" and widgets:
            widgets[0] = seed
            if len(widgets) > 1:
                widgets[1] = "fixed"
        elif node_type in {"KSampler", "KSamplerAdvanced"} and widgets:
            widgets[0] = seed
        elif node_type == "SaveImage" and widgets and filename_prefix:
            widgets[0] = filename_prefix
    return data


def _link_lookup(workflow: dict[str, Any]) -> dict[int, tuple[int, int]]:
    lookup: dict[int, tuple[int, int]] = {}
    for raw_link in workflow.get("links", []):
        link = raw_link.get("value") if isinstance(raw_link, dict) and "value" in raw_link else raw_link
        if not isinstance(link, list) or len(link) < 5:
            continue
        link_id, origin_id, origin_slot = int(link[0]), int(link[1]), int(link[2])
        lookup[link_id] = (origin_id, origin_slot)
    return lookup


def ui_workflow_to_api_prompt(workflow: dict[str, Any]) -> dict[str, Any]:
    if is_api_workflow(workflow):
        return copy.deepcopy(workflow)

    nodes = {int(node["id"]): node for node in workflow.get("nodes", [])}
    link_lookup = _link_lookup(workflow)
    primitive_values: dict[int, Any] = {
        node_id: node.get("widgets_values", [None])[0]
        for node_id, node in nodes.items()
        if node.get("type") == "PrimitiveNode" and node.get("widgets_values")
    }

    def linked_value(link_id: int) -> Any:
        origin_id, origin_slot = link_lookup[int(link_id)]
        if origin_id in primitive_values:
            return primitive_values[origin_id]
        return [str(origin_id), origin_slot]

    api_prompt: dict[str, Any] = {}
    for node_id, node in nodes.items():
        class_type = node.get("type")
        if class_type in {"Note", "PrimitiveNode"}:
            continue
        if node.get("mode") == 2:
            continue

        inputs: dict[str, Any] = {}
        for input_spec in node.get("inputs", []):
            link_id = input_spec.get("link")
            if link_id is not None:
                inputs[input_spec["name"]] = linked_value(int(link_id))

        widget_names = ICLORA_WIDGET_INPUTS.get(str(class_type), [])
        for index, value in enumerate(node.get("widgets_values") or []):
            if index >= len(widget_names):
                continue
            input_name = widget_names[index]
            if input_name and input_name not in inputs:
                inputs[input_name] = value

        api_prompt[str(node_id)] = {
            "class_type": class_type,
            "inputs": inputs,
        }
    return api_prompt


def resolve_workflow_path(repo_dir: str | Path, workflow: str | Path) -> Path:
    workflow_path = Path(workflow)
    if workflow_path.exists():
        return workflow_path
    repo_workflow_path = Path(repo_dir) / workflow_path
    if repo_workflow_path.exists():
        return repo_workflow_path
    raise FileNotFoundError(f"IC-LoRA workflow not found: {workflow_path} or {repo_workflow_path}")
