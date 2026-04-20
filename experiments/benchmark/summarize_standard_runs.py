from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
STANDARD_DIR = REPO_ROOT / "experiments" / "benchmark" / "standard_runs"
OUTPUT_DIR = REPO_ROOT / "experiments" / "benchmark" / "outputs"

POLLUTION_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"data:image", re.IGNORECASE),
    re.compile(r"traceback", re.IGNORECASE),
    re.compile(r"debug", re.IGNORECASE),
    re.compile(r"error", re.IGNORECASE),
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_pollution(text: str) -> bool:
    return any(p.search(text or "") for p in POLLUTION_PATTERNS)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    worldview_default = read_json(STANDARD_DIR / "benchmark_v1_worldview_default_20.json")
    worldview_no = read_json(STANDARD_DIR / "benchmark_v1_worldview_no_council_20.json")
    fullchain = read_json(STANDARD_DIR / "benchmark_v1_fullchain_default_20.json")

    ab_rows = []
    for d, n in zip(worldview_default["runs"], worldview_no["runs"]):
        ab_rows.append(
            {
                "benchmark_id": d["benchmark_id"],
                "theme_id": d["theme_id"],
                "theme": d["theme"],
                "default_elapsed_s": d["elapsed_s"],
                "no_council_elapsed_s": n["elapsed_s"],
                "delta_no_minus_default_s": round(n["elapsed_s"] - d["elapsed_s"], 3),
                "default_queue_mean_ms": d.get("provider_events", {}).get("queue_wait_ms", {}).get("mean"),
                "no_council_queue_mean_ms": n.get("provider_events", {}).get("queue_wait_ms", {}).get("mean"),
                "default_status": d["status"],
                "no_council_status": n["status"],
            }
        )

    fullchain_rows = []
    for run in fullchain["runs"]:
        option = run.get("generate_option", {})
        option_data = option.get("response_json", {}).get("optionData", {}) or {}
        scene = option_data.get("scene", "") or ""
        scene_image = option_data.get("scene_image", {}) or {}
        fullchain_rows.append(
            {
                "benchmark_id": run["benchmark_id"],
                "theme_id": run["theme_id"],
                "theme": run["theme"],
                "worldview_elapsed_s": run["worldview"]["elapsed_s"],
                "generate_option_elapsed_s": option.get("elapsed_s"),
                "main_character_completion_s": run.get("main_character", {}).get("elapsed_s"),
                "has_scene": int(option.get("has_scene") is True),
                "has_image": int(option.get("has_image") is True),
                "option_count": len(option_data.get("next_options") or []),
                "scene_prompt_polluted": int(has_pollution(scene_image.get("prompt", "") or "")),
                "scene_text_non_empty": int(bool(scene.strip())),
                "queue_mean_ms": run.get("provider_events", {}).get("queue_wait_ms", {}).get("mean"),
            }
        )

    summary_rows = [
        {
            "section": "worldview_default_20",
            "metric": "mean_s",
            "value": worldview_default["summary"]["elapsed_s"]["mean"],
        },
        {
            "section": "worldview_default_20",
            "metric": "median_s",
            "value": worldview_default["summary"]["elapsed_s"]["median"],
        },
        {
            "section": "worldview_default_20",
            "metric": "p95_s",
            "value": worldview_default["summary"]["elapsed_s"]["p95"],
        },
        {
            "section": "worldview_no_council_20",
            "metric": "mean_s",
            "value": worldview_no["summary"]["elapsed_s"]["mean"],
        },
        {
            "section": "worldview_no_council_20",
            "metric": "median_s",
            "value": worldview_no["summary"]["elapsed_s"]["median"],
        },
        {
            "section": "worldview_no_council_20",
            "metric": "p95_s",
            "value": worldview_no["summary"]["elapsed_s"]["p95"],
        },
        {
            "section": "fullchain_default_20",
            "metric": "worldview_median_s",
            "value": fullchain["summary"]["worldview_elapsed_s"]["median"],
        },
        {
            "section": "fullchain_default_20",
            "metric": "generate_option_median_s",
            "value": fullchain["summary"]["generate_option_elapsed_s"]["median"],
        },
        {
            "section": "fullchain_default_20",
            "metric": "main_character_median_s",
            "value": fullchain["summary"]["main_character_completion_s"]["median"],
        },
        {
            "section": "fullchain_default_20",
            "metric": "full_success_rate",
            "value": round(fullchain["summary"]["full_success_count"] / fullchain["summary"]["sample_size"], 4),
        },
        {
            "section": "fullchain_default_20",
            "metric": "has_image_rate",
            "value": round(sum(r["has_image"] for r in fullchain_rows) / len(fullchain_rows), 4),
        },
        {
            "section": "fullchain_default_20",
            "metric": "option_count_ge_2_rate",
            "value": round(sum(int(r["option_count"] >= 2) for r in fullchain_rows) / len(fullchain_rows), 4),
        },
    ]

    write_csv(OUTPUT_DIR / "benchmark_v1_worldview_ab_20.csv", ab_rows)
    write_csv(OUTPUT_DIR / "benchmark_v1_fullchain_20.csv", fullchain_rows)
    write_csv(OUTPUT_DIR / "benchmark_v1_summary_metrics.csv", summary_rows)

    (OUTPUT_DIR / "benchmark_v1_summary_metrics.json").write_text(
        json.dumps(
            {
                "worldview_default_summary": worldview_default["summary"],
                "worldview_no_council_summary": worldview_no["summary"],
                "fullchain_default_summary": fullchain["summary"],
                "notes": [
                    "这一版是基于 DN-quality-benchmark-v1 的标准化批跑结果",
                    "worldview A/B 与 fullchain default 在不同运行窗口执行，受 provider 实时状态影响",
                    "建议后续再做重复轮次以区分时段波动与配置本身效果",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(OUTPUT_DIR / "benchmark_v1_summary_metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
