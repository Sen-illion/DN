from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from src.image.api_providers import call_image_api_with_custom_size


DEFAULT_DEPTHS = (1, 2, 3, 4)
SOURCE_DIR = REPO_ROOT / "experiments" / "benchmark" / "standard_runs"
DEFAULT_REPAIRED_DIR = SOURCE_DIR / "repaired_v16_pregendepth"
DEFAULT_IMAGE_DIR = REPO_ROOT / "experiments" / "benchmark" / "repaired_images" / "v16_pregendepth"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_image_result(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, dict):
        for key in ("url", "image_url", "path", "result"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None
    if isinstance(result, str) and result.strip():
        return result.strip()
    return None


def materialize_image(result: Any, target_path: Path) -> str | None:
    value = normalize_image_result(result)
    if not value:
        return None

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if value.startswith("data:image"):
        if "," not in value:
            return None
        _, encoded = value.split(",", 1)
        data = base64.b64decode(re.sub(r"\s+", "", encoded))
        target_path.write_bytes(data)
        return str(target_path.resolve())

    if value.startswith("http://") or value.startswith("https://"):
        import requests

        resp = requests.get(value, timeout=60)
        resp.raise_for_status()
        target_path.write_bytes(resp.content)
        return str(target_path.resolve())

    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / value.lstrip("/\\")).resolve()
    if candidate.exists():
        target_path.write_bytes(candidate.read_bytes())
        return str(target_path.resolve())
    return None


def generate_with_retries(prompt: str, target_path: Path, *, attempts: int = 3, sleep_seconds: float = 2.0) -> str | None:
    last_error: str | None = None
    size_options = [
        (1920, 1080),
        (1280, 720),
        (1024, 576),
    ]
    for attempt in range(1, attempts + 1):
        width, height = size_options[min(attempt - 1, len(size_options) - 1)]
        try:
            result = call_image_api_with_custom_size(
                prompt,
                width=width,
                height=height,
                request_type="scene_image",
            )
            saved = materialize_image(result, target_path)
            if saved:
                return saved
            last_error = "empty_image_result"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        if attempt < attempts:
            print(f"[repair] retry {attempt}/{attempts - 1} for {target_path.name} at {width}x{height} after error: {last_error}")
            time.sleep(sleep_seconds)

    print(f"[repair] gave up on {target_path} after {attempts} attempts: {last_error}")
    return None


def replace_exact_strings(obj: Any, replacements: dict[str, str]) -> Any:
    if isinstance(obj, dict):
        return {k: replace_exact_strings(v, replacements) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_exact_strings(v, replacements) for v in obj]
    if isinstance(obj, str) and obj in replacements:
        return replacements[obj]
    return obj


