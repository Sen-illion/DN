"""Run SDM-v2 / stable-diffusion-2-1-base on DN-style prompts."""

from __future__ import annotations

import os
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
    write_failure,
    write_json,
)


BASELINE = "sdmv2"
MODEL_ID = "stabilityai/stable-diffusion-2-1-base"
LOCAL_MODEL_DIR = "/root/autodl-tmp/models/stable-diffusion-2-1-base"


def resolve_default_model_id() -> str:
    env_path = os.environ.get("SDMV2_LOCAL_MODEL_DIR")
    if env_path and Path(env_path).exists():
        return env_path
    if Path(LOCAL_MODEL_DIR).exists():
        return LOCAL_MODEL_DIR
    return MODEL_ID


def generate_image(pipe, prompt: str, negative_prompt: str | None, args, torch_module):
    generator = torch_module.Generator(device="cuda" if torch_module.cuda.is_available() else "cpu").manual_seed(args.seed)
    return pipe(
        prompt,
        negative_prompt=negative_prompt,
        height=args.height,
        width=args.width,
        num_inference_steps=args.steps,
        guidance_scale=args.guidance_scale,
        generator=generator,
    ).images[0]


def build_next_turn_result(item, prompt_pack, sample_dir: Path, pipe, args, torch_module) -> dict:
    current_prompt = prompt_pack["prompts"][0]
    current_image = generate_image(pipe, current_prompt, prompt_pack.get("negative_prompt"), args, torch_module)
    previous_image_paths = save_pil_images([current_image], sample_dir, prefix="current_image")

    next_turn = build_next_turn_prompt(item, prompt_pack, args.player_action)
    request_start_ts = time.time()
    start = time.perf_counter()
    next_image = generate_image(pipe, next_turn["continuation_prompt"], prompt_pack.get("negative_prompt"), args, torch_module)
    latency = time.perf_counter() - start
    first_playable_ts = request_start_ts + latency
    finish_ts = first_playable_ts
    image_paths = save_pil_images([next_image], sample_dir)
    input_bundle = build_input_bundle(
        item,
        prompt_pack,
        mode="next_turn",
        player_action=args.player_action,
        previous_image_paths=previous_image_paths,
    )
    raw_output = {
        "current_prompt": current_prompt,
        "continuation_prompt": next_turn["continuation_prompt"],
        "previous_image_paths": previous_image_paths,
        "image_paths": image_paths,
        "narrative_response": "SDM-v2 generated a continuation image after the simulated player click.",
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
        notes=["SDM-v2 next-turn latency measures only the post-click continuation image."],
        extra={"model_id": args.model_id},
    )
    playable.update(
        result_payload(
            item,
            BASELINE,
            "success",
            [next_turn["continuation_prompt"]],
            latency_s=latency,
            image_paths=image_paths,
            extra={"model_id": args.model_id, "mode": "next_turn"},
        )
    )
    write_json(sample_dir / "prompt.json", {"first_turn_prompt": current_prompt, "next_turn": next_turn, "input_bundle": input_bundle})
    write_json(sample_dir / "result.json", playable)
    return playable


def main() -> None:
    parser = common_parser("Run stable-diffusion-2-1-base with diffusers.")
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--guidance-scale", type=float, default=7.5)
    parser.add_argument("--model-id", default=resolve_default_model_id())
    parser.add_argument("--mode", choices=["first_turn", "next_turn"], default="first_turn")
    parser.add_argument("--player-action", default=DEFAULT_NEXT_TURN_ACTION)
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
    except Exception as exc:  # pragma: no cover
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
                extra={"model_id": args.model_id, "mode": args.mode},
            )
            write_json(sample_dir / "result.json", payload)
            results.append(payload)
        summarize_results(
            run_dir,
            BASELINE,
            results,
            notes="SDM-v2 model load blocked before generation; likely gated model access or network/cache issue.",
            mode=args.mode,
        )
        print(run_dir)
        return

    for item, prompt_pack, prompts in prompt_packs:
        sample_dir = run_dir / str(item["benchmark_id"])
        sample_dir.mkdir(parents=True, exist_ok=True)
        try:
            if args.mode == "next_turn":
                results.append(build_next_turn_result(item, prompt_pack, sample_dir, pipe, args, torch))
                continue
            write_json(sample_dir / "prompt.json", prompt_pack)
            start = time.perf_counter()
            image = generate_image(pipe, prompts[0], prompt_pack.get("negative_prompt"), args, torch)
            latency = time.perf_counter() - start
            image_paths = save_pil_images([image], sample_dir)
            payload = result_payload(
                item,
                BASELINE,
                "success",
                prompts,
                latency,
                image_paths,
                extra={"model_id": args.model_id, "mode": "first_turn"},
            )
            write_json(sample_dir / "result.json", payload)
            results.append(payload)
        except Exception as exc:  # pragma: no cover
            results.append(write_failure(sample_dir, item, BASELINE, prompts, exc))

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes=(
            "SDM-v2 uses diffusers and generates one image per DN-style item; no character-consistency claim."
            if args.mode == "first_turn"
            else "SDM-v2 next-turn latency measures the post-click continuation image only."
        ),
        mode=args.mode,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
