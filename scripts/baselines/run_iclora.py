"""IC-LoRA runner placeholder with explicit blocked-result artifacts.

IC-LoRA's public repo primarily documents models/workflows. The first remote
step is to verify workflow/model availability without training. This runner
therefore records a structured blocked status unless a ComfyUI API endpoint is
provided later.
"""

from __future__ import annotations

import time

from baseline_io import (
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


def main() -> None:
    parser = common_parser("Record IC-LoRA workflow readiness for DN-style prompts.")
    parser.add_argument("--comfyui-url", default=None, help="Optional ComfyUI API URL for future execution.")
    parser.add_argument("--workflow", default="baselines/IC-LoRA/workflow/film-storyboard.json")
    args = parser.parse_args()

    items = load_subset(args.subset)
    run_dir = make_run_dir(args.output, BASELINE, args.run_id)
    write_json(run_dir / "config.json", vars(args))
    write_json(run_dir / "environment.json", environment_payload())

    results = []
    for item in items:
        prompt_pack = item.get("visual_prompt_pack") or build_visual_prompts(item, args.scene_count)
        sample_dir = run_dir / str(item["benchmark_id"])
        sample_dir.mkdir(parents=True, exist_ok=True)
        write_json(sample_dir / "prompt.json", prompt_pack)
        payload = result_payload(
            item,
            BASELINE,
            "blocked",
            prompt_pack["prompts"][: args.scene_count],
            latency_s=0.0,
            error=(
                "IC-LoRA training is out of scope for this step. Provide a configured "
                "ComfyUI endpoint and downloaded IC-LoRA weights to enable inference."
            ),
            extra={
                "workflow": args.workflow,
                "comfyui_url": args.comfyui_url,
                "blocked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        write_json(sample_dir / "result.json", payload)
        results.append(payload)

    summarize_results(
        run_dir,
        BASELINE,
        results,
        notes="IC-LoRA smoke currently records workflow/model blocker only; no training is attempted.",
    )
    print(run_dir)


if __name__ == "__main__":
    main()