def scene_image_source(turn: dict[str, Any]) -> str | None:
    prompt = turn.get("scene_image_prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()
    click = (turn.get("click") or {}).get("response_json") or {}
    option_data = click.get("optionData") or {}
    scene_image = option_data.get("scene_image") or {}
    if isinstance(scene_image, dict):
        prompt = scene_image.get("prompt")
        if isinstance(prompt, str) and prompt.strip():
            return prompt.strip()
    return None


def turn_target_path(image_dir: Path, depth: int, run: dict[str, Any], turn: dict[str, Any]) -> Path:
    benchmark_id = str(run.get("benchmark_id") or "unknown")
    turn_index = int(turn.get("turn_index") or 0)
    safe_benchmark_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", benchmark_id)
    return image_dir / f"d{depth}" / safe_benchmark_id / f"turn{turn_index:02d}.png"


def repaired_run_path(repaired_dir: Path, source_path: Path) -> Path:
    return repaired_dir / source_path.name


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        if rows:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            fh.write("")


def run_depth(depth: int, source_path: Path, repaired_dir: Path, image_dir: Path) -> dict[str, Any]:
    payload = load_json(source_path)
    replacements: dict[str, str] = {}
    generated = 0
    skipped = 0
    failed = 0
    missing_before = 0
    missing_after = 0
    processed = 0

    for run in payload.get("runs", []):
        for turn in run.get("turns", []):
            old_url = turn.get("scene_image_url")
            if not isinstance(old_url, str) or not old_url.strip():
                continue
            old_url = old_url.strip()
            local_old = REPO_ROOT / old_url.lstrip("/\\")
            if not local_old.exists():
                missing_before += 1

            target_path = turn_target_path(image_dir, depth, run, turn)
            if target_path.exists():
                skipped += 1
                processed += 1
                replacements[old_url] = str(target_path.resolve())
                turn["scene_image_url"] = str(target_path.resolve())
                print(f"[repair][d{depth}] skip existing {run.get('benchmark_id')} turn {turn.get('turn_index')} -> {target_path}")
                continue

            prompt = scene_image_source(turn)
            if not prompt:
                failed += 1
                processed += 1
                print(f"[repair][d{depth}] missing prompt {run.get('benchmark_id')} turn {turn.get('turn_index')}")
                continue

            saved = generate_with_retries(prompt, target_path)
            processed += 1
            if not saved:
                failed += 1
                print(f"[repair][d{depth}] failed {run.get('benchmark_id')} turn {turn.get('turn_index')}")
                continue

            generated += 1
            replacements[old_url] = saved
            turn["scene_image_url"] = saved
            print(f"[repair][d{depth}] generated {run.get('benchmark_id')} turn {turn.get('turn_index')} -> {saved}")

    payload = replace_exact_strings(payload, replacements)
    output_path = repaired_run_path(repaired_dir, source_path)
    write_json(output_path, payload)

    for run in payload.get("runs", []):
        for turn in run.get("turns", []):
            url = turn.get("scene_image_url")
            if isinstance(url, str) and url.strip():
                local = Path(url)
                if not local.is_absolute():
                    local = (REPO_ROOT / url.lstrip("/\\")).resolve()
                if not local.exists():
                    missing_after += 1

    return {
        "depth": depth,
        "source_path": str(source_path),
        "repaired_path": str(output_path),
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "processed": processed,
        "missing_before": missing_before,
        "missing_after": missing_after,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair v16 pregendepth scene images and write repaired run JSONs.")
    parser.add_argument("--depths", nargs="*", type=int, default=list(DEFAULT_DEPTHS))
    parser.add_argument("--source-dir", default=str(SOURCE_DIR))
    parser.add_argument("--repaired-dir", default=str(DEFAULT_REPAIRED_DIR))
    parser.add_argument("--image-dir", default=str(DEFAULT_IMAGE_DIR))
    parser.add_argument("--manifest-json", default=str(DEFAULT_REPAIRED_DIR / "repair_manifest.json"))
    parser.add_argument("--manifest-csv", default=str(DEFAULT_REPAIRED_DIR / "repair_manifest.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir)
    repaired_dir = Path(args.repaired_dir)
    image_dir = Path(args.image_dir)
    repaired_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for depth in args.depths:
        source_path = source_dir / f"benchmark_v16_pregendepth_d{depth}_turn4_rw60_formal20.json"
        if not source_path.is_file():
            records.append(
                {
                    "depth": depth,
                    "source_path": str(source_path),
                    "repaired_path": "",
                    "generated": 0,
                    "skipped": 0,
                    "failed": 0,
                    "processed": 0,
                    "missing_before": 0,
                    "missing_after": 0,
                    "status": "missing_source",
                }
            )
            continue
        record = run_depth(depth, source_path, repaired_dir, image_dir)
        record["status"] = "ok" if record["failed"] == 0 and record["missing_after"] == 0 else "partial"
        records.append(record)

    manifest = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "image_dir": str(image_dir),
        "repaired_dir": str(repaired_dir),
        "records": records,
    }
    write_json(Path(args.manifest_json), manifest)
    write_csv(Path(args.manifest_csv), records)
    print(args.manifest_json)
    print(args.manifest_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
