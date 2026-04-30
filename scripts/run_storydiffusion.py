import argparse
from pathlib import Path

from baseline_common import read_jsonl, require_prompt, sample_id, write_jsonl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare unified JSONL prompts for the official StoryDiffusion image/comic implementation."
    )
    parser.add_argument("--input", required=True, help="Input JSONL with an id and prompt per line.")
    parser.add_argument("--output_dir", required=True, help="Directory for prepared prompt manifest and future outputs.")
    parser.add_argument("--repo_dir", default="baselines/image/StoryDiffusion", help="Official StoryDiffusion repo path.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--prepare_only",
        action="store_true",
        help="Write a manifest without attempting generation. This is the current supported mode.",
    )
    parser.add_argument(
        "--launch_hint",
        action="store_true",
        help="Print the official low-VRAM Gradio command after writing the manifest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir)
    app_file = repo_dir / "gradio_app_sdxl_specific_id_low_vram.py"
    if not app_file.exists():
        raise SystemExit(f"StoryDiffusion official app not found: {app_file}")

    rows = read_jsonl(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for idx, row in enumerate(rows):
        sid = sample_id(row, idx)
        prompt = require_prompt(row)
        prompt_file = output_dir / f"{sid}.prompt.txt"
        prompt_file.write_text(prompt + "\n", encoding="utf-8")
        manifest.append(
            {
                "id": sid,
                "baseline": "StoryDiffusion",
                "prompt": prompt,
                "image_path": None,
                "metadata": {
                    "seed": args.seed + idx,
                    "status": "prepared_not_generated",
                    "official_repo": str(repo_dir.as_posix()),
                    "prompt_file": str(prompt_file.as_posix()),
                    "limitation": "The official release exposes Notebook/Gradio image generation, not a stable batch CLI.",
                },
            }
        )
    write_jsonl(output_dir / "index.jsonl", manifest)

    cmd = f"cd {repo_dir.as_posix()} && python gradio_app_sdxl_specific_id_low_vram.py"
    print(f"Wrote StoryDiffusion prepared manifest to {output_dir / 'index.jsonl'}")
    if args.launch_hint:
        print("Official interactive command:", cmd)
    if not args.prepare_only:
        raise SystemExit(
            "StoryDiffusion batch generation is not executed by this wrapper yet. "
            "Use --prepare_only to create manifests, or run the official Gradio/Notebook workflow manually."
        )


if __name__ == "__main__":
    main()
