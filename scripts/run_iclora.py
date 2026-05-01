import argparse
import json
import uuid
from pathlib import Path

from baseline_common import read_jsonl, sample_id, write_jsonl
from comfyui_client import download_image, get_system_stats, image_refs_from_history, queue_prompt, wait_for_history
from iclora_workflow_utils import (
    format_iclora_prompt,
    load_workflow,
    replace_prompt_seed_and_prefix,
    resolve_workflow_path,
    ui_workflow_to_api_prompt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IC-LoRA through a local ComfyUI FLUX server from unified JSONL.")
    parser.add_argument("--input", required=True, help="Input JSONL with an id and prompt per line.")
    parser.add_argument("--output_dir", required=True, help="Directory for prepared workflows and index.jsonl.")
    parser.add_argument("--repo_dir", default="baselines/image/In-Context-LoRA", help="Official IC-LoRA repo path.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--workflow",
        default="baselines/image/In-Context-LoRA/workflow/film-storyboard.json",
        help="ComfyUI workflow JSON path, or path relative to repo_dir.",
    )
    parser.add_argument(
        "--prepare_only",
        action="store_true",
        help="Write per-sample UI/API workflow JSON files without submitting them to ComfyUI.",
    )
    parser.add_argument("--comfy_url", default="http://127.0.0.1:8188", help="ComfyUI server URL.")
    parser.add_argument("--max_samples", type=int, default=None, help="Optional cap for smoke tests.")
    parser.add_argument("--timeout", type=float, default=900.0, help="Seconds to wait for each ComfyUI prompt.")
    return parser.parse_args()


def relative_path(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def write_index(output_dir: Path, rows: list[dict]) -> None:
    write_jsonl(output_dir / "index.jsonl", rows)


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir)
    try:
        workflow_path = resolve_workflow_path(repo_dir, args.workflow)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc

    workflow = load_workflow(workflow_path)
    rows = read_jsonl(args.input)
    if args.max_samples is not None:
        rows = rows[: args.max_samples]
    output_dir = Path(args.output_dir)
    workflow_out_dir = output_dir / "workflows"
    api_workflow_out_dir = output_dir / "api_workflows"
    workflow_out_dir.mkdir(parents=True, exist_ok=True)
    api_workflow_out_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    if not args.prepare_only:
        stats = get_system_stats(args.comfy_url)
        devices = stats.get("devices", [])
        print(f"Connected to ComfyUI at {args.comfy_url}; devices={json.dumps(devices, ensure_ascii=False)}")

    for idx, row in enumerate(rows):
        sid = sample_id(row, idx)
        prompt = format_iclora_prompt(row)
        seed = args.seed + idx
        filename_prefix = f"IC-LoRA/{sid}"
        prepared = replace_prompt_seed_and_prefix(workflow, prompt, seed, filename_prefix)
        api_prompt = ui_workflow_to_api_prompt(prepared)
        prepared_path = workflow_out_dir / f"{sid}.film-storyboard.workflow.json"
        api_prepared_path = api_workflow_out_dir / f"{sid}.film-storyboard.api.json"
        prepared_path.parent.mkdir(parents=True, exist_ok=True)
        api_prepared_path.parent.mkdir(parents=True, exist_ok=True)
        prepared_path.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
        api_prepared_path.write_text(json.dumps(api_prompt, ensure_ascii=False, indent=2), encoding="utf-8")

        base_row = {
            "id": sid,
            "baseline": "IC-LoRA",
            "prompt": prompt,
            "metadata": {
                "seed": seed,
                "workflow": relative_path(prepared_path),
                "api_workflow": relative_path(api_prepared_path),
                "source_workflow": workflow_path.as_posix(),
                "comfy_url": args.comfy_url,
            },
        }

        if args.prepare_only:
            manifest.append(
                {
                    **base_row,
                    "image_path": None,
                    "metadata": {
                        **base_row["metadata"],
                        "status": "prepared_not_generated",
                        "required_models": [
                            "flux1-dev.safetensors in ComfyUI/models/unet/",
                            "ae.safetensors in ComfyUI/models/vae/",
                            "t5xxl_fp8_e4m3fn.safetensors or t5xxl_fp16.safetensors in ComfyUI/models/clip/",
                            "clip_l.safetensors in ComfyUI/models/clip/",
                            "movie-shots.safetensors in ComfyUI/models/loras/",
                        ],
                    },
                }
            )
            continue

        try:
            client_id = str(uuid.uuid4())
            prompt_id = queue_prompt(args.comfy_url, api_prompt, client_id=client_id)
            history = wait_for_history(args.comfy_url, prompt_id, timeout_seconds=args.timeout)
            image_refs = image_refs_from_history(history)
            if not image_refs:
                raise RuntimeError(f"ComfyUI finished prompt {prompt_id} without image outputs")
            target_image = output_dir / f"{sid}.png"
            target_image.parent.mkdir(parents=True, exist_ok=True)
            download_image(args.comfy_url, image_refs[-1], target_image)
            if not target_image.exists() or target_image.stat().st_size == 0:
                raise RuntimeError(f"Expected generated image was not saved: {target_image}")
            manifest.append(
                {
                    **base_row,
                    "image_path": relative_path(target_image),
                    "metadata": {
                        **base_row["metadata"],
                        "status": "success",
                        "prompt_id": prompt_id,
                        "comfy_image": image_refs[-1],
                    },
                }
            )
            write_index(output_dir, manifest)
            print(f"Generated {target_image}")
        except Exception as exc:
            manifest.append(
                {
                    **base_row,
                    "image_path": None,
                    "metadata": {
                        **base_row["metadata"],
                        "status": "failed",
                        "error": str(exc),
                    },
                }
            )
            write_index(output_dir, manifest)
            raise

    write_index(output_dir, manifest)
    if args.prepare_only:
        print(f"Wrote IC-LoRA prepared manifest to {output_dir / 'index.jsonl'}")
    else:
        print(f"Wrote IC-LoRA generation manifest to {output_dir / 'index.jsonl'}")


if __name__ == "__main__":
    main()
