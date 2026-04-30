"""Run StoryDiffusion low-VRAM generation on DN-style prompts.

This runner loads StoryDiffusion's low-VRAM script without launching the Gradio
UI, then calls its process_generation generator. It keeps all new experiment
artifacts outside the upstream repository.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from baseline_io import (
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
    """Execute StoryDiffusion script up to the UI block and return globals."""

    script_path = repo_dir / "gradio_app_sdxl_specific_id_low_vram.py"
    source = script_path.read_text(encoding="utf-8", errors="replace")
    marker = "with gr.Blocks(css=css) as demo:"
    if marker not in source:
        raise RuntimeError(f"Cannot find Gradio UI marker in {script_path}")
    head = source.split(marker, 1)[0]
    # The upstream low-VRAM script downloads PhotoMaker at import time even for
    # textual-description mode. The batch runner does not use PhotoMaker, so skip
    # that eager download and let the real SDXL model download happen later.
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
        except Exception as exc:  # pragma: no cover - remote model/runtime dependent
            for item, prompt_pack in prompt_packs:
                sample_dir = run_dir / str(item["benchmark_id"])
                sample_dir.mkdir(parents=True, exist_ok=True)
                (sample_dir / "prompt.txt").write_text("\n".join(prompt_pack["prompts"]), encoding="utf-8")
                write_json(sample_dir / "prompt.json", prompt_pack)
                payload = result_payload(
                    item,
                    BASELINE,
                    "blocked",
                    prompt_pack["prompts"],
                    latency_s=0.0,
                    error=f"StoryDiffusion model load blocked: {type(exc).__name__}: {exc}",
                    extra={"sd_type": args.sd_type},
                )
                write_json(sample_dir / "result.json", payload)
                results.append(payload)
        else:
            for item, prompt_pack in prompt_packs:
                sample_dir = run_dir / str(item["benchmark_id"])
                sample_dir.mkdir(parents=True, exist_ok=True)
                (sample_dir / "prompt.txt").write_text("\n".join(prompt_pack["prompts"]), encoding="utf-8")
                write_json(sample_dir / "prompt.json", prompt_pack)
                try:
                    start = time.perf_counter()
                    images = run_one(namespace, prompt_pack, args)
                    latency = time.perf_counter() - start
                    image_paths = save_pil_images(images[: args.scene_count], sample_dir)
                    payload = result_payload(item, BASELINE, "success", prompt_pack["prompts"], latency, image_paths)
                    write_json(sample_dir / "result.json", payload)
                    results.append(payload)
                except Exception as exc:  # pragma: no cover - remote model/runtime dependent
                    results.append(write_failure(sample_dir, item, BASELINE, prompt_pack["prompts"], exc))

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes="StoryDiffusion low-VRAM textual-description mode; 4 DN-style scene prompts per item by default.",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
