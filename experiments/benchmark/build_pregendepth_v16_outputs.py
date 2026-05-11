from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_or_none(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    return load_json(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d1", required=True)
    parser.add_argument("--d2", required=True)
    parser.add_argument("--d3", required=True)
    parser.add_argument("--d4", required=True)
    parser.add_argument("--summary-json", required=True)
    parser.add_argument("--table-csv", required=True)
    parser.add_argument("--paper-table-csv", required=True)
    parser.add_argument(
        "--image-consistency-dir",
        help="Optional v16 DINOv2 output dir containing results/d1..d4/summary.json.",
    )
    parser.add_argument("--image-consistency-d1")
    parser.add_argument("--image-consistency-d2")
    parser.add_argument("--image-consistency-d3")
    parser.add_argument("--image-consistency-d4")
    args = parser.parse_args()

    run_paths = {
        1: Path(args.d1),
        2: Path(args.d2),
        3: Path(args.d3),
        4: Path(args.d4),
    }
    explicit_image_consistency_paths = {
        1: Path(args.image_consistency_d1) if args.image_consistency_d1 else None,
        2: Path(args.image_consistency_d2) if args.image_consistency_d2 else None,
        3: Path(args.image_consistency_d3) if args.image_consistency_d3 else None,
        4: Path(args.image_consistency_d4) if args.image_consistency_d4 else None,
    }

    def image_consistency_summary_path(depth: int) -> Path | None:
        explicit_path = explicit_image_consistency_paths[depth]
        if explicit_path is not None:
            return explicit_path
        if args.image_consistency_dir:
            root = Path(args.image_consistency_dir)
            for candidate in (
                root / "results" / f"d{depth}" / "summary.json",
                root / f"d{depth}" / "summary.json",
            ):
                if candidate.is_file():
                    return candidate
        return None

    runs: dict[int, dict[str, Any]] = {}
    image_consistency_summaries: dict[int, dict[str, Any]] = {}
    table_rows: list[dict[str, Any]] = []
    paper_rows: list[dict[str, Any]] = []

    for depth in (1, 2, 3, 4):
        payload = load_json(run_paths[depth])
        summary = payload.get("summary") or {}
        image_summary_path = image_consistency_summary_path(depth)
        image_summary = load_json_or_none(image_summary_path)
        if image_summary:
            image_consistency_summaries[depth] = {
                "summary_path": str(image_summary_path),
                "metric": image_summary.get("metric"),
                "processed_rows": image_summary.get("processed_rows"),
                "score_mean": image_summary.get("score_mean"),
                "score_std_population": image_summary.get("score_std_population"),
                "score_min": image_summary.get("score_min"),
                "score_max": image_summary.get("score_max"),
            }
        image_consistency_value = (
            round(float(image_summary["score_mean"]), 4)
            if image_summary and image_summary.get("score_mean") is not None
            else "pending_eval_from_dataset"
        )
        runs[depth] = summary
        table_rows.append(
            {
                "pregeneration_rounds": depth,
                "sample_size": summary.get("sample_size"),
                "turn_count": summary.get("turn_count"),
                "read_wait_s": summary.get("read_wait_s"),
                "avg_generation_speed_s": summary.get("avg_generation_speed_s"),
                "turn2_full_ready_mean_s": summary.get("turn2_full_ready_mean_s"),
                "turn3_full_ready_mean_s": summary.get("turn3_full_ready_mean_s"),
                "turn4_full_ready_mean_s": summary.get("turn4_full_ready_mean_s"),
                "strict_success_count": summary.get("strict_success_count"),
                "strict_success_rate": summary.get("strict_success_rate"),
                "placeholder_rate": summary.get("placeholder_rate"),
                "direct_image_rate": summary.get("direct_image_rate"),
                "async_image_rate": summary.get("async_image_rate"),
                "provider_429_count": summary.get("provider_429_count"),
                "provider_timeout_count": summary.get("provider_timeout_count"),
                "provider_retry_heavy_count": summary.get("provider_retry_heavy_count"),
                "evidence_path": str(run_paths[depth]),
                "notes": summary.get("notes", ""),
            }
        )
        paper_rows.append(
            {
                "pregeneration_rounds": depth,
                "avg_generation_speed_s": summary.get("avg_generation_speed_s"),
                "text_consistency": "pending_eval_from_dataset",
                "image_consistency": image_consistency_value,
                "notes": (
                    "fixed_path depth ablation on formal20; speed metric is mean full-ready latency of turn2-4; "
                    "image_consistency is mean DINOv2 adjacent-turn cosine"
                    if image_summary
                    else "fixed_path depth ablation on formal20; metric is mean full-ready latency of turn2-4"
                ),
            }
        )

    summary_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_paths": {str(k): str(v) for k, v in run_paths.items()},
        "image_consistency_metric": "dinov2_cosine_adjacent_turn_mean",
        "image_consistency_summaries": {str(k): v for k, v in image_consistency_summaries.items()},
        "depth_summaries": {str(k): runs[k] for k in (1, 2, 3, 4)},
        "table_rows": table_rows,
        "paper_table_rows": paper_rows,
    }

    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(Path(args.table_csv), table_rows)
    write_csv(Path(args.paper_table_csv), paper_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
