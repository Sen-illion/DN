from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_RUNS_DIR = REPO_ROOT / "experiments" / "benchmark" / "standard_runs"
REPAIRED_RUNS_DIR = STANDARD_RUNS_DIR / "repaired_v16_pregendepth"
STATUS_JSON = STANDARD_RUNS_DIR / "benchmark_v16_pregendepth_turn4_consistency_status.json"
STATUS_CSV = STANDARD_RUNS_DIR / "benchmark_v16_pregendepth_turn4_consistency_status.csv"
TEXT_OUT_DIR = REPO_ROOT / "experiments" / "qwen3_consistency_eval" / "outputs_v16_pregendepth"
DINO_OUT_DIR = REPO_ROOT / "experiments" / "benchmark" / "dinov2_eval" / "v16_pregendepth_turn4_rw60_formal20"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def choose_run(depth: int) -> Path:
    repaired = REPAIRED_RUNS_DIR / f"benchmark_v16_pregendepth_d{depth}_turn4_rw60_formal20.json"
    if repaired.is_file():
        return repaired
    return STANDARD_RUNS_DIR / f"benchmark_v16_pregendepth_d{depth}_turn4_rw60_formal20.json"


def image_status(run_path: Path) -> tuple[str, int, int]:
    payload = load_json(run_path)
    total = 0
    missing = 0
    for run in payload.get("runs", []):
        for turn in run.get("turns", []):
            url = turn.get("scene_image_url")
            if not isinstance(url, str) or not url.strip():
                continue
            total += 1
            p = Path(url)
            if not p.is_absolute():
                p = (REPO_ROOT / url.lstrip("/\\")).resolve()
            if not p.exists():
                missing += 1
    status = "completed" if total > 0 and missing == 0 else ("missing" if total == 0 else "partial")
    return status, total, missing


def main() -> int:
    rows: list[dict[str, Any]] = []
    text_done = all((TEXT_OUT_DIR / name).is_file() for name in ("system_summary.csv", "scores_long.csv", "failed_samples.jsonl"))
    dino_summary = DINO_OUT_DIR / "comparison" / "summary.json"
    dino_done = dino_summary.is_file()

    for depth in (1, 2, 3, 4):
        run_path = choose_run(depth)
        img_state, img_total, img_missing = image_status(run_path)
        rows.append(
            {
                "depth": depth,
                "run_json": str(run_path),
                "image_status": img_state,
                "image_total": img_total,
                "image_missing": img_missing,
                "text_consistency_status": "completed" if text_done else "missing",
                "dinov2_status": "completed" if dino_done else "missing",
            }
        )

    STATUS_JSON.write_text(json.dumps({"records": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    with STATUS_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(str(STATUS_JSON))
    print(str(STATUS_CSV))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
