from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POSTFIX_DIR = REPO_ROOT / "experiments" / "efficiency_postfix"
BENCHMARK_DIR = REPO_ROOT / "experiments" / "benchmark"
OUTPUT_DIR = BENCHMARK_DIR / "outputs"


POLLUTION_PATTERNS = [
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"data:image", re.IGNORECASE),
    re.compile(r"traceback", re.IGNORECASE),
    re.compile(r"debug", re.IGNORECASE),
    re.compile(r"error", re.IGNORECASE),
]


FALLBACK_HINTS = [
    "当前内容生成耗时较长",
    "继续推进剧情",
    "查看周围环境",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def has_pollution(text: str) -> bool:
    if not text:
        return False
    for pattern in POLLUTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def looks_garbled(text: str) -> bool:
    if not text:
        return False
    return "閰" in text or "鈥" in text or "锛" in text or "鎴" in text


def aggregate_metric(values: list[int | float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "sum": sum(values),
        "rate": round(sum(values) / len(values), 4) if all(v in (0, 1) for v in values) else None,
        "mean": round(sum(values) / len(values), 4),
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    full_v2 = read_json(POSTFIX_DIR / "fullchain_default_v2_4themes.json")
    full_v3 = read_json(POSTFIX_DIR / "fullchain_default_v3_8themes.json")
    world_default = read_json(POSTFIX_DIR / "worldview_default_v2_8themes.json")
    world_no = read_json(POSTFIX_DIR / "worldview_no_council_v2_8themes.json")
    benchmark = read_json(BENCHMARK_DIR / "dn_quality_benchmark_v1.json")

    benchmark_map = {item["theme_id"]: item for item in benchmark["items"]}

    full_runs = full_v2["runs"] + full_v3["runs"]
    full_rows = []
    for run in full_runs:
        theme_id = run["theme_id"]
        bench_item = benchmark_map.get(theme_id, {})
        world = run["worldview"]
        option = run["generate_option"]
        mc = run["main_character"]
        option_data = option.get("response_json", {}).get("optionData", {})
        scene = option_data.get("scene", "") or ""
        next_options = option_data.get("next_options", []) or []
        scene_image = option_data.get("scene_image", {}) or {}
        scene_prompt = scene_image.get("prompt", "") or ""

        protagonist_metadata_path = REPO_ROOT / "initial" / "main_character" / str(world.get("game_id") or "") / "metadata.json"
        protagonist_prompt = ""
        protagonist_prompt_polluted = 0
        protagonist_prompt_garbled = 0
        if protagonist_metadata_path.exists():
            try:
                metadata = json.loads(protagonist_metadata_path.read_text(encoding="utf-8"))
                protagonist_prompt = (
                    ((metadata.get("views") or {}).get("front") or {}).get("prompt")
                    or metadata.get("prompt")
                    or ""
                )
            except Exception:
                protagonist_prompt = ""
        if has_pollution(protagonist_prompt):
            protagonist_prompt_polluted = 1
        if looks_garbled(protagonist_prompt):
            protagonist_prompt_garbled = 1

        row = {
            "experiment_group": "fullchain_default",
            "benchmark_id": bench_item.get("benchmark_id", ""),
            "theme_id": theme_id,
            "theme": run["theme"],
            "worldview_success": int(world.get("status") == "success"),
            "first_scene_success": int(option.get("status") == "success"),
            "scene_non_empty": int(bool(scene.strip())),
            "next_options_count": len(next_options),
            "option_count_ge_2": int(len(next_options) >= 2),
            "image_returned": int(option.get("has_image") is True),
            "main_character_completed": int(mc.get("completed") is True),
            "fallback_triggered": int(any(hint in scene for hint in FALLBACK_HINTS)),
            "scene_prompt_polluted": int(has_pollution(scene_prompt)),
            "scene_prompt_garbled": int(looks_garbled(scene_prompt)),
            "protagonist_prompt_polluted": protagonist_prompt_polluted,
            "protagonist_prompt_garbled": protagonist_prompt_garbled,
            "worldview_elapsed_s": world.get("elapsed_s"),
            "generate_option_elapsed_s": option.get("elapsed_s"),
            "main_character_completion_s": mc.get("elapsed_s"),
            "queue_mean_ms": run.get("provider_events", {}).get("queue_wait_ms", {}).get("mean"),
        }
        full_rows.append(row)

    worldview_rows = []
    for label, payload in [("default", world_default), ("no_council", world_no)]:
        for run in payload["runs"]:
            global_state = run.get("response_json", {}).get("globalState", {}) or {}
            worldview_text = (
                ((global_state.get("core_worldview") or {}).get("main_quest") or "")
                + " "
                + ((global_state.get("core_worldview") or {}).get("world_basic_setting") or "")
            )
            worldview_rows.append(
                {
                    "experiment_group": f"worldview_{label}",
                    "theme_id": run["theme_id"],
                    "theme": run["theme"],
                    "status_success": int(run.get("status") == "success"),
                    "has_global_state": int(run.get("has_global_state") is True),
                    "worldview_text_non_empty": int(bool(worldview_text.strip())),
                    "worldview_text_garbled": int(looks_garbled(worldview_text)),
                    "elapsed_s": run.get("elapsed_s"),
                    "queue_mean_ms": run.get("provider_events", {}).get("queue_wait_ms", {}).get("mean"),
                }
            )

    summary_rows = [
        {
            "dataset": "fullchain_default_12",
            "metric": "worldview_success_rate",
            "value": round(sum(r["worldview_success"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "first_scene_success_rate",
            "value": round(sum(r["first_scene_success"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "image_return_rate",
            "value": round(sum(r["image_returned"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "main_character_completion_rate",
            "value": round(sum(r["main_character_completed"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "option_count_ge_2_rate",
            "value": round(sum(r["option_count_ge_2"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "fallback_trigger_rate",
            "value": round(sum(r["fallback_triggered"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "scene_prompt_pollution_rate",
            "value": round(sum(r["scene_prompt_polluted"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "protagonist_prompt_pollution_rate",
            "value": round(sum(r["protagonist_prompt_polluted"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "fullchain_default_12",
            "metric": "protagonist_prompt_garbled_rate",
            "value": round(sum(r["protagonist_prompt_garbled"] for r in full_rows) / len(full_rows), 4),
        },
        {
            "dataset": "worldview_default_8",
            "metric": "worldview_success_rate",
            "value": round(sum(r["status_success"] for r in worldview_rows if r["experiment_group"] == "worldview_default") / 8, 4),
        },
        {
            "dataset": "worldview_no_council_8",
            "metric": "worldview_success_rate",
            "value": round(sum(r["status_success"] for r in worldview_rows if r["experiment_group"] == "worldview_no_council") / 8, 4),
        },
        {
            "dataset": "worldview_default_8",
            "metric": "garbled_text_rate",
            "value": round(sum(r["worldview_text_garbled"] for r in worldview_rows if r["experiment_group"] == "worldview_default") / 8, 4),
        },
        {
            "dataset": "worldview_no_council_8",
            "metric": "garbled_text_rate",
            "value": round(sum(r["worldview_text_garbled"] for r in worldview_rows if r["experiment_group"] == "worldview_no_council") / 8, 4),
        },
    ]

    def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_csv(OUTPUT_DIR / "effectiveness_proxies_fullchain_12.csv", full_rows)
    write_csv(OUTPUT_DIR / "effectiveness_proxies_worldview_16.csv", worldview_rows)
    write_csv(OUTPUT_DIR / "effectiveness_proxies_summary.csv", summary_rows)

    summary_json = {
        "benchmark_name": benchmark["benchmark_name"],
        "fullchain_rows": len(full_rows),
        "worldview_rows": len(worldview_rows),
        "summary_metrics": summary_rows,
        "notes": [
            "prompt_pollution_rate 目前使用规则匹配，仅能覆盖显式异常文本",
            "garbled_rate 使用乱码启发式判断，适合作为异常告警而非最终质量结论",
            "该脚本输出的指标用于为效率实验增加效果护栏，不替代人工评分",
        ],
    }
    (OUTPUT_DIR / "effectiveness_proxies_summary.json").write_text(
        json.dumps(summary_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(OUTPUT_DIR / "effectiveness_proxies_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
