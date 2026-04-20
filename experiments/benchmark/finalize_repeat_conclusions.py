from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = REPO_ROOT / "experiments" / "benchmark"
OUTPUT_DIR = BENCHMARK_DIR / "outputs"
STANDARD_DIR = BENCHMARK_DIR / "standard_runs"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    repeat_summary = read_json(OUTPUT_DIR / "benchmark_v1_ab_repeat_validation_summary.json")
    fullchain_summary = read_json(STANDARD_DIR / "benchmark_v1_fullchain_default_20.json")["summary"]
    effect_proxy = read_json(OUTPUT_DIR / "effectiveness_proxies_summary.json")
    benchmark_meta = read_json(BENCHMARK_DIR / "dn_quality_benchmark_v1.json")

    stable_conclusions = [
        {
            "conclusion_id": "stable_001",
            "scope": "benchmark_v1 / worldview",
            "statement": "在 DN-quality-benchmark-v1 上，no_council 在两轮 repeat 中都显著快于 default。",
            "evidence": "run1: mean 20.031s vs 33.657s; run2: mean 20.456s vs 42.008s; 40-run combined: 20.244s vs 37.832s",
            "confidence": "high",
        },
        {
            "conclusion_id": "stable_002",
            "scope": "benchmark_v1 / worldview",
            "statement": "no_council 的中位数与 p95 也优于 default，说明优势不只体现在平均值。",
            "evidence": "combined median 16.046s vs 30.002s; combined p95 40.133s vs 81.879s",
            "confidence": "high",
        },
        {
            "conclusion_id": "stable_003",
            "scope": "benchmark_v1 / fullchain default",
            "statement": "default full-chain 在 20 个 benchmark 样本上全部成功跑通。",
            "evidence": "full_success_count 20 / sample_size 20",
            "confidence": "high",
        },
        {
            "conclusion_id": "stable_004",
            "scope": "post-fix / fullchain default",
            "statement": "当前 full-chain 的主要体感瓶颈仍是 worldview 阶段与主角图完成时间，而不是 generate-option 的典型路径。",
            "evidence": "fullchain default 20: worldview median 9.003s, generate-option median 0.022s, main-character median 56.546s",
            "confidence": "medium_high",
        },
        {
            "conclusion_id": "stable_005",
            "scope": "post-fix / quality guardrails",
            "statement": "在已统计的 post-fix 样本里，基本可玩性护栏指标表现稳定。",
            "evidence": "effectiveness proxies: worldview/scene/image/main-character success rates are all 1.0 in current tracked sample",
            "confidence": "medium",
        },
    ]

    pending_conclusions = [
        {
            "conclusion_id": "pending_001",
            "scope": "benchmark_v1 / fullchain",
            "statement": "no_council 是否在 full-chain 上同样更优，尚未验证。",
            "why_pending": "目前只做了 worldview 的 repeat A/B，没有做 no_council full-chain repeat。",
        },
        {
            "conclusion_id": "pending_002",
            "scope": "benchmark_v1 / quality",
            "statement": "no_council 的效率提升是否伴随质量退化，尚未通过人工评分协议验证。",
            "why_pending": "当前只有自动效果代理，没有完成双人或抽样人工评分。",
        },
        {
            "conclusion_id": "pending_003",
            "scope": "concurrency / no_council",
            "statement": "并发场景下 no_council 是否仍优于 default，尚未验证。",
            "why_pending": "当前并发实验只在 default 上完成。",
        },
    ]

    executive_rows = [
        {
            "section": "benchmark_v1_worldview_default_combined_40",
            "metric": "mean_s",
            "value": repeat_summary["default_combined_40"]["mean"],
        },
        {
            "section": "benchmark_v1_worldview_default_combined_40",
            "metric": "median_s",
            "value": repeat_summary["default_combined_40"]["median"],
        },
        {
            "section": "benchmark_v1_worldview_default_combined_40",
            "metric": "p95_s",
            "value": repeat_summary["default_combined_40"]["p95"],
        },
        {
            "section": "benchmark_v1_worldview_no_council_combined_40",
            "metric": "mean_s",
            "value": repeat_summary["no_council_combined_40"]["mean"],
        },
        {
            "section": "benchmark_v1_worldview_no_council_combined_40",
            "metric": "median_s",
            "value": repeat_summary["no_council_combined_40"]["median"],
        },
        {
            "section": "benchmark_v1_worldview_no_council_combined_40",
            "metric": "p95_s",
            "value": repeat_summary["no_council_combined_40"]["p95"],
        },
        {
            "section": "benchmark_v1_pairwise_run1",
            "metric": "faster_no_council",
            "value": repeat_summary["pairwise_run1"]["faster_no_council"],
        },
        {
            "section": "benchmark_v1_pairwise_run2",
            "metric": "faster_no_council",
            "value": repeat_summary["pairwise_run2"]["faster_no_council"],
        },
        {
            "section": "benchmark_v1_fullchain_default_20",
            "metric": "worldview_median_s",
            "value": fullchain_summary["worldview_elapsed_s"]["median"],
        },
        {
            "section": "benchmark_v1_fullchain_default_20",
            "metric": "generate_option_median_s",
            "value": fullchain_summary["generate_option_elapsed_s"]["median"],
        },
        {
            "section": "benchmark_v1_fullchain_default_20",
            "metric": "main_character_median_s",
            "value": fullchain_summary["main_character_completion_s"]["median"],
        },
        {
            "section": "quality_guardrails",
            "metric": "playable_success_rate",
            "value": next(
                x["value"]
                for x in effect_proxy["summary_metrics"]
                if x["dataset"] == "fullchain_default_12" and x["metric"] == "first_scene_success_rate"
            ),
        },
    ]

    final_payload = {
        "benchmark_name": benchmark_meta["benchmark_name"],
        "version": "repeat_conclusions_v1",
        "stable_conclusions": stable_conclusions,
        "pending_conclusions": pending_conclusions,
        "executive_metrics": executive_rows,
        "source_files": {
            "repeat_summary": str(OUTPUT_DIR / "benchmark_v1_ab_repeat_validation_summary.json"),
            "fullchain_summary": str(STANDARD_DIR / "benchmark_v1_fullchain_default_20.json"),
            "effectiveness_proxy_summary": str(OUTPUT_DIR / "effectiveness_proxies_summary.json"),
        },
    }

    out_json = OUTPUT_DIR / "dn_current_best_conclusions_v1.json"
    out_json.write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(OUTPUT_DIR / "dn_current_best_executive_metrics_v1.csv", executive_rows)
    write_csv(OUTPUT_DIR / "dn_current_best_stable_conclusions_v1.csv", stable_conclusions)
    write_csv(OUTPUT_DIR / "dn_current_best_pending_conclusions_v1.csv", pending_conclusions)
    print(out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
