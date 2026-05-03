"""Run StoryDiffusion low-VRAM generation on DN-style prompts."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

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
    save_pil_images,
    summarize_results,
    tee_run_log,
    write_failure,
    write_json,
)


BASELINE = "storydiffusion"


def load_storydiffusion_namespace(repo_dir: Path) -> dict:
    script_path = repo_dir / "gradio_app_sdxl_specific_id_low_vram.py"
    source = script_path.read_text(encoding="utf-8", errors="replace")
    marker = "with gr.Blocks(css=css) as demo:"
    if marker not in source:
        raise RuntimeError(f"Cannot find Gradio UI marker in {script_path}")
    head = source.split(marker, 1)[0]
    photomaker_block = '''if not os.path.exists(photomaker_local_path):
    photomaker_path = hf_hub_download(
        repo_id="TencentARC/PhotoMaker",
        filename="photomaker-v1.bin",
        repo_type="model",
        local_dir=local_dir,
    )
else:
    photomaker_path = photomaker_local_path
'''
    if photomaker_block in head:
        head = head.replace(photomaker_block, "photomaker_path = photomaker_local_path\n")
    local_override = r'''
def _dn_local_snapshot(repo_id):
    cache = os.environ.get("HF_HUB_CACHE") or os.environ.get("HF_HOME")
    if not cache:
        return None
    root = os.path.join(cache, "models--" + repo_id.replace("/", "--"), "snapshots")
    if not os.path.isdir(root):
        return None
    snapshots = [os.path.join(root, name) for name in os.listdir(root)]
    snapshots = [path for path in snapshots if os.path.isdir(path)]
    return sorted(snapshots)[-1] if snapshots else None

for _dn_key, _dn_repo in {
    "Unstable": "stablediffusionapi/sdxl-unstable-diffusers-y",
    "SDXL": "stabilityai/stable-diffusion-xl-base-1.0",
}.items():
    _dn_path = _dn_local_snapshot(_dn_repo)
    if _dn_path and _dn_key in models_dict:
        models_dict[_dn_key]["path"] = _dn_path
'''
    head = head.replace("models_dict = get_models_dict()", "models_dict = get_models_dict()\n" + local_override)
    head = head.replace(
        'models_dict["Unstable"]["path"]',
        'models_dict[os.environ.get("STORYDIFFUSION_INIT_MODEL", "SDXL")]["path"]',
    )
    head = head.replace(
        'models_dict["Unstable"]["single_files"]',
        'models_dict[os.environ.get("STORYDIFFUSION_INIT_MODEL", "SDXL")]["single_files"]\n'
        'use_safetensors = models_dict[os.environ.get("STORYDIFFUSION_INIT_MODEL", "SDXL")].get("use_safetensors", True)',
    )
    head = head.replace("use_safetensors=False", "use_safetensors=use_safetensors")
    namespace = {"__name__": "storydiffusion_batch_adapter", "__file__": str(script_path)}
    old_cwd = os.getcwd()
    sys.path.insert(0, str(repo_dir))
    try:
        os.chdir(repo_dir)
        exec(compile(head, str(script_path), "exec"), namespace)
    finally:
        os.chdir(old_cwd)
        try:
            sys.path.remove(str(repo_dir))
        except ValueError:
            pass
    for model_info in (namespace.get("models_dict") or {}).values():
        if isinstance(model_info, dict):
            model_info.setdefault("model_type", "original")
    return namespace


def pack_with_prompts(prompt_pack: dict, prompts: list[str]) -> dict:
    cloned = dict(prompt_pack)
    cloned["prompts"] = prompts
    return cloned


def run_one(namespace: dict, prompt_pack: dict, args) -> list:
    process_generation = namespace["process_generation"]
    generator = process_generation(
        args.sd_type,
        "Only Using Textual Description",
        None,
        args.steps,
        prompt_pack.get("style_name", args.style),
        0.5,
        args.style_strength_ratio,
        args.guidance_scale,
        args.seed,
        args.sa32,
        args.sa64,
        args.id_length,
        prompt_pack["character_description"],
        prompt_pack["negative_prompt"],
        "\n".join(prompt_pack["prompts"]),
        args.height,
        args.width,
        "No typesetting (default)",
        args.font,
        "",
    )
    last_images = None
    for yielded in generator:
        last_images = yielded
    if not last_images:
        raise RuntimeError("StoryDiffusion returned no images")
    return last_images


def build_next_turn_result(item: dict, base_prompt_pack: dict, sample_dir: Path, namespace: dict, args) -> dict:
    min_prompt_count = max(int(args.id_length), 2)
    current_prompts = base_prompt_pack["prompts"][:min_prompt_count]
    first_pack = pack_with_prompts(base_prompt_pack, current_prompts)
    current_images = run_one(namespace, first_pack, args)
    previous_image_paths = save_pil_images(current_images[: len(current_prompts)], sample_dir, prefix="current_image")

    next_turn = build_next_turn_prompt(item, base_prompt_pack, args.player_action)
    next_prompts = current_prompts[:-1] + [next_turn["continuation_prompt"]]
    next_pack = pack_with_prompts(base_prompt_pack, next_prompts)
    request_start_ts = time.time()
    start = time.perf_counter()
    images = run_one(namespace, next_pack, args)
    latency = time.perf_counter() - start
    first_playable_ts = request_start_ts + latency
    finish_ts = first_playable_ts
    continuation_image = images[len(next_prompts) - 1]
    image_paths = save_pil_images([continuation_image], sample_dir)
    input_bundle = build_input_bundle(
        item,
        base_prompt_pack,
        mode="next_turn",
        player_action=args.player_action,
        previous_image_paths=previous_image_paths,
    )
    raw_output = {
        "current_prompt": first_pack["prompts"][0],
        "continuation_prompt": next_pack["prompts"][0],
        "previous_image_paths": previous_image_paths,
        "image_paths": image_paths,
        "narrative_response": "StoryDiffusion generated a continuation image after the simulated player click.",
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
        success=True,
        notes=["StoryDiffusion next-turn latency measures only the post-click continuation image."],
        extra={"sd_type": args.sd_type},
    )
    playable.update(
        result_payload(
            item,
            BASELINE,
            "success",
            next_pack["prompts"],
            latency_s=latency,
            image_paths=image_paths,
            extra={"mode": "next_turn", "sd_type": args.sd_type},
        )
    )
    write_json(sample_dir / "prompt.json", {"first_turn": first_pack, "next_turn": next_pack, "input_bundle": input_bundle})
    write_json(sample_dir / "result.json", playable)
    return playable


def main() -> None:
    parser = common_parser("Run StoryDiffusion low-VRAM batch generation.")
    parser.add_argument("--repo-dir", default="baselines/StoryDiffusion")
    parser.add_argument("--sd-type", default="Unstable", help="Key in StoryDiffusion config/models.yaml.")
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance-scale", type=float, default=5.0)
    parser.add_argument("--style-strength-ratio", type=float, default=50.0)
    parser.add_argument("--sa32", type=float, default=0.5)
    parser.add_argument("--sa64", type=float, default=0.5)
    parser.add_argument("--id-length", type=int, default=2)
    parser.add_argument("--style", default="Photographic")
    parser.add_argument("--font", default="Inkfree.ttf")
    parser.add_argument("--mode", choices=["first_turn", "next_turn"], default="first_turn")
    parser.add_argument("--player-action", default=DEFAULT_NEXT_TURN_ACTION)
    args = parser.parse_args()

    items = load_subset(args.subset)
    run_dir = make_run_dir(args.output, BASELINE, args.run_id)
    write_json(run_dir / "config.json", vars(args))
    write_json(run_dir / "environment.json", environment_payload())

    prompt_packs = []
    for item in items:
        prompt_pack = item.get("visual_prompt_pack") or build_visual_prompts(item, args.scene_count)
        prompt_pack["prompts"] = prompt_pack["prompts"][: args.scene_count]
        prompt_packs.append((item, prompt_pack))

    results = []
    with tee_run_log(run_dir / "run.log"):
        try:
            namespace = load_storydiffusion_namespace(Path(args.repo_dir).resolve())
        except Exception as exc:  # pragma: no cover
            for item, prompt_pack in prompt_packs:
                sample_dir = run_dir / str(item["benchmark_id"])
                sample_dir.mkdir(parents=True, exist_ok=True)
                write_json(sample_dir / "prompt.json", prompt_pack)
                payload = result_payload(
                    item,
                    BASELINE,
                    "blocked",
                    prompt_pack["prompts"],
                    latency_s=0.0,
                    error=f"StoryDiffusion model load blocked: {type(exc).__name__}: {exc}",
                    extra={"sd_type": args.sd_type, "mode": args.mode},
                )
                write_json(sample_dir / "result.json", payload)
                results.append(payload)
        else:
            for item, prompt_pack in prompt_packs:
                sample_dir = run_dir / str(item["benchmark_id"])
                sample_dir.mkdir(parents=True, exist_ok=True)
                try:
                    if args.mode == "next_turn":
                        results.append(build_next_turn_result(item, prompt_pack, sample_dir, namespace, args))
                        continue
                    (sample_dir / "prompt.txt").write_text("\n".join(prompt_pack["prompts"]), encoding="utf-8")
                    write_json(sample_dir / "prompt.json", prompt_pack)
                    start = time.perf_counter()
                    images = run_one(namespace, prompt_pack, args)
                    latency = time.perf_counter() - start
                    image_paths = save_pil_images(images[: args.scene_count], sample_dir)
                    payload = result_payload(
                        item,
                        BASELINE,
                        "success",
                        prompt_pack["prompts"],
                        latency,
                        image_paths,
                        extra={"mode": "first_turn"},
                    )
                    write_json(sample_dir / "result.json", payload)
                    results.append(payload)
                except Exception as exc:  # pragma: no cover
                    results.append(write_failure(sample_dir, item, BASELINE, prompt_pack["prompts"], exc))

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes=(
            "StoryDiffusion low-VRAM textual-description mode; 4 DN-style scene prompts per item by default."
            if args.mode == "first_turn"
            else "StoryDiffusion next-turn latency measures the post-click continuation image only."
        ),
        mode=args.mode,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
