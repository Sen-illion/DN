from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "experiments" / "benchmark" / "outputs"


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
    best = read_json(OUTPUT_DIR / "dn_current_best_conclusions_v1.json")
    full_ab = read_json(OUTPUT_DIR / "benchmark_v1_fullchain_ab_summary.json")

    updated_stable = list(best["stable_conclusions"])
    updated_pending = [
        row for row in best["pending_conclusions"] if row["conclusion_id"] != "pending_001"
    ]

    updated_stable.append(
        {
            "conclusion_id": "stable_006",
            "scope": "benchmark_v1 / fullchain",
            "statement": "在 full-chain benchmark-v1 上，no_council 并没有把 worldview 阶段的单点加速转化为更好的整局体验，反而在 worldview 中位数与成功率上不如 default。",
            "evidence": "default fullchain worldview median 9.003s vs no_council 13.799s; success_count 20/20 vs 19/20",
            "confidence": "medium_high",
        }
    )
    updated_stable.append(
        {
            "conclusion_id": "stable_007",
            "scope": "benchmark_v1 / fullchain",
            "statement": "default 仍是更稳妥的 full-chain 基线配置。",
            "evidence": "default fullchain has lower worldview median, lower p95, and no timeout failure in this batch",
            "confidence": "medium_high",
        }
    )

    updated_pending.insert(
        0,
        {
            "conclusion_id": "pending_004",
            "scope": "benchmark_v1 / fullchain mechanism",
            "statement": "为什么 no_council 在 worldview 单点上更快，但在 full-chain 上反而不占优，仍需归因分析。",
            "why_pending": "当前还未拆开 cache、pregeneration、主角图阻塞、provider 排队窗口等因素。",
        },
    )

    exec_rows = list(best["executive_metrics"])
    exec_rows.extend(
        [
            {
                "section": "benchmark_v1_fullchain_default_20",
                "metric": "success_rate",
                "value": round(full_ab["default_fullchain_20"]["success_count"] / full_ab["default_fullchain_20"]["sample_size"], 4),
            },
            {
                "section": "benchmark_v1_fullchain_no_council_20",
                "metric": "success_rate",
                "value": round(full_ab["no_council_fullchain_20"]["success_count"] / full_ab["no_council_fullchain_20"]["sample_size"], 4),
            },
            {
                "section": "benchmark_v1_fullchain_default_20",
                "metric": "worldview_median_s",
                "value": full_ab["default_fullchain_20"]["worldview"]["median"],
            },
            {
                "section": "benchmark_v1_fullchain_no_council_20",
                "metric": "worldview_median_s",
                "value": full_ab["no_council_fullchain_20"]["worldview"]["median"],
            },
        ]
    )

    final = dict(best)
    final["version"] = "repeat_conclusions_v2"
    final["stable_conclusions"] = updated_stable
    final["pending_conclusions"] = updated_pending
    final["executive_metrics"] = exec_rows
    final["source_files"]["fullchain_ab_summary"] = str(OUTPUT_DIR / "benchmark_v1_fullchain_ab_summary.json")

    out_json = OUTPUT_DIR / "dn_current_best_conclusions_v2.json"
    out_json.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(OUTPUT_DIR / "dn_current_best_executive_metrics_v2.csv", exec_rows)
    write_csv(OUTPUT_DIR / "dn_current_best_stable_conclusions_v2.csv", updated_stable)
    write_csv(OUTPUT_DIR / "dn_current_best_pending_conclusions_v2.csv", updated_pending)
    print(out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
