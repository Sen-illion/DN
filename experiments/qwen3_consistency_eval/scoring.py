from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


EMBED_INSTRUCTION = (
    "Evaluate whether a generated Chinese interactive narrative matches the "
    "given benchmark specification, including theme, genre, tone, required "
    "constraints, and forbidden issues."
)


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def safe_mean(values: list[float]) -> float:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return float(np.mean(vals)) if vals else float("nan")


def safe_min(values: list[float]) -> float:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return float(np.min(vals)) if vals else float("nan")


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return float("nan")
    return float(np.dot(a, b) / denom)


class JsonCache:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, Any] = {}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    def key(self, prefix: str, *parts: str) -> str:
        h = hashlib.sha256()
        h.update(prefix.encode("utf-8"))
        for part in parts:
            h.update(b"\0")
            h.update(str(part).encode("utf-8"))
        return h.hexdigest()

    def get(self, key: str) -> Any:
        return self.data.get(key)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")


class QwenScorer:
    def __init__(self, config: dict[str, Any], out_dir: Path, device: str):
        from sentence_transformers import CrossEncoder, SentenceTransformer
        import torch

        model_cfg = config["model"]
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device
        self.embedding_batch_size = int(model_cfg.get("embedding_batch_size", 16))
        self.reranker_batch_size = int(model_cfg.get("reranker_batch_size", 4))
        self.max_length = int(model_cfg.get("max_length", 8192))
        cache_dir = model_cfg.get("cache_dir") or None
        self.embedder = SentenceTransformer(
            model_cfg["embedding_model"],
            device=device,
            cache_folder=cache_dir,
            trust_remote_code=True,
        )
        self.reranker = CrossEncoder(
            model_cfg["reranker_model"],
            device=device,
            max_length=self.max_length,
            trust_remote_code=True,
        )
        self.cache = JsonCache(out_dir / "score_cache.json")

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors: list[Any] = []
        missing_idx: list[int] = []
        for i, text in enumerate(texts):
            key = self.cache.key("emb", text)
            cached = self.cache.get(key)
            if cached is None:
                missing_idx.append(i)
                vectors.append(None)
            else:
                vectors.append(cached)
        if missing_idx:
            batch_texts = [texts[i] for i in missing_idx]
            encoded = self.embedder.encode(
                batch_texts,
                batch_size=self.embedding_batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            for idx, vec in zip(missing_idx, encoded):
                key = self.cache.key("emb", texts[idx])
                value = np.asarray(vec, dtype=np.float32).tolist()
                self.cache.set(key, value)
                vectors[idx] = value
            self.cache.save()
        return np.asarray(vectors, dtype=np.float32)

    def rerank(self, pairs: list[tuple[str, str]]) -> list[float]:
        scores: list[Any] = []
        missing_idx: list[int] = []
        for i, (query, doc) in enumerate(pairs):
            key = self.cache.key("rerank", query, doc)
            cached = self.cache.get(key)
            if cached is None:
                missing_idx.append(i)
                scores.append(None)
            else:
                scores.append(float(cached))
        if missing_idx:
            batch_pairs = [pairs[i] for i in missing_idx]
            raw = self.reranker.predict(
                batch_pairs,
                batch_size=self.reranker_batch_size,
                show_progress_bar=False,
            )
            for idx, score in zip(missing_idx, raw):
                prob = sigmoid(float(score))
                key = self.cache.key("rerank", pairs[idx][0], pairs[idx][1])
                self.cache.set(key, prob)
                scores[idx] = prob
            self.cache.save()
        return [float(x) for x in scores]


def minmax(values: list[float]) -> list[float]:
    arr = np.asarray([v if not math.isnan(v) else np.nan for v in values], dtype=np.float64)
    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return [float("nan")] * len(values)
    lo, hi = float(valid.min()), float(valid.max())
    if abs(hi - lo) < 1e-9:
        return [0.5 if not math.isnan(v) else float("nan") for v in values]
    return [float((v - lo) / (hi - lo)) if not math.isnan(v) else float("nan") for v in values]
