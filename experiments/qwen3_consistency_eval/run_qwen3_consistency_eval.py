from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from adapters import EvalSample, load_all_samples, load_benchmarks
from scoring import QwenScorer, cosine, minmax, safe_mean, safe_min


SCORES_FIELDS = [
    "run_id",
    "system_name",
    "benchmark_id",
    "theme_id",
    "theme",
    "source_file",
    "raw_text_chars",
    "overall_embedding_score",
    "must_embedding_mean",
    "must_embedding_min",
    "must_reranker_mean",
    "must_reranker_min",
    "forbidden_risk_mean",
    "forbidden_risk_max",
    "top_forbidden_issue",
    "turn_drift_mean",
    "turn_drift_min",
    "qwen3_consistency_score",
    "status",
    "error",
]


def repo_root() -> Path:
    return SCRIPT_DIR.parents[1]


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def rel_to_root(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def unique_preserve_order(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    ordered: list[Any] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def resolve_spec(sample: EvalSample, specs: dict[str, Any]) -> Any:
    spec = specs.get(sample.benchmark_id)
    if spec is None and sample.theme:
        spec = next((s for s in specs.values() if s.theme == sample.theme or s.theme_id == sample.theme_id), None)
    return spec


def warm_sample_cache(samples: list[EvalSample], specs: dict[str, Any], scorer: QwenScorer) -> None:
    text_values: list[str] = []
    rerank_pairs: list[tuple[str, str]] = []

    for sample in samples:
        if sample.status != "ok":
            continue
        spec = resolve_spec(sample, specs)
        if spec is None:
            continue

        card = spec.card()
        text_values.extend([card, sample.generated_text])

        must_texts = [x for x in spec.must_have_constraints if x]
        forbidden_texts = [x for x in spec.forbidden_issues if x]
        text_values.extend(must_texts)

        turns = [t for t in sample.turns if isinstance(t, str) and len(t.strip()) >= 30]
        text_values.extend(turns)

        rerank_pairs.extend(
            (f"Does the generated Chinese interactive narrative satisfy this requirement: {req}", sample.generated_text)
            for req in must_texts
        )
        rerank_pairs.extend(
            (f"Does the generated Chinese interactive narrative contain this forbidden issue: {issue}", sample.generated_text)
            for issue in forbidden_texts
        )

    unique_texts = unique_preserve_order([text for text in text_values if isinstance(text, str) and text.strip()])
    unique_pairs = unique_preserve_order([
        pair for pair in rerank_pairs if isinstance(pair[0], str) and pair[0].strip() and isinstance(pair[1], str) and pair[1].strip()
    ])

    embed_chunk = max(2, scorer.embedding_batch_size * 2)
    rerank_chunk = max(2, scorer.reranker_batch_size * 4)

    if unique_texts:
        print(f"[info] warming embedding cache for {len(unique_texts)} unique texts")
        for start in range(0, len(unique_texts), embed_chunk):
            end = min(start + embed_chunk, len(unique_texts))
            scorer.encode(unique_texts[start:end])
            print(f"[info] embedding cache {end}/{len(unique_texts)}")

    if unique_pairs:
        print(f"[info] warming reranker cache for {len(unique_pairs)} unique pairs")
        for start in range(0, len(unique_pairs), rerank_chunk):
            end = min(start + rerank_chunk, len(unique_pairs))
            scorer.rerank(unique_pairs[start:end])
            print(f"[info] reranker cache {end}/{len(unique_pairs)}")


def score_sample(sample: EvalSample, spec: Any, scorer: QwenScorer) -> dict[str, Any]:
    base = {
        "run_id": sample.run_id,
        "system_name": sample.system_name,
        "benchmark_id": sample.benchmark_id,
        "theme_id": sample.theme_id,
        "theme": sample.theme,
        "source_file": sample.source_file,
        "raw_text_chars": len(sample.generated_text or ""),
        "status": sample.status,
        "error": sample.error,
    }
    if sample.status != "ok":
        return base
    if spec is None:
        base.update(status="missing_spec", error="No benchmark spec matched sample.")
        return base

    try:
        card = spec.card()
        emb = scorer.encode([card, sample.generated_text])
        overall = cosine(emb[0], emb[1])

        must_texts = [x for x in spec.must_have_constraints if x]
        forbidden_texts = [x for x in spec.forbidden_issues if x]

        must_embedding_scores: list[float] = []
        if must_texts:
            must_emb = scorer.encode(must_texts + [sample.generated_text])
            doc_vec = must_emb[-1]
            must_embedding_scores = [cosine(vec, doc_vec) for vec in must_emb[:-1]]

        must_pairs = [
            (f"Does the generated Chinese interactive narrative satisfy this requirement: {req}", sample.generated_text)
            for req in must_texts
        ]
        must_rerank_scores = scorer.rerank(must_pairs) if must_pairs else []

        forbidden_pairs = [
            (f"Does the generated Chinese interactive narrative contain this forbidden issue: {issue}", sample.generated_text)
            for issue in forbidden_texts
        ]
        forbidden_scores = scorer.rerank(forbidden_pairs) if forbidden_pairs else []
        top_forbidden_issue = ""
        if forbidden_scores and forbidden_texts:
            top_i = int(np.argmax(np.asarray(forbidden_scores)))
            top_forbidden_issue = forbidden_texts[top_i]

        turn_scores: list[float] = []
        turns = [t for t in sample.turns if isinstance(t, str) and len(t.strip()) >= 30]
        if len(turns) >= 2:
            turn_emb = scorer.encode(turns)
            for i in range(len(turn_emb) - 1):
                turn_scores.append(cosine(turn_emb[i], turn_emb[i + 1]))

        base.update({
            "overall_embedding_score": overall,
            "must_embedding_mean": safe_mean(must_embedding_scores),
            "must_embedding_min": safe_min(must_embedding_scores),
            "must_reranker_mean": safe_mean(must_rerank_scores),
            "must_reranker_min": safe_min(must_rerank_scores),
            "forbidden_risk_mean": safe_mean(forbidden_scores),
            "forbidden_risk_max": max(forbidden_scores) if forbidden_scores else float("nan"),
            "top_forbidden_issue": top_forbidden_issue,
            "turn_drift_mean": safe_mean(turn_scores),
            "turn_drift_min": safe_min(turn_scores),
            "qwen3_consistency_score": float("nan"),
            "status": "ok",
            "error": "",
        })
        return base
    except Exception as exc:
        base.update(status="error", error=f"{type(exc).__name__}: {exc}")
        return base


def add_composite_scores(rows: list[dict[str, Any]]) -> None:
    valid = [r for r in rows if r.get("status") == "ok"]
    overall_norm = minmax([float(r.get("overall_embedding_score", float("nan"))) for r in valid])
    must_emb_norm = minmax([float(r.get("must_embedding_mean", float("nan"))) for r in valid])
    turn_norm = minmax([float(r.get("turn_drift_mean", float("nan"))) for r in valid])
    for row, overall, must_emb, turn in zip(valid, overall_norm, must_emb_norm, turn_norm):
        must_rerank = float(row.get("must_reranker_mean", float("nan")))
        forbidden = float(row.get("forbidden_risk_max", float("nan")))
        if math.isnan(turn):
            score = 0.30 * overall + 0.35 * must_rerank + 0.20 * must_emb + 0.15 * (1 - forbidden)
        else:
            score = 0.25 * overall + 0.35 * must_rerank + 0.20 * must_emb + 0.15 * (1 - forbidden) + 0.05 * turn
        row["qwen3_consistency_score"] = score


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    systems = sorted({r.get("system_name", "") for r in rows if r.get("system_name")})
    dn_by_key: dict[tuple[str, str], float] = {}
    for r in rows:
        if r.get("status") == "ok" and str(r.get("system_name", "")).startswith("dn_"):
            key = (str(r.get("benchmark_id", "")), str(r.get("theme_id", "")))
            score = float(r.get("qwen3_consistency_score", float("nan")))
            if not math.isnan(score):
                dn_by_key.setdefault(key, score)

    summary: list[dict[str, Any]] = []
    for system in systems:
        rs = [r for r in rows if r.get("system_name") == system]
        valid = [r for r in rs if r.get("status") == "ok" and not math.isnan(float(r.get("qwen3_consistency_score", float("nan"))))]
        scores = [float(r["qwen3_consistency_score"]) for r in valid]
        deltas: list[float] = []
        wins = 0
        pairs = 0
        for r in valid:
            key = (str(r.get("benchmark_id", "")), str(r.get("theme_id", "")))
            if key in dn_by_key and not str(system).startswith("dn_"):
                delta = float(r["qwen3_consistency_score"]) - dn_by_key[key]
                deltas.append(delta)
                wins += 1 if delta > 0 else 0
                pairs += 1
        summary.append({
            "system_name": system,
            "n": len(rs),
            "valid_n": len(valid),
            "missing_raw_text_n": sum(1 for r in rs if r.get("status") == "missing_raw_text"),
            "mean_score": float(np.mean(scores)) if scores else float("nan"),
            "median_score": float(np.median(scores)) if scores else float("nan"),
            "std_score": float(np.std(scores)) if scores else float("nan"),
            "mean_overall_embedding": safe_mean([float(r.get("overall_embedding_score", float("nan"))) for r in valid]),
            "mean_must_reranker": safe_mean([float(r.get("must_reranker_mean", float("nan"))) for r in valid]),
            "mean_forbidden_risk": safe_mean([float(r.get("forbidden_risk_max", float("nan"))) for r in valid]),
            "win_rate_vs_dn": (wins / pairs) if pairs else float("nan"),
            "paired_delta_vs_dn": float(np.mean(deltas)) if deltas else float("nan"),
        })
    return summary


def maybe_write_excel(out_dir: Path, scores: list[dict[str, Any]], summary: list[dict[str, Any]], failed: list[dict[str, Any]]) -> None:
    try:
        import pandas as pd

        with pd.ExcelWriter(out_dir / "qwen3_consistency_report.xlsx") as writer:
            pd.DataFrame(scores).to_excel(writer, sheet_name="scores_long", index=False)
            pd.DataFrame(summary).to_excel(writer, sheet_name="system_summary", index=False)
            pd.DataFrame(failed).to_excel(writer, sheet_name="failed_samples", index=False)
    except Exception as exc:
        print(f"[warn] Excel report skipped: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(SCRIPT_DIR / "config.yaml"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default=None, choices=["auto", "cuda", "cpu"])
    args = parser.parse_args()

    root = repo_root()
    config = load_config(Path(args.config))
    if args.device:
        config["model"]["device"] = args.device
    out_dir = rel_to_root(root, config["outputs"]["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    hf_endpoint = config["model"].get("hf_endpoint")
    if hf_endpoint:
        os.environ.setdefault("HF_ENDPOINT", str(hf_endpoint))
        os.environ.setdefault("HUGGINGFACE_HUB_ENDPOINT", str(hf_endpoint))
    if config["model"].get("cache_dir"):
        os.environ.setdefault("HF_HOME", str(config["model"]["cache_dir"]))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(Path(config["model"]["cache_dir"]) / "transformers"))

    specs = load_benchmarks(rel_to_root(root, config["inputs"]["benchmark_csv"]))
    samples, summary_missing = load_all_samples(root, config, specs)
    min_chars = int(config.get("scoring", {}).get("min_text_chars", 80))
    max_chars = int(config.get("scoring", {}).get("max_text_chars", 12000))
    for sample in samples:
        if len(sample.generated_text) < min_chars:
            sample.status = "missing_raw_text"
            sample.error = sample.error or f"Generated text shorter than {min_chars} chars."
        sample.generated_text = sample.generated_text[:max_chars]

    samples.sort(key=lambda s: (s.system_name, s.benchmark_id, s.theme_id, s.run_id))
    if args.limit:
        ok = [s for s in samples if s.status == "ok"][: args.limit]
        missing = [s for s in samples if s.status != "ok"][: max(0, args.limit - len(ok))]
        samples = ok + missing

    write_jsonl(out_dir / "samples_normalized.jsonl", [s.to_json() for s in samples])

    scorer = QwenScorer(config, out_dir, config["model"].get("device", "auto"))
    print(f"[info] device={scorer.device} samples={len(samples)} specs={len(specs)}")
    warm_sample_cache(samples, specs, scorer)
    scorer.cache.save()

    rows: list[dict[str, Any]] = []
    for idx, sample in enumerate(samples, 1):
        spec = resolve_spec(sample, specs)
        row = score_sample(sample, spec, scorer)
        rows.append(row)
        if idx % 10 == 0 or idx == len(samples):
            print(f"[info] scored {idx}/{len(samples)}")

    add_composite_scores(rows)
    scorer.cache.save()
    failed = [r for r in rows if r.get("status") != "ok"]
    failed.extend(summary_missing)
    summary = summarize(rows)

    write_csv(out_dir / "scores_long.csv", rows, SCORES_FIELDS)
    write_csv(out_dir / "system_summary.csv", summary, [
        "system_name", "n", "valid_n", "missing_raw_text_n", "mean_score", "median_score",
        "std_score", "mean_overall_embedding", "mean_must_reranker", "mean_forbidden_risk",
        "win_rate_vs_dn", "paired_delta_vs_dn",
    ])
    write_jsonl(out_dir / "failed_samples.jsonl", failed)
    maybe_write_excel(out_dir, rows, summary, failed)
    print(f"[done] wrote outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
