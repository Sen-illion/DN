from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "baselines" / "next_turn_visual_eval"
DEFAULT_DINOV2_SCRIPT = REPO_ROOT / "baselines" / "consistency_detection" / "scripts" / "run_dinov2_eval.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local-only next-turn visual consistency evaluation from prebuilt pair CSVs."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mode", choices=["smoke", "formal"], required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--model-name", default="dinov2_vits14")
    parser.add_argument("--limit", type=int, default=0, help="Apply only to smoke runs when > 0.")
    parser.add_argument("--auto-clone", action="store_true")
    parser.add_argument(
        "--only-slug",
        action="append",
        default=[],
        help="Optional slug filter. Repeat or pass comma-separated values such as dn,ic_lora.",
    )
    parser.add_argument(
        "--merge-manifest",
        action="store_true",
        help="Merge newly run records into an existing run_manifest.json instead of replacing unrelated records.",
    )
    return parser.parse_args()


def load_inventory(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("inventory", [])


def count_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def skip_record(item: dict[str, Any], reason: str, pairs_csv: Path) -> dict[str, Any]:
    return {
        "baseline": item["baseline"],
        "slug": item["slug"],
        "pairs_csv": str(pairs_csv),
        "pair_count": count_rows(pairs_csv),
        "status": "skipped",
        "reason": reason,
        "summary_path": None,
        "jsonl_path": None,
    }


def parse_slug_filter(values: list[str]) -> set[str]:
    slugs: set[str] = set()
    for value in values:
        for slug in value.split(","):
            cleaned = slug.strip()
            if cleaned:
                slugs.add(cleaned)
    return slugs


def merge_manifest_records(existing_records: list[dict[str, Any]], new_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def key_for(record: dict[str, Any]) -> str:
        return str(record.get("slug") or record.get("baseline"))

    for record in existing_records:
        key = key_for(record)
        if key not in merged:
            order.append(key)
        merged[key] = record

    for record in new_records:
        key = key_for(record)
        if key not in merged:
            order.append(key)
        merged[key] = record

    return [merged[key] for key in order]


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    inventory_path = output_dir / "inventory.json"
    if not inventory_path.is_file():
        raise FileNotFoundError(f"Inventory not found: {inventory_path}")

    run_dir = output_dir / args.mode
    results_dir = run_dir / "results"
    run_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    manifest_records: list[dict[str, Any]] = []
    only_slugs = parse_slug_filter(args.only_slug)
    for item in load_inventory(inventory_path):
        if only_slugs and item["slug"] not in only_slugs:
            continue

        slug = item["slug"]
        pairs_csv = output_dir / "pairs" / f"{slug}_pairs.csv"
        pair_count = count_rows(pairs_csv)
        if not item.get("evaluable_now"):
            manifest_records.append(
                skip_record(item, item.get("blocker") or "baseline_not_evaluable_now", pairs_csv)
            )
            continue
        if pair_count == 0:
            manifest_records.append(skip_record(item, "no_pairs_csv_rows", pairs_csv))
            continue

        baseline_dir = results_dir / slug
        baseline_dir.mkdir(parents=True, exist_ok=True)
        out_jsonl = baseline_dir / "scores.jsonl"
        out_summary = baseline_dir / "summary.json"

        command = [
            sys.executable,
            str(DEFAULT_DINOV2_SCRIPT),
            "--pairs-csv",
            str(pairs_csv),
            "--out-jsonl",
            str(out_jsonl),
            "--out-summary",
            str(out_summary),
            "--device",
            args.device,
            "--model-name",
            args.model_name,
            "--skip-missing",
        ]
        if args.auto_clone:
            command.append("--auto-clone")
        if args.mode == "smoke" and args.limit > 0:
            command.extend(["--limit", str(args.limit)])

        completed = subprocess.run(command, capture_output=True, text=True)
        record = {
            "baseline": item["baseline"],
            "slug": item["slug"],
            "pairs_csv": str(pairs_csv),
            "pair_count": pair_count,
            "status": "completed" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "summary_path": str(out_summary) if out_summary.exists() else None,
            "jsonl_path": str(out_jsonl) if out_jsonl.exists() else None,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }
        if completed.returncode != 0:
            record["reason"] = "dinov2_eval_command_failed"
        manifest_records.append(record)

    manifest_path = run_dir / "run_manifest.json"
    if args.merge_manifest and manifest_path.is_file():
        existing_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_records = merge_manifest_records(existing_payload.get("records", []), manifest_records)
    payload = {
        "mode": args.mode,
        "model_name": args.model_name,
        "device": args.device,
        "records": manifest_records,
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"manifest_path": str(manifest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
