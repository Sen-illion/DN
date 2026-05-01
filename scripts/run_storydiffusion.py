import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from baseline_common import read_jsonl, require_prompt, sample_id, write_jsonl


DEFAULT_NEGATIVE_PROMPT = (
    "bad anatomy, bad hands, missing fingers, extra fingers, poorly drawn face, "
    "fused face, cloned face, extra limbs, missing limbs, low quality, blurry, "
    "watermark, text"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run StoryDiffusion image/comic generation over the unified JSONL dataset. "
            "Use --prepare_only to write deterministic prompt manifests without loading models."
        )
    )
    parser.add_argument("--input", required=True, help="Input JSONL with id/prompt fields.")
    parser.add_argument("--output_dir", required=True, help="Directory for images and index.jsonl.")
    parser.add_argument("--repo_dir", default="baselines/image/StoryDiffusion", help="Official StoryDiffusion repo path.")
    parser.add_argument("--seed", type=int, default=42, help="Base seed; sample index is added for each row.")
    parser.add_argument(
        "--model",
        default="Unstable",
        help="Model key from config/models.yaml, or a Hugging Face/local model id. Ignored when --model_path is set.",
    )
    parser.add_argument("--model_path", default=None, help="Explicit Hugging Face id, local diffusers dir, or .safetensors file.")
    parser.add_argument("--single_file", action="store_true", help="Treat --model/--model_path as a single checkpoint file.")
    parser.add_argument("--num_inference_steps", type=int, default=30)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--device", default="cuda", help="cuda, cpu, mps, or auto.")
    parser.add_argument("--dtype", default="float16", choices=["auto", "float16", "float32", "bfloat16"])
    parser.add_argument("--guidance_scale", type=float, default=5.0)
    parser.add_argument("--frames", type=int, default=4, help="Number of storyboard prompts to derive when a row has no frame prompts.")
    parser.add_argument("--id_length", type=int, default=4, help="StoryDiffusion reference prompt count per character.")
    parser.add_argument("--sa32", type=float, default=0.5, help="Official StoryDiffusion 32x attention sampling ratio.")
    parser.add_argument("--sa64", type=float, default=0.5, help="Official StoryDiffusion 64x attention sampling ratio.")
    parser.add_argument("--style", default="Japanese Anime", help="Style template name from StoryDiffusion utils/style_template.py.")
    parser.add_argument("--negative_prompt", default=DEFAULT_NEGATIVE_PROMPT)
    parser.add_argument(
        "--comic_type",
        default="Four Pannel",
        choices=["No typesetting (default)", "Four Pannel", "Classic Comic Style"],
        help="Optional StoryDiffusion comic compositor. Four Pannel writes {id}.png by default.",
    )
    parser.add_argument("--font", default="Inkfree.ttf", help="Font file under the official StoryDiffusion fonts/ directory.")
    parser.add_argument("--attention_slicing", action="store_true", help="Enable diffusers attention slicing.")
    parser.add_argument("--cpu_offload", action="store_true", help="Enable accelerate model CPU offload for low VRAM CUDA runs.")
    parser.add_argument("--vae_slicing", action="store_true", default=True, help="Enable VAE slicing.")
    parser.add_argument("--no_vae_slicing", action="store_false", dest="vae_slicing")
    parser.add_argument("--no_freeu", action="store_true", help="Disable the official FreeU settings.")
    parser.add_argument("--local_files_only", action="store_true", help="Do not download models; use local cache/files only.")
    parser.add_argument("--continue_on_error", action="store_true", help="Write failed rows and keep processing later samples.")
    parser.add_argument(
        "--prepare_only",
        action="store_true",
        help="Write prompt manifest/index with status prepared_not_generated and do not load StoryDiffusion dependencies.",
    )
    parser.add_argument("--launch_hint", action="store_true", help="Print the official low-VRAM Gradio command.")
    return parser.parse_args()


def _coerce_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _character_aliases(characters: List[str]) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for index, character in enumerate(characters[:2]):
        aliases[character] = f"[{chr(ord('A') + index)}]"
    return aliases


