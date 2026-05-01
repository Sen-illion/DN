import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


THEMES = [
    "theme_001_game_1776417898_zthbu3",
    "theme_002_game_1776418186_406ktb",
    "theme_003_game_1776418475_uho8y4",
    "theme_004_game_1776418746_kox2ae",
    "theme_005_game_1776419026_gflx4b",
    "theme_006_game_1776419299_05783f",
    "theme_012_game_1776419613_9xv3kl",
    "theme_018_game_1776419881_ts9erz",
    "theme_054_game_1776420257_ds08b3",
    "theme_073_game_1776420517_nejnnv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a text-only image baseline manifest from DN segment JSON.")
    parser.add_argument("--dn_root", default="DN-experiment-2.0")
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--segments", type=int, default=10)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def flatten_prompt_json(value: Any) -> str:
    chunks: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, str):
            text = obj.strip()
            if text:
                chunks.append(text)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            for item in obj.values():
                walk(item)

    walk(value)
    return ", ".join(chunks)


def select_prompt(data: dict[str, Any]) -> tuple[str, str]:
    prompt = str(data.get("prompt") or "").strip()
    if prompt:
        return prompt, "prompt"
    prompt_json = data.get("prompt_json")
    if prompt_json:
        text = flatten_prompt_json(prompt_json)
        if text:
            return text, "prompt_json"
    scene = str(data.get("scene") or "").strip()
    if scene:
        return scene, "scene"
    return "", "missing"


def game_id_from_theme(theme: str) -> str:
    match = re.search(r"(game_[^_]+_[A-Za-z0-9]+)$", theme)
    if not match:
        raise ValueError(f"Cannot parse game_id from theme directory name: {theme}")
    return match.group(1)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    dn_root = Path(args.dn_root)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for theme in THEMES:
        theme_dir = dn_root / theme
        game_id = game_id_from_theme(theme)
        for segment_index in range(1, args.segments + 1):
            segment = f"{segment_index:03d}"
            json_path = theme_dir / f"{game_id}_{segment}.json"
            png_path = theme_dir / f"{game_id}_{segment}.png"
            row_id = f"{game_id}/seg_{segment}"
            base = {
                "id": row_id,
                "theme_id": theme,
                "game_id": game_id,
                "segment_index": segment_index,
                "source_text_json": json_path.as_posix(),
                "dn_reference_image": png_path.as_posix() if png_path.exists() else "",
                "dn_reference_image_exists": png_path.exists(),
            }
            if not json_path.exists():
                failure = {**base, "status": "missing_text_json", "error": f"Missing {json_path}"}
                rows.append({**failure, "text_prompt": "", "prompt_source": "missing"})
                failures.append(failure)
                continue
            try:
                data = read_json(json_path)
                prompt, prompt_source = select_prompt(data)
            except Exception as exc:
                failure = {**base, "status": "json_read_error", "error": repr(exc)}
                rows.append({**failure, "text_prompt": "", "prompt_source": "error"})
                failures.append(failure)
                continue
            status = "ready" if prompt else "missing_prompt"
            row = {
                **base,
                "text_prompt": prompt,
                "prompt_source": prompt_source,
                "status": status,
                "error": "" if prompt else "No usable prompt/prompt_json/scene field",
            }
            rows.append(row)
            if status != "ready":
                failures.append(row)

    sdm_rows = [
        {
            "id": row["id"],
            "prompt": row["text_prompt"],
            "theme_id": row["theme_id"],
            "game_id": row["game_id"],
            "segment_index": row["segment_index"],
            "source_text_json": row["source_text_json"],
            "dn_reference_image": row["dn_reference_image"],
        }
        for row in rows
        if row["status"] == "ready"
    ]

    write_jsonl(output_dir / "manifest.jsonl", rows)
    write_csv(output_dir / "manifest.csv", rows)
    write_jsonl(output_dir / "sdm_v2_input.jsonl", sdm_rows)
    write_jsonl(output_dir / "input_failures.jsonl", failures)
    coverage = {
        "themes": len(THEMES),
        "expected_segments": len(THEMES) * args.segments,
        "text_json_ready": sum(1 for row in rows if row["status"] == "ready"),
        "dn_reference_images_present": sum(1 for row in rows if row["dn_reference_image_exists"]),
        "dn_reference_images_missing": sum(1 for row in rows if not row["dn_reference_image_exists"]),
        "input_failures": len(failures),
    }
    (output_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
