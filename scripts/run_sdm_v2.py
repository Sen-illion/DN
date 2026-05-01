import argparse
import json
import os
from pathlib import Path
from typing import Any

from baseline_common import read_jsonl, require_prompt, sample_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run stable-diffusion-2-1-base on unified JSONL input.")
    parser.add_argument("--input", required=True, help="Input JSONL with an id and prompt per line.")
    parser.add_argument("--output_dir", required=True, help="Directory for images and index.jsonl.")
    parser.add_argument("--model_id", default="stabilityai/stable-diffusion-2-1-base")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num_inference_steps", type=int, default=20)
    parser.add_argument("--guidance_scale", type=float, default=7.5)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--dtype", default="auto", choices=["auto", "float16", "float32"])
    parser.add_argument("--attention_slicing", action="store_true", help="Enable attention slicing for low VRAM.")
    parser.add_argument("--cpu_offload", action="store_true", help="Enable accelerate CPU offload.")
    parser.add_argument("--local_files_only", action="store_true", help="Do not download missing model files.")
    parser.add_argument("--use_euler", action="store_true", help="Use EulerDiscreteScheduler.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing index or image files.")
    return parser.parse_args()


def ensure_can_write(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite or choose a new output_dir.")


def main() -> None:
    args = parse_args()
    try:
        import torch
        from diffusers import StableDiffusionPipeline
        from diffusers.schedulers import EulerDiscreteScheduler
    except ImportError as exc:
        raise SystemExit(
            "Missing SDM-v2 dependencies. Install: pip install diffusers transformers "
            "accelerate safetensors torch. Original import error: " + str(exc)
        ) from exc

    if args.device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested, but torch.cuda.is_available() is False.")

    if args.dtype == "float16" or (args.dtype == "auto" and device == "cuda"):
        torch_dtype = torch.float16
    else:
        torch_dtype = torch.float32

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    load_kwargs: dict[str, Any] = {
        "torch_dtype": torch_dtype,
        "token": token,
        "local_files_only": args.local_files_only,
        "safety_checker": None,
    }
    if torch_dtype == torch.float16:
        load_kwargs["use_safetensors"] = True
    pipe = StableDiffusionPipeline.from_pretrained(args.model_id, **load_kwargs)
    if args.use_euler:
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    if args.attention_slicing:
        pipe.enable_attention_slicing()
    if args.cpu_offload:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    rows = read_jsonl(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / "index.jsonl"
    ensure_can_write(index_path, args.overwrite)

    image_paths = []
    for idx, row in enumerate(rows):
        sid = sample_id(row, idx)
        image_path = output_dir / f"{sid}.png"
        ensure_can_write(image_path, args.overwrite)
        image_paths.append(image_path)

    with index_path.open("w", encoding="utf-8") as handle:
        for idx, row in enumerate(rows):
            sid = sample_id(row, idx)
            prompt = require_prompt(row)
            seed = args.seed + idx
            generator = torch.Generator(device=device if not args.cpu_offload else "cpu").manual_seed(seed)
            result = pipe(
                prompt,
                generator=generator,
                num_inference_steps=args.num_inference_steps,
                guidance_scale=args.guidance_scale,
                height=args.height,
                width=args.width,
            )
            image_path = image_paths[idx]
            image_path.parent.mkdir(parents=True, exist_ok=True)
            result.images[0].save(image_path)
            row_out = {
                "id": sid,
                "baseline": "SDM-v2",
                "status": "success",
                "image_path": str(image_path.as_posix()),
                "prompt": prompt,
                "metadata": {
                    "model": args.model_id,
                    "seed": seed,
                    "num_inference_steps": args.num_inference_steps,
                    "height": args.height,
                    "width": args.width,
                    "device": device,
                    "dtype": str(torch_dtype).replace("torch.", ""),
                    "attention_slicing": args.attention_slicing,
                    "cpu_offload": args.cpu_offload,
                },
            }
            handle.write(json.dumps(row_out, ensure_ascii=False) + "\n")
            handle.flush()
    print(f"Wrote {len(rows)} image index rows to {index_path}")


if __name__ == "__main__":
    main()
