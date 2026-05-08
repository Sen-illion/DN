"""Export DN benchmark subsets for image baseline smoke/formal runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from baseline_io import build_visual_prompts, load_json, write_json


SMOKE_IDS = ["DNQBV1_001", "DNQBV1_002", "DNQBV1_005"]
FORMAL_IDS = [
    "DNQBV1_001",
    "DNQBV1_002",
    "DNQBV1_004",
    "DNQBV1_005",
    "DNQBV1_006",
    "DNQBV1_007",
    "DNQBV1_009",
    "DNQBV1_010",
]


def export_subset(source: Path, output: Path, ids: list[str], scene_count: int) -> None:
    data = load_json(source)
    items = data["items"] if isinstance(data, dict) and "items" in data else data
    by_id = {item["benchmark_id"]: item for item in items}
    subset = []
    for benchmark_id in ids:
        item = dict(by_id[benchmark_id])
        item["visual_prompt_pack"] = build_visual_prompts(item, scene_count=scene_count)
        subset.append(item)
    write_json(
        output,
        {
            "subset_name": output.stem,
            "source": str(source),
            "scene_count": scene_count,
            "items": subset,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        default="experiments/benchmark/dn_quality_benchmark_v1.json",
        help="DN benchmark JSON.",
    )
    parser.add_argument("--output-dir", default="baselines/subsets")
    parser.add_argument("--scene-count", type=int, default=4)
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    export_subset(Path(args.source), output_dir / "dn_style_smoke3.json", SMOKE_IDS, args.scene_count)
    export_subset(Path(args.source), output_dir / "dn_style_formal8.json", FORMAL_IDS, args.scene_count)
    print(f"Wrote subsets to {output_dir}")


if __name__ == "__main__":
    main()
