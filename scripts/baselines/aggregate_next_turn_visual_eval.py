from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "baselines" / "next_turn_visual_eval"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate next-turn visual evaluation outputs into concise comparison tables."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def write_markdown_table(path: Path, title: str, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    lines = [f"# {title}", ""]
    lines.append("| " + " | ".join(fieldnames) + " |")
    lines.append("| " + " | ".join("---" for _ in fieldnames) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fieldnames) + " |")
    if not rows:
        lines.append("| " + " | ".join("" for _ in fieldnames) + " |")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    comparison_dir = output_dir / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)

    inventory = load_json(output_dir / "inventory.json").get("inventory", [])
    smoke_manifest = load_json(output_dir / "smoke" / "run_manifest.json")
    formal_manifest = load_json(output_dir / "formal" / "run_manifest.json")

    formal_by_baseline = {row["baseline"]: row for row in formal_manifest.get("records", [])}

    comparison_rows: list[dict[str, Any]] = []
    not_evaluable_rows: list[dict[str, Any]] = []
    for item in inventory:
        formal_row = formal_by_baseline.get(item["baseline"])
        summary_payload = None
        summary_path = None
        if formal_row and formal_row.get("summary_path"):
            summary_path = Path(formal_row["summary_path"])
            if summary_path.is_file():
                summary_payload = load_json(summary_path)

        if summary_payload:
            comparison_rows.append(
                {
                    "baseline": item["baseline"],
                    "sample_count": summary_payload.get("processed_rows"),
                    "successful_pairs": summary_payload.get("processed_rows"),
                    "mean": summary_payload.get("score_mean"),
                    "std": summary_payload.get("score_std_population"),
                    "min": summary_payload.get("score_min"),
                    "max": summary_payload.get("score_max"),
                    "note": "",
                }
            )
        else:
            reason = item.get("blocker") or (formal_row or {}).get("reason") or "not_evaluable"
            not_evaluable_rows.append(
                {
                    "baseline": item["baseline"],
                    "source_kind": item["source_kind"],
                    "candidate_pairs": item["candidate_next_turn_pairs"],
                    "evaluable_pairs": item["evaluable_pairs"],
                    "reason": reason,
                }
            )

    comparison_fields = ["baseline", "sample_count", "successful_pairs", "mean", "std", "min", "max", "note"]
    write_csv(comparison_dir / "comparison_table.csv", comparison_rows, comparison_fields)
    write_markdown_table(comparison_dir / "comparison_table.md", "Comparison Table", comparison_rows, comparison_fields)

    not_evaluable_fields = ["baseline", "source_kind", "candidate_pairs", "evaluable_pairs", "reason"]
    write_csv(comparison_dir / "not_evaluable.csv", not_evaluable_rows, not_evaluable_fields)
    write_markdown_table(
        comparison_dir / "not_evaluable.md", "Not Evaluable Baselines", not_evaluable_rows, not_evaluable_fields
    )

    summary_payload = {
        "inventory_baseline_count": len(inventory),
        "smoke_record_count": len(smoke_manifest.get("records", [])),
        "formal_record_count": len(formal_manifest.get("records", [])),
        "comparable_baseline_count": len(comparison_rows),
        "not_evaluable_baseline_count": len(not_evaluable_rows),
        "top_baseline": comparison_rows[0]["baseline"] if comparison_rows else None,
        "notes": (
            ["No baseline had local image pairs available for strict local-only next-turn DINOv2 evaluation."]
            if not comparison_rows
            else ["Comparison table ranks only baselines with completed formal DINOv2 summaries."]
        ),
    }
    (comparison_dir / "summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary_lines = [
        "# Summary",
        "",
        f"- inventory_baseline_count: `{summary_payload['inventory_baseline_count']}`",
        f"- comparable_baseline_count: `{summary_payload['comparable_baseline_count']}`",
        f"- not_evaluable_baseline_count: `{summary_payload['not_evaluable_baseline_count']}`",
    ]
    for note in summary_payload["notes"]:
        summary_lines.append(f"- note: {note}")
    (comparison_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(json.dumps({"comparison_dir": str(comparison_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