def _expand_frame_prompts(row: Dict[str, Any], prompt: str, frame_count: int) -> List[str]:
    explicit = row.get("frame_prompts") or row.get("frames") or row.get("storyboard")
    explicit_prompts: List[str] = []
    if isinstance(explicit, list):
        for item in explicit:
            if isinstance(item, dict):
                text = str(item.get("prompt", "")).strip()
            else:
                text = str(item).strip()
            if text:
                explicit_prompts.append(text)
    if explicit_prompts:
        return explicit_prompts

    scene = str(row.get("scene", "")).strip()
    context = str(row.get("story_context", "")).strip()
    suffix = " ".join(part for part in [scene, context] if part)
    base = prompt if not suffix else f"{prompt} Setting/context: {suffix}."
    templates = [
        "establishing shot, cinematic storyboard panel",
        "character-focused shot, expressive pose, clear identity",
        "conflict or discovery shot, dramatic composition",
        "resolution shot, cinematic wide angle, coherent ending",
    ]
    while len(templates) < frame_count:
        templates.append(f"continuation storyboard panel {len(templates) + 1}, coherent visual narrative")
    return [f"{base} -- {templates[i]}" for i in range(max(1, frame_count))]


def build_storydiffusion_prompts(row: Dict[str, Any], prompt: str, frames: int, id_length: int) -> Dict[str, Any]:
    characters = _coerce_str_list(row.get("characters")) or ["main character"]
    aliases = _character_aliases(characters)
    main_alias = next(iter(aliases.values()))
    general_prompt = "\n".join(f"{alias} {character}" for character, alias in aliases.items())

    raw_frames = _expand_frame_prompts(row, prompt, frames)
    tagged_frames: List[str] = []
    for text in raw_frames:
        tagged = text
        if not any(alias in tagged for alias in aliases.values()) and "[NC]" not in tagged:
            tagged = f"{main_alias} {tagged}"
        tagged_frames.append(tagged)

    prompt_array = tagged_frames
    visible_indices = list(range(len(prompt_array)))

    if len(aliases) > 1:
        # StoryDiffusion needs id_length single-character reference prompts per character.
        reference_prompts: List[str] = []
        for character, alias in aliases.items():
            for ref_index in range(id_length):
                reference_prompts.append(
                    f"{alias} character reference panel {ref_index + 1}, {character}, consistent identity, {prompt}"
                )
        visible_indices = list(range(len(reference_prompts), len(reference_prompts) + len(tagged_frames)))
        prompt_array = reference_prompts + tagged_frames

    return {
        "general_prompt": general_prompt,
        "prompt_array": prompt_array,
        "prompt_array_text": "\n".join(prompt_array),
        "visible_indices": visible_indices,
        "characters": characters,
        "aliases": aliases,
    }


