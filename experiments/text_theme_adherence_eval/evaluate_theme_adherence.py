#!/usr/bin/env python
"""Offline text theme-adherence evaluation with BAAI/bge-m3.

Pipeline:
1) Download model to local path (default: D:\\models\\bge-m3)
2) Read one theme CSV and multiple text CSV files
3) Compute sim_pos / sim_neg_max / margin / pass
4) Export per-dataset results + cross-dataset summaries
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer

MODEL_ID = "BAAI/bge-m3"
DEFAULT_MODEL_DIR = Path(r"D:\models\bge-m3")
DEFAULT_OUTPUT_DIR = Path(r"D:\embedding_eval_outputs")
CSV_ENCODINGS = ["utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1"]


@dataclass
class EvalConfig:
    pos_threshold: float = 0.35
    margin_threshold: float = 0.08
    batch_size: int = 64
    top_n: int = 20


def set_reproducibility(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
    logging.info("Logging to %s", log_path)


def read_csv_robust(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in CSV_ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, on_bad_lines="skip")
            logging.info("Loaded CSV %s (encoding=%s, rows=%d)", path, enc, len(df))
            return df
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            continue
    raise RuntimeError(f"Failed to read CSV: {path}. Last error: {last_error}")


def normalize_text_col(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def clean_theme_df(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    required = {"id", "theme"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{source} missing columns: {sorted(missing)}")

    work = df[["id", "theme"]].copy()
    work["id"] = normalize_text_col(work["id"])
    work["theme"] = normalize_text_col(work["theme"])

    missing_id = (work["id"] == "").sum()
    missing_theme = (work["theme"] == "").sum()
    if missing_id:
        logging.warning("%s has %d rows with empty id; dropped", source, int(missing_id))
    if missing_theme:
        logging.warning("%s has %d rows with empty theme; dropped", source, int(missing_theme))

    work = work[(work["id"] != "") & (work["theme"] != "")]

    dup_cnt = work.duplicated(subset=["id"], keep="first").sum()
    if dup_cnt:
        logging.warning("%s has %d duplicated ids; keeping first occurrence", source, int(dup_cnt))
        work = work.drop_duplicates(subset=["id"], keep="first")

    return work.reset_index(drop=True)


def clean_text_df(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    required = {"id", "text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{source} missing columns: {sorted(missing)}")

    work = df[["id", "text"]].copy()
    work["id"] = normalize_text_col(work["id"])
    work["text"] = normalize_text_col(work["text"])

    missing_id = (work["id"] == "").sum()
    missing_text = (work["text"] == "").sum()
    if missing_id:
        logging.warning("%s has %d rows with empty id; dropped", source, int(missing_id))
    if missing_text:
        logging.warning("%s has %d rows with empty text; dropped", source, int(missing_text))

    work = work[(work["id"] != "") & (work["text"] != "")]

    dup_cnt = work.duplicated(subset=["id"], keep="first").sum()
    if dup_cnt:
        logging.warning("%s has %d duplicated ids; keeping first occurrence", source, int(dup_cnt))
        work = work.drop_duplicates(subset=["id"], keep="first")

    return work.reset_index(drop=True)


def ensure_model_downloaded(model_dir: Path, model_id: str = MODEL_ID) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    required_files = [
        "config.json",
        "modules.json",
        "config_sentence_transformers.json",
        "sentence_bert_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "sentencepiece.bpe.model",
        "special_tokens_map.json",
        "1_Pooling/config.json",
    ]
    has_weight = (model_dir / "pytorch_model.bin").exists() or (model_dir / "model.safetensors").exists()
    if all((model_dir / rel).exists() for rel in required_files) and has_weight:
        logging.info("Model appears available at %s", model_dir)
        return

    logging.info("Downloading model %s to %s", model_id, model_dir)
    # Download only files required by SentenceTransformer runtime to reduce failures.
    allow_patterns = [
        "config.json",
        "modules.json",
        "config_sentence_transformers.json",
        "sentence_bert_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "sentencepiece.bpe.model",
        "special_tokens_map.json",
        "1_Pooling/config.json",
        "pytorch_model.bin",
        "model.safetensors",
        "colbert_linear.pt",
        "sparse_linear.pt",
    ]
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            snapshot_download(
                repo_id=model_id,
                local_dir=str(model_dir),
                allow_patterns=allow_patterns,
                max_workers=2,
            )
            has_weight = (model_dir / "pytorch_model.bin").exists() or (model_dir / "model.safetensors").exists()
            if all((model_dir / rel).exists() for rel in required_files) and has_weight:
                logging.info("Model downloaded successfully")
                return
            raise RuntimeError("Model files are incomplete after download")
        except Exception as exc:  # pylint: disable=broad-except
            last_error = exc
            logging.warning("Model download attempt %d/5 failed: %s", attempt, exc)
    raise RuntimeError(f"Model download failed after retries: {last_error}")


def choose_device(force_cpu: bool = False) -> str:
    if force_cpu:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_encoder(model_dir: Path, device: str) -> SentenceTransformer:
    logging.info("Loading SentenceTransformer from %s (device=%s)", model_dir, device)
    model = SentenceTransformer(str(model_dir), device=device, trust_remote_code=True)
    return model


def encode_texts(model: SentenceTransformer, texts: Sequence[str], batch_size: int) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings


def unique_with_inverse(values: Sequence[str]) -> Tuple[List[str], np.ndarray]:
    unique_vals: List[str] = []
    index_map: dict[str, int] = {}
    inverse = np.empty(len(values), dtype=np.int64)
    for i, val in enumerate(values):
        if val not in index_map:
            index_map[val] = len(unique_vals)
            unique_vals.append(val)
        inverse[i] = index_map[val]
    return unique_vals, inverse


def embed_deduplicated(model: SentenceTransformer, texts: Sequence[str], batch_size: int) -> np.ndarray:
    unique_vals, inverse = unique_with_inverse(texts)
    unique_emb = encode_texts(model, unique_vals, batch_size=batch_size)
    return unique_emb[inverse]


def parse_negative_themes(neg_themes: Sequence[str], neg_file: Path | None) -> List[str]:
    vals: List[str] = []
    if neg_file is not None:
        lines = neg_file.read_text(encoding="utf-8").splitlines()
        vals.extend([line.strip() for line in lines if line.strip()])
    vals.extend([t.strip() for t in neg_themes if t.strip()])

    # unique preserve order
    dedup: List[str] = []
    seen: set[str] = set()
    for t in vals:
        if t not in seen:
            seen.add(t)
            dedup.append(t)

    if not (3 <= len(dedup) <= 10):
        raise ValueError(f"Negative theme count must be in [3,10], got {len(dedup)}")
    return dedup


def cosine_pos(theme_emb: np.ndarray, text_emb: np.ndarray) -> np.ndarray:
    return np.einsum("ij,ij->i", theme_emb, text_emb)


def cosine_neg_max(text_emb: np.ndarray, neg_emb: np.ndarray) -> np.ndarray:
    return text_emb @ neg_emb.T


def evaluate_single_dataset(
    model: SentenceTransformer,
    theme_df: pd.DataFrame,
    text_csv: Path,
    neg_themes: Sequence[str],
    config: EvalConfig,
    output_dir: Path,
) -> Tuple[pd.DataFrame, dict]:
    raw_text_df = read_csv_robust(text_csv)
    text_df = clean_text_df(raw_text_df, text_csv)

    merged = theme_df.merge(text_df, on="id", how="inner")
    if merged.empty:
        raise ValueError(f"No overlapping ids between theme CSV and {text_csv}")

    dropped_theme_only = len(theme_df) - merged["id"].nunique()
    dropped_text_only = len(text_df) - merged["id"].nunique()
    if dropped_theme_only > 0:
        logging.warning("%s: %d theme ids not found in text dataset", text_csv.name, dropped_theme_only)
    if dropped_text_only > 0:
        logging.warning("%s: %d text ids not found in theme dataset", text_csv.name, dropped_text_only)

    theme_emb = embed_deduplicated(model, merged["theme"].tolist(), batch_size=config.batch_size)
    text_emb = embed_deduplicated(model, merged["text"].tolist(), batch_size=config.batch_size)
    neg_emb = encode_texts(model, list(neg_themes), batch_size=config.batch_size)

    sim_pos = cosine_pos(theme_emb, text_emb)
    neg_scores = cosine_neg_max(text_emb, neg_emb)
    sim_neg_max = neg_scores.max(axis=1)
    margin = sim_pos - sim_neg_max
    passed = (sim_pos >= config.pos_threshold) & (margin >= config.margin_threshold)

    result = merged.copy()
    result["sim_pos"] = sim_pos
    result["sim_neg_max"] = sim_neg_max
    result["margin"] = margin
    result["pass"] = passed

    dataset_name = text_csv.stem
    result_path = output_dir / f"{dataset_name}_results.csv"
    result.to_csv(result_path, index=False, encoding="utf-8-sig")

    worst_path = output_dir / f"{dataset_name}_worst_top{config.top_n}.csv"
    result.sort_values(by="margin", ascending=True).head(config.top_n).to_csv(
        worst_path, index=False, encoding="utf-8-sig"
    )

    summary = {
        "dataset_name": dataset_name,
        "n_samples": int(len(result)),
        "mean_sim_pos": float(result["sim_pos"].mean()),
        "mean_margin": float(result["margin"].mean()),
        "pass_rate": float(result["pass"].mean()),
        "result_csv": str(result_path),
        "worst_csv": str(worst_path),
    }

    logging.info(
        "[%s] n=%d | mean_sim_pos=%.4f | mean_margin=%.4f | pass_rate=%.2f%%",
        dataset_name,
        summary["n_samples"],
        summary["mean_sim_pos"],
        summary["mean_margin"],
        summary["pass_rate"] * 100,
    )

    return result, summary


def evaluate_all(
    theme_csv: Path,
    text_csvs: Sequence[Path],
    neg_themes: Sequence[str],
    model_dir: Path,
    output_dir: Path,
    config: EvalConfig,
    seed: int,
    force_cpu: bool,
) -> None:
    setup_logging(output_dir)
    set_reproducibility(seed)

    logging.info("Running with model=%s local_model_dir=%s", MODEL_ID, model_dir)
    logging.info("Thresholds: sim_pos>=%.3f, margin>=%.3f", config.pos_threshold, config.margin_threshold)

    raw_theme_df = read_csv_robust(theme_csv)
    theme_df = clean_theme_df(raw_theme_df, theme_csv)
    if theme_df.empty:
        raise ValueError("Theme dataset is empty after cleaning")

    ensure_model_downloaded(model_dir)
    device = choose_device(force_cpu=force_cpu)
    model = load_encoder(model_dir=model_dir, device=device)

    summaries: List[dict] = []
    all_results: List[pd.DataFrame] = []

    for text_csv in text_csvs:
        result_df, summary = evaluate_single_dataset(
            model=model,
            theme_df=theme_df,
            text_csv=text_csv,
            neg_themes=neg_themes,
            config=config,
            output_dir=output_dir,
        )
        result_df = result_df.copy()
        result_df["dataset_name"] = summary["dataset_name"]
        all_results.append(result_df)
        summaries.append(summary)

    summary_df = pd.DataFrame(summaries)
    summary_path = output_dir / "summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    compare_margin = summary_df.sort_values(by=["mean_margin", "pass_rate"], ascending=[False, False])
    compare_margin_path = output_dir / "comparison_by_margin_then_pass_rate.csv"
    compare_margin.to_csv(compare_margin_path, index=False, encoding="utf-8-sig")

    compare_pass = summary_df.sort_values(by=["pass_rate", "mean_margin"], ascending=[False, False])
    compare_pass_path = output_dir / "comparison_by_pass_rate_then_margin.csv"
    compare_pass.to_csv(compare_pass_path, index=False, encoding="utf-8-sig")

    global_worst = pd.concat(all_results, ignore_index=True).sort_values(by="margin", ascending=True).head(config.top_n)
    global_worst_path = output_dir / f"global_worst_top{config.top_n}.csv"
    global_worst.to_csv(global_worst_path, index=False, encoding="utf-8-sig")

    versions = {
        "python": sys.version,
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "torch": torch.__version__,
        "sentence_transformers": __import__("sentence_transformers").__version__,
    }
    (output_dir / "versions.json").write_text(json.dumps(versions, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== Evaluation Report =====")
    for row in summary_df.to_dict(orient="records"):
        print(
            f"{row['dataset_name']}: n={row['n_samples']}, "
            f"mean_sim_pos={row['mean_sim_pos']:.4f}, "
            f"mean_margin={row['mean_margin']:.4f}, "
            f"pass_rate={row['pass_rate'] * 100:.2f}%"
        )

    best = compare_margin.iloc[0]
    worst = compare_margin.iloc[-1]
    print("\nBest dataset (margin/pass_rate):", best["dataset_name"])
    print("Worst dataset (margin/pass_rate):", worst["dataset_name"])
    print("\nOutputs:")
    print(f"- Summary: {summary_path}")
    print(f"- Compare (margin->pass_rate): {compare_margin_path}")
    print(f"- Compare (pass_rate->margin): {compare_pass_path}")
    print(f"- Global worst TopN: {global_worst_path}")


def collect_text_csvs(explicit_csvs: Sequence[str], csv_glob: str | None) -> List[Path]:
    paths: List[Path] = [Path(p) for p in explicit_csvs]
    if csv_glob:
        paths.extend(sorted(Path().glob(csv_glob)))
    dedup = []
    seen = set()
    for p in paths:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            dedup.append(rp)
    if not dedup:
        raise ValueError("No text CSV files were provided")
    for p in dedup:
        if not p.exists():
            raise FileNotFoundError(f"Text CSV not found: {p}")
    return dedup


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline theme adherence evaluation with BAAI/bge-m3")
    sub = parser.add_subparsers(dest="command", required=True)

    p_download = sub.add_parser("download", help="Download BAAI/bge-m3 to local directory")
    p_download.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR), help="Local model directory")

    p_eval = sub.add_parser("evaluate", help="Run evaluation")
    p_eval.add_argument("--theme-csv", required=True, help="Theme CSV path with columns: id,theme")
    p_eval.add_argument(
        "--text-csv",
        action="append",
        default=[],
        help="Text CSV path with columns: id,text. Repeat for multiple files.",
    )
    p_eval.add_argument("--text-csv-glob", default=None, help="Optional glob for text CSVs, e.g. data/texts/*.csv")
    p_eval.add_argument(
        "--neg-theme",
        action="append",
        default=[],
        help="Negative theme. Repeat to add more.",
    )
    p_eval.add_argument("--neg-theme-file", default=None, help="Optional txt file with one negative theme per line")
    p_eval.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR), help="Local model directory")
    p_eval.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory")
    p_eval.add_argument("--batch-size", type=int, default=64)
    p_eval.add_argument("--pos-threshold", type=float, default=0.35)
    p_eval.add_argument("--margin-threshold", type=float, default=0.08)
    p_eval.add_argument("--top-n", type=int, default=20)
    p_eval.add_argument("--seed", type=int, default=42)
    p_eval.add_argument("--force-cpu", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "download":
        out = Path(args.model_dir).resolve()
        setup_logging(DEFAULT_OUTPUT_DIR)
        ensure_model_downloaded(out)
        print(f"Model ready at: {out}")
        return

    if args.command == "evaluate":
        theme_csv = Path(args.theme_csv).resolve()
        if not theme_csv.exists():
            raise FileNotFoundError(f"Theme CSV not found: {theme_csv}")

        text_csvs = collect_text_csvs(args.text_csv, args.text_csv_glob)
        neg_file = Path(args.neg_theme_file).resolve() if args.neg_theme_file else None
        if neg_file and not neg_file.exists():
            raise FileNotFoundError(f"Negative-theme file not found: {neg_file}")

        neg_themes = parse_negative_themes(args.neg_theme, neg_file)
        output_dir = Path(args.output_dir).resolve()

        config = EvalConfig(
            pos_threshold=args.pos_threshold,
            margin_threshold=args.margin_threshold,
            batch_size=args.batch_size,
            top_n=args.top_n,
        )

        evaluate_all(
            theme_csv=theme_csv,
            text_csvs=text_csvs,
            neg_themes=neg_themes,
            model_dir=Path(args.model_dir).resolve(),
            output_dir=output_dir,
            config=config,
            seed=args.seed,
            force_cpu=args.force_cpu,
        )
        return

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
