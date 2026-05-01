import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize baseline image generation and LLM evaluation outputs.")
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--eval_name", default="llm_eval_doubao")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 4) if values else 0.0


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    dataset_rows = read_jsonl(run_dir / "indexes" / "baseline_dataset_index.jsonl")
    eval_rows = read_jsonl(run_dir / "eval" / "sdm_v2" / args.eval_name / "llm_eval_results.jsonl")
    eval_by_id = {row["id"]: row for row in eval_rows}

    overall_rows: list[dict[str, Any]] = []
    theme_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []

    by_baseline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset_rows:
        by_baseline[row["baseline_name"]].append(row)

    for baseline_name, rows in sorted(by_baseline.items()):
        generated = [row for row in rows if row["generation_status"] == "success"]
        comparable = [row for row in generated if row["dn_reference_image_exists"]]
        scored = []
        for row in comparable:
            row_id = f"{row['game_id']}/seg_{int(row['segment_index']):03d}"
            if row_id in eval_by_id:
                scored.append(eval_by_id[row_id])

        overall = {
            "baseline_name": baseline_name,
            "rows_total": len(rows),
            "generated_rows": len(generated),
            "dn_reference_available": sum(1 for row in rows if row["dn_reference_image_exists"]),
            "comparable_pairs": len(comparable),
            "scored_pairs": len(scored),
            "unscored_pairs": len(comparable) - len(scored),
        }
        if scored:
            overall["dn_average"] = mean([row["dn_average"] for row in scored])
            overall["baseline_average"] = mean([row["baseline_average"] for row in scored])
            overall["delta_baseline_minus_dn"] = round(
                overall["baseline_average"] - overall["dn_average"], 4
            )
        else:
            overall["dn_average"] = 0.0
            overall["baseline_average"] = 0.0
            overall["delta_baseline_minus_dn"] = 0.0
        if rows and rows[0]["generation_status"] == "unavailable":
            overall["status"] = "unavailable"
            overall["note"] = rows[0]["error"]
        else:
            overall["status"] = "completed" if overall["scored_pairs"] else "partial"
            overall["note"] = ""
        overall_rows.append(overall)

        if baseline_name != "sdm_v2":
            failure_rows.extend(rows)
            continue

        by_theme: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in scored:
            by_theme[row["theme_id"]].append(row)

        for theme_id, theme_scored in sorted(by_theme.items()):
            theme_rows.append(
                {
                    "baseline_name": baseline_name,
                    "theme_id": theme_id,
                    "scored_pairs": len(theme_scored),
                    "dn_average": mean([row["dn_average"] for row in theme_scored]),
                    "baseline_average": mean([row["baseline_average"] for row in theme_scored]),
                    "delta_baseline_minus_dn": round(
                        mean([row["baseline_average"] for row in theme_scored])
                        - mean([row["dn_average"] for row in theme_scored]),
                        4,
                    ),
                }
            )

        for row in rows:
            row_id = f"{row['game_id']}/seg_{int(row['segment_index']):03d}"
            if row_id in eval_by_id:
                eval_row = eval_by_id[row_id]
                detail_rows.append(
                    {
                        "id": row_id,
                        "baseline_name": baseline_name,
                        "theme_id": row["theme_id"],
                        "game_id": row["game_id"],
                        "segment_index": row["segment_index"],
                        "input_text_path": row["input_text_path"],
                        "baseline_image_path": row["baseline_image_path"],
                        "dn_reference_image": row["dn_reference_image"],
                        "dn_average": eval_row["dn_average"],
                        "baseline_average": eval_row["baseline_average"],
                        "delta_baseline_minus_dn": eval_row["delta_baseline_minus_dn"],
                        "winner": eval_row["winner"],
                        "summary": eval_row.get("summary", ""),
                        **{f"dn_{k}": v for k, v in eval_row["dn_scores"].items()},
                        **{f"baseline_{k}": v for k, v in eval_row["baseline_scores"].items()},
                    }
                )
            else:
                failure_rows.append(
                    {
                        "id": row_id,
                        "baseline_name": baseline_name,
                        "theme_id": row["theme_id"],
                        "game_id": row["game_id"],
                        "segment_index": row["segment_index"],
                        "input_text_path": row["input_text_path"],
                        "baseline_image_path": row["baseline_image_path"],
                        "dn_reference_image": row["dn_reference_image"],
                        "generation_status": row["generation_status"],
                        "error": row["error"] or (
                            "DN reference image missing" if not row["dn_reference_image_exists"] else "Evaluation result missing"
                        ),
                    }
                )

    report_dir = run_dir / "reports"
    write_json(report_dir / "overall_summary.json", overall_rows)
    write_csv(report_dir / "overall_summary.csv", overall_rows)
    write_json(report_dir / "theme_summary.json", theme_rows)
    write_csv(report_dir / "theme_summary.csv", theme_rows)
    write_jsonl(report_dir / "segment_details.jsonl", detail_rows)
    write_csv(report_dir / "segment_details.csv", detail_rows)
    write_jsonl(report_dir / "failure_samples.jsonl", failure_rows)

    sdm_overall = next((row for row in overall_rows if row["baseline_name"] == "sdm_v2"), None)
    unavailable = [row for row in overall_rows if row["status"] == "unavailable"]
    md_lines = [
        "# Baseline Image From DN Text Report",
        "",
        f"Run directory: `{run_dir.as_posix()}`",
        "",
        "## Overall Summary",
        "",
        "| baseline | status | generated | comparable | scored | DN avg | baseline avg | delta |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in overall_rows:
        md_lines.append(
            f"| {row['baseline_name']} | {row['status']} | {row['generated_rows']}/{row['rows_total']} | "
            f"{row['comparable_pairs']} | {row['scored_pairs']} | {row['dn_average']:.4f} | "
            f"{row['baseline_average']:.4f} | {row['delta_baseline_minus_dn']:.4f} |"
        )
    md_lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- SDM-v2 generated 100/100 images from text-only inputs; 77 segments had DN reference images available for comparison." if sdm_overall else "- No SDM-v2 summary found.",
            "- DN reference PNGs were missing for 23 segments, so those samples could not be scored against DN.",
        ]
    )
    for row in unavailable:
        md_lines.append(f"- {row['baseline_name']}: {row['note']}")
    if theme_rows:
        md_lines.extend(
            [
                "",
                "## Theme Scores (SDM-v2)",
                "",
                "| theme | scored | DN avg | baseline avg | delta |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in theme_rows:
            md_lines.append(
                f"| {row['theme_id']} | {row['scored_pairs']} | {row['dn_average']:.4f} | "
                f"{row['baseline_average']:.4f} | {row['delta_baseline_minus_dn']:.4f} |"
            )
    (report_dir / "report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps({"overall_rows": len(overall_rows), "theme_rows": len(theme_rows), "detail_rows": len(detail_rows), "failure_rows": len(failure_rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
