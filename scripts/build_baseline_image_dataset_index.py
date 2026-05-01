import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Join DN text manifest with baseline image outputs.")
    parser.add_argument("--run_dir", required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    manifest_rows = read_jsonl(run_dir / "manifests" / "manifest.jsonl")
    sdm_rows = {row["id"]: row for row in read_jsonl(run_dir / "baselines" / "sdm_v2" / "index.jsonl")}

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    unavailable = {
        "storydiffusion": "Official workflow is Gradio/Notebook-oriented; local wrapper prepares manifests only, no batch image CLI was run.",
        "iclora": "Requires ComfyUI + FLUX + IC-LoRA weights; local wrapper prepares workflows only, no image generation was run.",
    }

    for manifest in manifest_rows:
        sdm = sdm_rows.get(manifest["id"])
        row = {
            "baseline_name": "sdm_v2",
            "theme_id": manifest["theme_id"],
            "game_id": manifest["game_id"],
            "segment_index": manifest["segment_index"],
            "input_text_path": manifest["source_text_json"],
            "text_prompt": manifest["text_prompt"],
            "prompt_source": manifest["prompt_source"],
            "baseline_image_path": sdm.get("image_path", "") if sdm else "",
            "dn_reference_image": manifest["dn_reference_image"],
            "dn_reference_image_exists": manifest["dn_reference_image_exists"],
            "generation_status": sdm.get("status", "missing_output") if sdm else "missing_output",
            "error": "" if sdm else "No SDM-v2 output index row found",
        }
        rows.append(row)
        if row["generation_status"] != "success" or not row["dn_reference_image_exists"]:
            failures.append(row)

    for baseline, reason in unavailable.items():
        for manifest in manifest_rows:
            row = {
                "baseline_name": baseline,
                "theme_id": manifest["theme_id"],
                "game_id": manifest["game_id"],
                "segment_index": manifest["segment_index"],
                "input_text_path": manifest["source_text_json"],
                "text_prompt": manifest["text_prompt"],
                "prompt_source": manifest["prompt_source"],
                "baseline_image_path": "",
                "dn_reference_image": manifest["dn_reference_image"],
                "dn_reference_image_exists": manifest["dn_reference_image_exists"],
                "generation_status": "unavailable",
                "error": reason,
            }
            rows.append(row)
            failures.append(row)

    out_dir = run_dir / "indexes"
    write_jsonl(out_dir / "baseline_dataset_index.jsonl", rows)
    write_csv(out_dir / "baseline_dataset_index.csv", rows)
    write_jsonl(out_dir / "failure_samples.jsonl", failures)

    summary: dict[str, Any] = {}
    for baseline in sorted({row["baseline_name"] for row in rows}):
        b_rows = [row for row in rows if row["baseline_name"] == baseline]
        summary[baseline] = {
            "rows": len(b_rows),
            "generated": sum(1 for row in b_rows if row["generation_status"] == "success"),
            "dn_reference_available": sum(1 for row in b_rows if row["dn_reference_image_exists"]),
            "failures_or_unscored": sum(
                1 for row in b_rows if row["generation_status"] != "success" or not row["dn_reference_image_exists"]
            ),
        }
    (out_dir / "baseline_dataset_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
