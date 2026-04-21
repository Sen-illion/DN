from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass
class BuildStats:
    manifest_files: int = 0
    discovered_samples: int = 0
    usable_samples: int = 0

    @property
    def coverage(self) -> float:
        if self.discovered_samples == 0:
            return 0.0
        return self.usable_samples / self.discovered_samples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a reusable eval manifest from DN image path manifests."
    )
    parser.add_argument(
        "--experiment-root",
        type=Path,
        default=Path("DN-experiment-2.0"),
        help="Root directory containing theme_*/..._image_paths.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("DN-experiment-2.0/experiments/multiview_image_consistency/results"),
        help="Directory to write output manifest and summary.",
    )
    parser.add_argument(
        "--limit-per-game",
        type=int,
        default=0,
        help="Optional cap of usable samples per game_id. 0 means no cap.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_source_manifests(experiment_root: Path) -> Iterable[Path]:
    return sorted(experiment_root.glob("theme_*/*_image_paths.json"))


def sample_record(manifest: Dict, segment: Dict) -> Dict[str, object]:
    game_id = str(manifest.get("game_id", ""))
    seg_index = int(segment.get("segment_index", -1))
    return {
        "sample_id": f"{game_id}_seg_{seg_index:03d}",
        "game_id": game_id,
        "theme_item_id": manifest.get("theme_item_id"),
        "segment_index": seg_index,
        "image_path_repo_relative": segment.get("image_path_repo_relative"),
        "source_manifest": manifest.get("manifest_file"),
    }


def build_manifest(
    experiment_root: Path,
    limit_per_game: int,
) -> tuple[List[Dict[str, object]], BuildStats]:
    stats = BuildStats()
    samples: List[Dict[str, object]] = []
    per_game_counter: Dict[str, int] = {}

    for manifest_path in iter_source_manifests(experiment_root):
        stats.manifest_files += 1
        manifest = load_json(manifest_path)
        for segment in manifest.get("segments", []):
            stats.discovered_samples += 1
            exists = bool(segment.get("exists"))
            path_rel = segment.get("image_path_repo_relative")
            if not exists or not path_rel:
                continue

            game_id = str(manifest.get("game_id", ""))
            if limit_per_game > 0 and per_game_counter.get(game_id, 0) >= limit_per_game:
                continue

            record = sample_record(manifest, segment)
            samples.append(record)
            stats.usable_samples += 1
            per_game_counter[game_id] = per_game_counter.get(game_id, 0) + 1

    return samples, stats


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    samples, stats = build_manifest(
        experiment_root=args.experiment_root,
        limit_per_game=max(0, int(args.limit_per_game)),
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    manifest_jsonl = out_dir / f"eval_manifest_{ts}.jsonl"
    latest_jsonl = out_dir / "latest_eval_manifest.jsonl"
    summary_json = out_dir / f"eval_manifest_summary_{ts}.json"
    latest_summary = out_dir / "latest_eval_manifest_summary.json"

    write_jsonl(manifest_jsonl, samples)
    write_jsonl(latest_jsonl, samples)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_root": str(args.experiment_root),
        "manifest_files": stats.manifest_files,
        "discovered_samples": stats.discovered_samples,
        "usable_samples": stats.usable_samples,
        "coverage": round(stats.coverage, 4),
        "limit_per_game": int(args.limit_per_game),
        "output_manifest_jsonl": str(manifest_jsonl),
        "output_latest_jsonl": str(latest_jsonl),
    }
    write_json(summary_json, summary)
    write_json(latest_summary, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
