# -*- coding: utf-8 -*-
"""Aggregate visual-quality judge outputs into paper-ready summary tables."""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PKG_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = PKG_DIR / "results"

INSTRUCTION_PATH = RESULTS_DIR / "per_image_instruction_following_scores.jsonl"
AESTHETIC_PATH = RESULTS_DIR / "per_group_aesthetic_consistency_scores.jsonl"
SYSTEM_SUMMARY_PATH = RESULTS_DIR / "quality_summary_by_system.csv"
DIMENSION_SUMMARY_PATH = RESULTS_DIR / "quality_summary_by_dimension.csv"
FAILURE_CASES_PATH = RESULTS_DIR / "quality_failure_cases.md"

INSTRUCTION_DIMS = [
    "theme_alignment",
    "text_image_alignment",
    "style_following",
    "constraint_coverage",
    "forbidden_violation",
    "instruction_following_score",
]

AESTHETIC_DIMS = [
    "style_lighting_consistency",
    "subject_attribute_consistency",
    "scene_world_consistency",
    "composition_quality",
    "artifact_rate",
    "aesthetic_consistency_score",
]


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mean(values: Iterable[Any]) -> str:
    nums = [v for v in (to_float(x) for x in values) if v is not None]
    return f"{statistics.mean(nums):.3f}" if nums else ""


def rate(values: Iterable[Any], pred) -> str:
    nums = [v for v in (to_float(x) for x in values) if v is not None]
    return f"{sum(1 for v in nums if pred(v)) / len(nums):.3f}" if nums else ""


def average_duplicate_disagreement(rows: List[Dict[str, Any]], key_field: str, score_field: str) -> Tuple[str, int]:
    by_key: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        score = to_float(row.get(score_field))
        if score is not None:
            by_key[row.get(key_field, "")].append(score)
    disagreements = []
    adjudication_needed = 0
    for scores in by_key.values():
        if len(scores) < 2:
            continue
        spread = max(scores) - min(scores)
        disagreements.append(spread)
        if spread >= 2:
            adjudication_needed += 1
    if not disagreements:
        return "", 0
    return f"{statistics.mean(disagreements):.3f}", adjudication_needed


def aggregate_by_system(instruction: List[Dict[str, Any]], aesthetic: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    systems = sorted({r.get("system") for r in instruction + aesthetic if r.get("system")})
    rows = []
    for system in systems:
        inst = [r for r in instruction if r.get("system") == system]
        aest = [r for r in aesthetic if r.get("system") == system]
        inst_agree, inst_adjud = average_duplicate_disagreement(inst, "sample_id", "instruction_following_score")
        aest_agree, aest_adjud = average_duplicate_disagreement(aest, "group_key", "aesthetic_consistency_score")
        rows.append({
            "System": system,
            "N_images": len({r.get("sample_id") for r in inst}),
            "N_groups": len({r.get("group_key") for r in aest}),
            "Instruction Following": mean(r.get("instruction_following_score") for r in inst),
            "Aesthetic Consistency": mean(r.get("aesthetic_consistency_score") for r in aest),
            "Artifact Rate": rate((r.get("artifact_rate") for r in aest), lambda v: v <= 2),
            "Theme Violation Rate": rate((r.get("theme_alignment") for r in inst), lambda v: v <= 2),
            "Forbidden Violation Rate": rate((r.get("forbidden_violation") for r in inst), lambda v: v <= 2),
            "Instruction Judge Disagreement": inst_agree,
            "Aesthetic Judge Disagreement": aest_agree,
            "Adjudication Needed": inst_adjud + aest_adjud,
        })
    return rows


def aggregate_by_dimension(instruction: List[Dict[str, Any]], aesthetic: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    systems = sorted({r.get("system") for r in instruction + aesthetic if r.get("system")})
    for system in systems:
        inst = [r for r in instruction if r.get("system") == system]
        aest = [r for r in aesthetic if r.get("system") == system]
        for dim in INSTRUCTION_DIMS:
            rows.append({"System": system, "Metric Family": "Instruction Following", "Dimension": dim, "N": len(inst), "Mean": mean(r.get(dim) for r in inst)})
        for dim in AESTHETIC_DIMS:
            rows.append({"System": system, "Metric Family": "Aesthetic Consistency", "Dimension": dim, "N": len(aest), "Mean": mean(r.get(dim) for r in aest)})
    return rows


def write_failure_cases(instruction: List[Dict[str, Any]], aesthetic: List[Dict[str, Any]]) -> None:
    failures = []
    for row in instruction:
        score = to_float(row.get("instruction_following_score"))
        if score is not None and score <= 2:
            failures.append(("Instruction", row.get("system", ""), row.get("sample_id", ""), score, row.get("failure_tags", []), row.get("reason", "")))
    for row in aesthetic:
        score = to_float(row.get("aesthetic_consistency_score"))
        if score is not None and score <= 2:
            failures.append(("Aesthetic", row.get("system", ""), row.get("group_key", ""), score, row.get("failure_tags", []), row.get("reason", "")))
    failures.sort(key=lambda x: (x[0], x[1], x[3]))
    lines = [
        "# Quality Failure Cases",
        "",
        "Only real judge outputs are summarized here. Scores <= 2 are treated as clear failures.",
        "",
    ]
    if not failures:
        lines.append("No failure cases available yet, or no score <= 2 was observed.")
    for family, system, sample, score, tags, reason in failures:
        tag_text = ", ".join(tags) if isinstance(tags, list) else str(tags)
        lines.extend([
            f"## {family}: {system} / {sample}",
            "",
            f"- Score: {score:g}",
            f"- Failure tags: {tag_text}",
            f"- Reason: {reason}",
            "",
        ])
    FAILURE_CASES_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    instruction = read_jsonl(INSTRUCTION_PATH)
    aesthetic = read_jsonl(AESTHETIC_PATH)
    system_rows = aggregate_by_system(instruction, aesthetic)
    dimension_rows = aggregate_by_dimension(instruction, aesthetic)
    write_csv(SYSTEM_SUMMARY_PATH, system_rows, [
        "System",
        "N_images",
        "N_groups",
        "Instruction Following",
        "Aesthetic Consistency",
        "Artifact Rate",
        "Theme Violation Rate",
        "Forbidden Violation Rate",
        "Instruction Judge Disagreement",
        "Aesthetic Judge Disagreement",
        "Adjudication Needed",
    ])
    write_csv(DIMENSION_SUMMARY_PATH, dimension_rows, ["System", "Metric Family", "Dimension", "N", "Mean"])
    write_failure_cases(instruction, aesthetic)
    print(json.dumps({
        "instruction_rows": len(instruction),
        "aesthetic_rows": len(aesthetic),
        "system_summary": str(SYSTEM_SUMMARY_PATH),
        "dimension_summary": str(DIMENSION_SUMMARY_PATH),
        "failure_cases": str(FAILURE_CASES_PATH),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