def write_prepared_manifest(rows: List[Dict[str, Any]], args: argparse.Namespace, output_dir: Path) -> None:
    manifest = []
    limited_rows = rows[: args.max_samples] if args.max_samples is not None else rows
    for idx, row in enumerate(limited_rows):
        sid = sample_id(row, idx)
        prompt = require_prompt(row)
        prepared = build_storydiffusion_prompts(row, prompt, args.frames, args.id_length)
        prompt_file = output_dir / f"{sid}.prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(prepared["prompt_array_text"] + "\n", encoding="utf-8")
        manifest.append(
            {
                "id": sid,
                "baseline": "StoryDiffusion",
                "image_path": None,
                "prompt": prompt,
                "metadata": {
                    "seed": args.seed + idx,
                    "status": "prepared_not_generated",
                    "model": args.model_path or args.model,
                    "frames": len(prepared["visible_indices"]),
                    "official_repo": str(Path(args.repo_dir).as_posix()),
                    "prompt_file": str(prompt_file.as_posix()),
                    "general_prompt": prepared["general_prompt"],
                    "prompt_array": prepared["prompt_array"],
                },
            }
        )
    write_jsonl(output_dir / "index.jsonl", manifest)


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.repo_dir)
    app_file = repo_dir / "gradio_app_sdxl_specific_id_low_vram.py"
    if not app_file.exists():
        raise SystemExit(f"StoryDiffusion official app not found: {app_file}")

    rows = read_jsonl(args.input)
    if args.max_samples is not None:
        rows = rows[: args.max_samples]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.prepare_only:
        write_prepared_manifest(rows, args, output_dir)
        print(f"Wrote StoryDiffusion prepared manifest to {output_dir / 'index.jsonl'}")
        if args.launch_hint:
            print(f"Official interactive command: cd {repo_dir.as_posix()} && python gradio_app_sdxl_specific_id_low_vram.py")
        return

    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from storydiffusion_batch_utils import StoryDiffusionBatchGenerator, save_storydiffusion_outputs

    generator = StoryDiffusionBatchGenerator(
        repo_dir=repo_dir,
        model=args.model,
        model_path=args.model_path,
        single_file=args.single_file,
        device=args.device,
        dtype=args.dtype,
        attention_slicing=args.attention_slicing,
        cpu_offload=args.cpu_offload,
        vae_slicing=args.vae_slicing,
        freeu=not args.no_freeu,
        local_files_only=args.local_files_only,
    )

    index_rows = []
    for idx, row in enumerate(rows):
        sid = sample_id(row, idx)
        prompt = require_prompt(row)
        prepared = build_storydiffusion_prompts(row, prompt, args.frames, args.id_length)
        prompt_file = output_dir / f"{sid}.prompt.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(prepared["prompt_array_text"] + "\n", encoding="utf-8")
        sample_seed = args.seed + idx
        try:
            images, generation_metadata = generator.generate(
                general_prompt=prepared["general_prompt"],
                prompt_array=prepared["prompt_array"],
                visible_indices=prepared["visible_indices"],
                seed=sample_seed,
                num_inference_steps=args.num_inference_steps,
                height=args.height,
                width=args.width,
                id_length=args.id_length,
                sa32=args.sa32,
                sa64=args.sa64,
                style_name=args.style,
                negative_prompt=args.negative_prompt,
                guidance_scale=args.guidance_scale,
            )
            paths = save_storydiffusion_outputs(
                repo_dir=repo_dir,
                output_dir=output_dir,
                sample_id=sid,
                images=images,
                prompt_array=[prepared["prompt_array"][i] for i in prepared["visible_indices"]],
                comic_type=args.comic_type,
                font_name=args.font,
            )
            index_rows.append(
                {
                    "id": sid,
                    "baseline": "StoryDiffusion",
                    "image_path": paths["primary"],
                    "prompt": prompt,
                    "metadata": {
                        "seed": sample_seed,
                        "status": "success",
                        "model": generator.model_label,
                        "frames": len(images),
                        "image_paths": paths["all"],
                        "comic_type": args.comic_type,
                        "prompt_file": str(prompt_file.as_posix()),
                        "general_prompt": prepared["general_prompt"],
                        "prompt_array": prepared["prompt_array"],
                        "visible_indices": prepared["visible_indices"],
                        **generation_metadata,
                    },
                }
            )
            write_jsonl(output_dir / "index.jsonl", index_rows)
            print(f"[StoryDiffusion] generated {sid}: {paths['primary']}")
        except Exception as exc:
            if not args.continue_on_error:
                write_jsonl(output_dir / "index.jsonl", index_rows)
                raise
            index_rows.append(
                {
                    "id": sid,
                    "baseline": "StoryDiffusion",
                    "image_path": None,
                    "prompt": prompt,
                    "metadata": {
                        "seed": sample_seed,
                        "status": "failed",
                        "error": str(exc),
                        "model": generator.model_label,
                        "prompt_file": str(prompt_file.as_posix()),
                    },
                }
            )
            write_jsonl(output_dir / "index.jsonl", index_rows)
            print(f"[StoryDiffusion] failed {sid}: {exc}")

    print(f"Wrote StoryDiffusion index to {output_dir / 'index.jsonl'}")


if __name__ == "__main__":
    main()
