"""Run SDM-v2 / stable-diffusion-2-1-base on DN-style prompts."""

from __future__ import annotations

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
    write_json,
)


BASELINE = "sdmv2"
MODEL_ID = "stabilityai/stable-diffusion-2-1-base"


def main() -> None:
    parser = common_parser("Run stable-diffusion-2-1-base with diffusers.")
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--model-id", default=MODEL_ID)
    args = parser.parse_args()

    items = load_subset(args.subset)
    run_dir = make_run_dir(args.output, BASELINE, args.run_id)
    write_json(run_dir / "config.json", vars(args))
    write_json(run_dir / "environment.json", environment_payload())

    results = []
    prompt_packs = []
    for item in items:
        prompt_pack = item.get("visual_prompt_pack") or build_visual_prompts(item, args.scene_count)
        prompt_packs.append((item, prompt_pack, prompt_pack["prompts"][:1]))

    try:
        import torch
        from diffusers import StableDiffusionPipeline

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        pipe = StableDiffusionPipeline.from_pretrained(args.model_id, torch_dtype=dtype)
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        pipe.enable_attention_slicing()
    except Exception as exc:  # pragma: no cover - remote model/runtime dependent
        for item, prompt_pack, prompts in prompt_packs:
            sample_dir = run_dir / str(item["benchmark_id"])
            sample_dir.mkdir(parents=True, exist_ok=True)
            write_json(sample_dir / "prompt.json", prompt_pack)
            payload = result_payload(
                item,
                BASELINE,
                "blocked",
                prompts,
                latency_s=0.0,
                error=f"Model load blocked: {type(exc).__name__}: {exc}",
                extra={"model_id": args.model_id},
            )
            write_json(sample_dir / "result.json", payload)
            results.append(payload)
        summarize_results(
            run_dir,
            BASELINE,
            results,
            notes="SDM-v2 model load blocked before generation; likely gated model access or network/cache issue.",
        )
        print(run_dir)
        return

    for item, prompt_pack, prompts in prompt_packs:
        sample_dir = run_dir / str(item["benchmark_id"])
        sample_dir.mkdir(parents=True, exist_ok=True)
        write_json(sample_dir / "prompt.json", prompt_pack)
        try:
            start = time.perf_counter()
            generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(args.seed)
            image = pipe(
                prompts[0],
                negative_prompt=prompt_pack.get("negative_prompt"),
                height=args.height,
                width=args.width,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance_scale,
                generator=generator,
            ).images[0]
            latency = time.perf_counter() - start
            image_paths = save_pil_images([image], sample_dir)
            payload = result_payload(
                item,
                BASELINE,
                "success",
                prompts,
                latency,
                image_paths,
                extra={"model_id": args.model_id},
            )
            write_json(sample_dir / "result.json", payload)
            results.append(payload)
        except Exception as exc:  # pragma: no cover - remote model/runtime dependent
            results.append(write_failure(sample_dir, item, BASELINE, prompts, exc))

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes="SDM-v2 uses diffusers and generates one image per DN-style item; no character-consistency claim.",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
