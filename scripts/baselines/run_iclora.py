"""Run IC-LoRA workflow generation or readiness probes on DN-style prompts."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from baseline_io import repo_root

from baseline_io import (
    DEFAULT_NEXT_TURN_ACTION,
    build_input_bundle,
    build_next_turn_prompt,
    build_playable_image_result,
    build_visual_prompts,
    common_parser,
    environment_payload,
    load_subset,
    make_run_dir,
    result_payload,
    summarize_results,
    write_json,
)


BASELINE = "ic-lora"
WORKFLOW_PATH_MAP = {
    "UNETLoader": "models/unet",
    "DualCLIPLoader": "models/clip",
    "VAELoader": "models/vae",
    "LoraLoader": "models/loras",
}
LORA_ALIAS_MAP = {
    "movie-shots.safetensors": "film-storyboard.safetensors",
}


def resolve_repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root() / path


def workflow_requirements(workflow_path: Path) -> list[dict]:
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    requirements: list[dict] = []
    for node in data.get("nodes", []):
        node_type = node.get("type")
        widgets = node.get("widgets_values") or []
        model_dir = WORKFLOW_PATH_MAP.get(node_type)
        if not model_dir:
            continue
        filenames = [value for value in widgets if isinstance(value, str) and value.endswith(".safetensors")]
        for filename in filenames:
            requirements.append(
                {
                    "node_id": node.get("id"),
                    "node_type": node_type,
                    "filename": filename,
                    "relative_dir": model_dir,
                }
            )
    return requirements


def asset_inventory(comfyui_root: Path, requirements: list[dict]) -> tuple[list[dict], list[dict]]:
    inventory: list[dict] = []
    missing: list[dict] = []
    for req in requirements:
        absolute_path = comfyui_root / req["relative_dir"] / req["filename"]
        row = dict(req)
        row["absolute_path"] = str(absolute_path)
        row["exists"] = absolute_path.exists()
        alias_name = LORA_ALIAS_MAP.get(req["filename"])
        if not row["exists"] and alias_name:
            alias_path = comfyui_root / req["relative_dir"] / alias_name
            if alias_path.exists():
                row["resolved_via_alias"] = alias_name
                row["absolute_path"] = str(alias_path)
                row["exists"] = True
        if row["exists"]:
            row["size_bytes"] = Path(row["absolute_path"]).stat().st_size
        else:
            missing.append(row)
        inventory.append(row)
    return inventory, missing


def probe_comfyui(url: str | None) -> dict:
    if not url:
        return {"configured": False, "reachable": False}
    target = url.rstrip("/") + "/system_stats"
    try:
        with urllib.request.urlopen(target, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return {
            "configured": True,
            "reachable": True,
            "url": url,
            "device_count": len(payload.get("devices") or []),
            "system": payload.get("system"),
        }
    except urllib.error.URLError as exc:
        return {"configured": True, "reachable": False, "url": url, "error": f"{type(exc).__name__}: {exc}"}


def blocker_message(workflow_path: Path, comfyui_root: Path, missing_assets: list[dict], comfy_probe: dict) -> str:
    reasons: list[str] = []
    if not workflow_path.exists():
        reasons.append(f"workflow missing: {workflow_path}")
    if missing_assets:
        names = ", ".join(asset["filename"] for asset in missing_assets)
        reasons.append(f"missing workflow assets under {comfyui_root}: {names}")
    if comfy_probe.get("configured") and not comfy_probe.get("reachable"):
        reasons.append(f"ComfyUI API unreachable: {comfy_probe.get('error')}")
    if not reasons:
        reasons.append("workflow/assets look present, but DN runner does not execute ComfyUI graph yet")
    return "; ".join(reasons)


def normalize_storyboard_prompt(item: dict[str, Any], prompt_pack: dict[str, Any], *, prompt_override: str | None = None) -> str:
    theme = item.get("theme", "DN benchmark")
    if prompt_override:
        prompts = [prompt_override]
    else:
        prompts = prompt_pack["prompts"][:3]
    scene_bits = []
    for idx, prompt in enumerate(prompts, start=1):
        cleaned = prompt.replace("[Protagonist]", "").strip(" ;")
        scene_bits.append(f"[SCENE-{idx}] {cleaned}")
    return f"[MOVIE-SHOTS] Theme: {theme}. " + ", ".join(scene_bits)


def resolve_lora_name(inventory: list[dict]) -> str:
    if any(row.get("filename") == "movie-shots.safetensors" and row.get("exists") for row in inventory):
        return "movie-shots.safetensors"
    return LORA_ALIAS_MAP["movie-shots.safetensors"]


def build_api_prompt(prompt_text: str, seed: int, lora_name: str, filename_prefix: str) -> dict[str, Any]:
    return {
        "12": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "default"}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "11": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux",
            },
        },
        "38": {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["12", 0],
                "clip": ["11", 0],
                "lora_name": lora_name,
                "strength_model": 1.0,
                "strength_clip": 1.0,
            },
        },
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["38", 1], "text": prompt_text}},
        "26": {"class_type": "FluxGuidance", "inputs": {"conditioning": ["6", 0], "guidance": 3.5}},
        "30": {
            "class_type": "ModelSamplingFlux",
            "inputs": {
                "model": ["38", 0],
                "max_shift": 1.15,
                "base_shift": 0.5,
                "width": 1024,
                "height": 1536,
            },
        },
        "22": {"class_type": "BasicGuider", "inputs": {"model": ["30", 0], "conditioning": ["26", 0]}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "17": {
            "class_type": "BasicScheduler",
            "inputs": {"model": ["30", 0], "scheduler": "simple", "steps": 20, "denoise": 1.0},
        },
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "27": {"class_type": "EmptySD3LatentImage", "inputs": {"width": 1024, "height": 1536, "batch_size": 1}},
        "13": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["25", 0],
                "guider": ["22", 0],
                "sampler": ["16", 0],
                "sigmas": ["17", 0],
                "latent_image": ["27", 0],
            },
        },
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["13", 0], "vae": ["10", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": filename_prefix}},
    }


def comfy_post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base_url.rstrip("/") + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def comfy_get_json(base_url: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(base_url.rstrip("/") + path, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_comfyui_prompt(base_url: str, prompt: dict[str, Any], timeout_s: int = 1800, poll_interval_s: float = 5.0) -> dict[str, Any]:
    client_id = str(uuid.uuid4())
    queued = comfy_post_json(base_url, "/prompt", {"prompt": prompt, "client_id": client_id})
    prompt_id = queued["prompt_id"]
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        history = comfy_get_json(base_url, f"/history/{prompt_id}")
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval_s)
    raise TimeoutError(f"ComfyUI prompt {prompt_id} did not finish within {timeout_s}s")


def collect_image_refs(history_entry: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for node_output in (history_entry.get("outputs") or {}).values():
        for image in node_output.get("images") or []:
            refs.append(image)
    return refs


def image_ref_paths(comfyui_root: Path, refs: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    base = comfyui_root / "output"
    for ref in refs:
        filename = ref.get("filename")
        if not filename:
            continue
        subfolder = ref.get("subfolder") or ""
        candidate = base / subfolder / filename
        paths.append(str(candidate))
    return paths


def build_success_payload(item, prompts, latency_s, image_paths, extra, *, mode: str, error: str | None = None, status: str = "success") -> dict:
    return result_payload(
        item,
        BASELINE,
        status,
        prompts,
        latency_s=latency_s,
        image_paths=image_paths,
        error=error,
        extra={**extra, "mode": mode},
    )


def main() -> None:
    parser = common_parser("Run IC-LoRA workflow execution or readiness probe for DN-style prompts.")
    parser.add_argument("--comfyui-url", default=None, help="Optional ComfyUI API URL for execution.")
    parser.add_argument("--workflow", default="baselines/IC-LoRA/workflow/film-storyboard.json")
    parser.add_argument("--comfyui-root", default="/root/autodl-tmp/ComfyUI")
    parser.add_argument("--execution-mode", choices=["probe", "real"], default="probe")
    parser.add_argument("--poll-timeout-s", type=int, default=1800)
    parser.add_argument("--poll-interval-s", type=float, default=5.0)
    parser.add_argument("--mode", choices=["first_turn", "next_turn"], default="first_turn")
    parser.add_argument("--player-action", default=DEFAULT_NEXT_TURN_ACTION)
    args = parser.parse_args()

    items = load_subset(args.subset)
    run_dir = make_run_dir(args.output, BASELINE, args.run_id)
    write_json(run_dir / "config.json", vars(args))
    write_json(run_dir / "environment.json", environment_payload())

    workflow_path = resolve_repo_path(args.workflow)
    comfyui_root = Path(args.comfyui_root)
    requirements = workflow_requirements(workflow_path) if workflow_path.exists() else []
    inventory, missing_assets = asset_inventory(comfyui_root, requirements) if requirements else ([], [])
    comfy_probe = probe_comfyui(args.comfyui_url)
    blocker = blocker_message(workflow_path, comfyui_root, missing_assets, comfy_probe)
    lora_name = resolve_lora_name(inventory) if inventory else "movie-shots.safetensors"

    results = []
    for item in items:
        prompt_pack = item.get("visual_prompt_pack") or build_visual_prompts(item, args.scene_count)
        sample_dir = run_dir / str(item["benchmark_id"])
        sample_dir.mkdir(parents=True, exist_ok=True)
        extra = {
            "workflow": str(workflow_path),
            "comfyui_url": args.comfyui_url,
            "comfyui_root": str(comfyui_root),
            "workflow_requirements": inventory,
            "missing_workflow_assets": missing_assets,
            "comfyui_probe": comfy_probe,
        }
        if args.execution_mode != "real" or missing_assets or not comfy_probe.get("reachable"):
            write_json(sample_dir / "prompt.json", prompt_pack)
            payload = build_success_payload(
                item,
                prompt_pack["prompts"][: args.scene_count],
                0.0,
                [],
                {**extra, "blocked_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                mode=args.mode,
                error=blocker,
                status="blocked",
            )
            write_json(sample_dir / "result.json", payload)
            results.append(payload)
            continue

        try:
            if args.mode == "next_turn":
                current_storyboard_prompt = normalize_storyboard_prompt(item, prompt_pack)
                current_api_prompt = build_api_prompt(
                    prompt_text=current_storyboard_prompt,
                    seed=args.seed,
                    lora_name=lora_name,
                    filename_prefix=f"ICLORA_CURRENT_{item['benchmark_id']}",
                )
                current_history = run_comfyui_prompt(
                    args.comfyui_url,
                    current_api_prompt,
                    timeout_s=args.poll_timeout_s,
                    poll_interval_s=args.poll_interval_s,
                )
                current_refs = collect_image_refs(current_history)
                previous_image_paths = image_ref_paths(comfyui_root, current_refs)

                next_turn = build_next_turn_prompt(item, prompt_pack, args.player_action)
                continuation_storyboard_prompt = normalize_storyboard_prompt(
                    item,
                    prompt_pack,
                    prompt_override=next_turn["continuation_prompt"],
                )
                next_api_prompt = build_api_prompt(
                    prompt_text=continuation_storyboard_prompt,
                    seed=args.seed,
                    lora_name=lora_name,
                    filename_prefix=f"ICLORA_NEXT_{item['benchmark_id']}",
                )
                request_start_ts = time.time()
                start = time.perf_counter()
                history = run_comfyui_prompt(
                    args.comfyui_url,
                    next_api_prompt,
                    timeout_s=args.poll_timeout_s,
                    poll_interval_s=args.poll_interval_s,
                )
                latency_s = time.perf_counter() - start
                first_playable_ts = request_start_ts + latency_s
                finish_ts = first_playable_ts
                image_refs = collect_image_refs(history)
                image_paths = image_ref_paths(comfyui_root, image_refs)
                input_bundle = build_input_bundle(
                    item,
                    prompt_pack,
                    mode="next_turn",
                    player_action=args.player_action,
                    previous_image_paths=previous_image_paths,
                )
                raw_output = {
                    "current_storyboard_prompt": current_storyboard_prompt,
                    "continuation_storyboard_prompt": continuation_storyboard_prompt,
                    "previous_image_paths": previous_image_paths,
                    "image_paths": image_paths,
                    "current_history_status": current_history.get("status"),
                    "comfyui_history_status": history.get("status"),
                    "narrative_response": "IC-LoRA generated a continuation image after the simulated player click.",
                }
                playable = build_playable_image_result(
                    item=item,
                    baseline=BASELINE,
                    run_id=f"{BASELINE}_{args.run_id or 'run'}_{item['benchmark_id']}",
                    input_bundle=input_bundle,
                    raw_output=raw_output,
                    image_paths=image_paths,
                    request_start_ts=request_start_ts,
                    first_playable_ts=first_playable_ts,
                    finish_ts=finish_ts,
                    success=bool(image_refs),
                    error=None if image_refs else "ComfyUI finished but returned no continuation image",
                    notes=["IC-LoRA next-turn latency measures only the post-click continuation workflow."],
                    extra={**extra, "current_api_prompt": current_api_prompt, "api_prompt": next_api_prompt},
                )
                playable.update(
                    build_success_payload(
                        item,
                        [next_turn["continuation_prompt"]],
                        latency_s,
                        image_paths,
                        {**extra, "current_api_prompt": current_api_prompt, "api_prompt": next_api_prompt, "comfyui_history": history, "image_refs": image_refs},
                        mode="next_turn",
                        error=None if image_refs else "ComfyUI finished but returned no continuation image",
                        status="success" if image_refs else "failed",
                    )
                )
                write_json(sample_dir / "prompt.json", {"first_turn_storyboard_prompt": current_storyboard_prompt, "next_turn": next_turn, "input_bundle": input_bundle})
                write_json(sample_dir / "result.json", playable)
                results.append(playable)
                continue

            storyboard_prompt = normalize_storyboard_prompt(item, prompt_pack)
            api_prompt = build_api_prompt(
                prompt_text=storyboard_prompt,
                seed=args.seed,
                lora_name=lora_name,
                filename_prefix=f"ICLORA_{item['benchmark_id']}",
            )
            start = time.perf_counter()
            history = run_comfyui_prompt(
                args.comfyui_url,
                api_prompt,
                timeout_s=args.poll_timeout_s,
                poll_interval_s=args.poll_interval_s,
            )
            latency_s = time.perf_counter() - start
            image_refs = collect_image_refs(history)
            image_paths = image_ref_paths(comfyui_root, image_refs)
            payload = build_success_payload(
                item,
                prompt_pack["prompts"][: args.scene_count],
                latency_s,
                image_paths,
                {**extra, "storyboard_prompt": storyboard_prompt, "api_prompt": api_prompt, "comfyui_history": history, "image_refs": image_refs},
                mode="first_turn",
                error=None if image_refs else "ComfyUI finished but returned no images",
                status="success" if image_refs else "failed",
            )
        except Exception as exc:
            payload = build_success_payload(
                item,
                prompt_pack["prompts"][: args.scene_count],
                0.0,
                [],
                extra,
                mode=args.mode,
                error=f"{type(exc).__name__}: {exc}",
                status="failed",
            )
        write_json(sample_dir / "prompt.json", prompt_pack)
        write_json(sample_dir / "result.json", payload)
        results.append(payload)

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes=(
            "IC-LoRA readiness probe only; records concrete workflow, asset, and ComfyUI blockers before any training or real inference."
            if args.execution_mode == "probe"
            else (
                "IC-LoRA attempts official ComfyUI workflow execution when assets and ComfyUI API are ready."
                if args.mode == "first_turn"
                else "IC-LoRA next-turn latency measures the post-click continuation workflow only."
            )
        ),
        mode=args.mode,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
