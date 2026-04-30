import argparse
import copy
import json
from pathlib import Path

from baseline_common import read_jsonl, require_prompt, sample_id, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare IC-LoRA/ComfyUI workflow inputs from unified JSONL.")
    parser.add_argument("--input", required=True, help="Input JSONL with an id and prompt per line.")
    parser.add_argument("--output_dir", required=True, help="Directory for prepared workflows and index.jsonl.")
    parser.add_argument("--repo_dir", default="baselines/image/In-Context-LoRA", help="Official IC-LoRA repo path.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--workflow",
        default="workflow/film-storyboard.json",
        help="Workflow JSON path relative to repo_dir.",
    )
    parser.add_argument(
        "--prepare_only",
        action="store_true",
        help="Write ComfyUI workflow files without attempting generation. This is the current supported mode.",
    )
    return parser.parse_args()


def replace_prompt_and_seed(workflow: dict, prompt: str, seed: int) -> dict:
    data = copy.deepcopy(workflow)
    for node in data.get("nodes", []):
        if node.get("type") == "CLIPTextEncode" and node.get("widgets_values"):
            node["widgets_values"][0] = prompt
        if node.get("type") == "RandomNoise" and node.get("widgets_values"):
            node["widgets_values"][0] = seed
            if len(node["widgets_values"]) > 1:
                node["widgets_values"][1] = "fixed"
    return data


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir)
    workflow_path = repo_dir / args.workflow
    if not workflow_path.exists():
        raise SystemExit(f"IC-LoRA workflow not found: {workflow_path}")

    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    rows = read_jsonl(args.input)
    output_dir = Path(args.output_dir)
    workflow_out_dir = output_dir / "workflows"
    workflow_out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for idx, row in enumerate(rows):
        sid = sample_id(row, idx)
        prompt = require_prompt(row)
        seed = args.seed + idx
        prepared = replace_prompt_and_seed(workflow, prompt, seed)
        prepared_path = workflow_out_dir / f"{sid}.film-storyboard.workflow.json"
        prepared_path.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest.append(
            {
                "id": sid,
                "baseline": "IC-LoRA",
                "prompt": prompt,
                "image_path": None,
                "metadata": {
                    "seed": seed,
                    "status": "prepared_not_generated",
                    "official_repo": str(repo_dir.as_posix()),
                    "workflow": str(prepared_path.as_posix()),
                    "required_models": [
                        "FLUX.1-dev or compatible base model",
                        "ali-vilab/In-Context-LoRA movie-shots.safetensors",
                        "ComfyUI FLUX dependencies: ae.safetensors, t5xxl, clip_l",
                    ],
                    "limitation": "Official repository provides training config/model zoo/ComfyUI workflow, not a standalone batch inference CLI.",
                },
            }
        )

    write_jsonl(output_dir / "index.jsonl", manifest)
    print(f"Wrote IC-LoRA prepared manifest to {output_dir / 'index.jsonl'}")
    if not args.prepare_only:
        raise SystemExit(
            "IC-LoRA image generation is not executed by this wrapper yet. "
            "Use --prepare_only to prepare ComfyUI workflows, then run them in a configured ComfyUI FLUX environment."
        )


if __name__ == "__main__":
    main()
