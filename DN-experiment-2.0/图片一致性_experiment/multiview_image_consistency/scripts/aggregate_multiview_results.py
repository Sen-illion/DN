from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate multi-view image consistency judge outputs from JSONL."
    )
    parser.add_argument(
        "--input-jsonl",
        type=Path,
        required=True,
        help="Judge output JSONL. One JSON object per line.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Experiment config JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("DN-experiment-2.0/experiments/multiview_image_consistency/results"),
        help="Directory for summary artifacts.",
    )
    return parser.parse_args()


def read_json(path: Path) -> Dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def stddev(values: List[float]) -> float:
    if len(values) <= 1:
        return 0.0
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def normalize_weights(dimensions: List[Dict]) -> Dict[str, float]:
    raw = {d["name"]: float(d.get("weight", 0.0)) for d in dimensions}
    total = sum(raw.values())
    if total <= 0:
        n = len(raw)
        if n == 0:
            return {}
        return {k: 1.0 / n for k in raw}
    return {k: v / total for k, v in raw.items()}


def compute_weighted_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    if not scores:
        return 0.0
    return sum(float(scores.get(k, 0.0)) * weights.get(k, 0.0) for k in weights)


def aggregate(rows: List[Dict], config: Dict) -> Dict:
    dims = [d["name"] for d in config.get("dimensions", [])]
    weights = normalize_weights(config.get("dimensions", []))

    dim_scores: Dict[str, List[float]] = {d: [] for d in dims}
    overall_scores: List[float] = []
    by_sample_by_model: Dict[str, Dict[str, float]] = defaultdict(dict)
    by_model_scores: Dict[str, List[float]] = defaultdict(list)

    for row in rows:
        sample_id = str(row.get("sample_id", ""))
        model = str(row.get("judge_model", "unknown"))
        d_scores = row.get("dimension_scores", {}) or {}
        local_scores: Dict[str, float] = {}
        for d in dims:
            if d in d_scores:
                v = float(d_scores[d])
                dim_scores[d].append(v)
                local_scores[d] = v

        if local_scores:
            weighted = compute_weighted_score(local_scores, weights)
        else:
            weighted = float(row.get("overall_score", 0.0))

        overall_scores.append(weighted)
        by_model_scores[model].append(weighted)
        if sample_id:
            by_sample_by_model[sample_id][model] = weighted

    disagreement_values: List[float] = []
    for model_map in by_sample_by_model.values():
        disagreement_values.append(stddev(list(model_map.values())))

    dim_summary = {
        d: {
            "mean": round(mean(vals), 4) if vals else None,
            "count": len(vals),
        }
        for d, vals in dim_scores.items()
    }

    model_summary = {
        m: {
            "mean_overall": round(mean(vals), 4) if vals else None,
            "count": len(vals),
        }
        for m, vals in sorted(by_model_scores.items())
    }

    return {
        "total_rows": len(rows),
        "unique_samples": len(by_sample_by_model),
        "unique_models": len(by_model_scores),
        "overall_score_mean": round(mean(overall_scores), 4) if overall_scores else None,
        "judge_disagreement_mean": round(mean(disagreement_values), 4)
        if disagreement_values
        else None,
        "dimension_summary": dim_summary,
        "model_summary": model_summary,
        "weights": weights,
    }


def check_thresholds(summary: Dict, config: Dict) -> Dict[str, bool]:
    th = config.get("thresholds", {})
    min_overall = float(th.get("min_overall_score_mean", 0.0))
    max_disagree = float(th.get("max_judge_disagreement_mean", 999.0))
    overall_ok = (summary.get("overall_score_mean") or 0.0) >= min_overall
    disagree_value = summary.get("judge_disagreement_mean")
    if disagree_value is None:
        disagreement_ok = False
    else:
        disagreement_ok = float(disagree_value) <= max_disagree
    return {
        "overall_ok": overall_ok,
        "disagreement_ok": disagreement_ok,
        "pass": overall_ok and disagreement_ok,
    }


def build_conclusion(summary: Dict, checks: Dict[str, bool]) -> str:
    if summary.get("total_rows", 0) == 0:
        return "No valid judge rows were found. Cannot conclude yet."
    if checks["pass"]:
        return "Multi-view consistency looks acceptable under current thresholds."
    if not checks["overall_ok"] and not checks["disagreement_ok"]:
        return "Scores are weak and judge disagreement is high; prompt or data quality likely unstable."
    if not checks["overall_ok"]:
        return "Scores are below target while judges are relatively aligned; generation quality is likely the bottleneck."
    return "Average scores are acceptable but judge disagreement is high; rubric or judge calibration needs refinement."


def write_markdown(path: Path, payload: Dict, checks: Dict, conclusion: str) -> None:
    lines = [
        "# Multi-View Image Consistency Report",
        "",
        f"- generated_at_utc: {datetime.now(timezone.utc).isoformat()}",
        f"- total_rows: {payload.get('total_rows')}",
        f"- unique_samples: {payload.get('unique_samples')}",
        f"- unique_models: {payload.get('unique_models')}",
        f"- overall_score_mean: {payload.get('overall_score_mean')}",
        f"- judge_disagreement_mean: {payload.get('judge_disagreement_mean')}",
        "",
        "## Threshold Checks",
        f"- overall_ok: {checks.get('overall_ok')}",
        f"- disagreement_ok: {checks.get('disagreement_ok')}",
        f"- pass: {checks.get('pass')}",
        "",
        "## Dimension Means",
    ]
    for name, stats in payload.get("dimension_summary", {}).items():
        lines.append(f"- {name}: mean={stats.get('mean')} count={stats.get('count')}")

    lines.extend(
        [
            "",
            "## Strongest Takeaway",
            f"- {conclusion}",
            "",
            "## Biggest Remaining Uncertainty",
            "- Are disagreements caused by judge model bias, rubric wording, or ambiguous image samples?",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    config = read_json(args.config)
    rows = read_jsonl(args.input_jsonl)
    summary = aggregate(rows, config)
    checks = check_thresholds(summary, config)
    conclusion = build_conclusion(summary, checks)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    summary_path = out_dir / f"multiview_summary_{ts}.json"
    latest_summary = out_dir / "latest_multiview_summary.json"
    report_path = out_dir / f"multiview_report_{ts}.md"
    latest_report = out_dir / "latest_multiview_report.md"

    summary_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_jsonl": str(args.input_jsonl),
        "config": str(args.config),
        "summary": summary,
        "checks": checks,
        "conclusion": conclusion,
    }
    summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_summary.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report_path, summary, checks, conclusion)
    write_markdown(latest_report, summary, checks, conclusion)

    print(json.dumps(summary_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
