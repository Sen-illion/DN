from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "baselines" / "next_turn_visual_eval"
DEFAULT_IMAGE_BASELINE_RUN = REPO_ROOT / "outputs" / "baseline_image_from_dn_text" / "run_20260430_145825"
DEFAULT_DN_MANIFEST = DEFAULT_IMAGE_BASELINE_RUN / "manifest" / "manifest.jsonl"
PAPER_BASELINES_DIR = (
    REPO_ROOT / "experiments" / "paper_method_view" / "1_table1_main_visual_efficiency" / "baselines"
)
NORMALIZED_RUNS_DIR = REPO_ROOT / "experiments" / "baseline_integration" / "normalized_runs"


@dataclass
class SequenceRecord:
    baseline: str
    game_id: str
    segment_index: int
    image_path: Path
    image_exists: bool
    source_file: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build local-only inventory and next-turn pair CSVs for visual consistency evaluation. "
            "Pairs are constructed as adjacent segment images within the same game."
        )
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--baseline-run-dir", default=str(DEFAULT_IMAGE_BASELINE_RUN))
    parser.add_argument(
        "--dn-manifest",
        default=str(DEFAULT_DN_MANIFEST),
        help="DN reference image manifest used to add DN itself to the same adjacent-segment protocol.",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    cleaned = []
    for ch in value.lower():
        if ch.isalnum():
            cleaned.append(ch)
        else:
            cleaned.append("_")
    slug = "".join(cleaned)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def normalize_display_name(value: str) -> str:
    lowered = value.lower().replace("_", "").replace("-", "")
    aliases = {
        "iclora": "IC-LoRA",
        "sdmv2": "SDM-v2",
        "storydiffusion": "StoryDiffusion",
        "genagents": "GenAgents",
        "aidungeon": "AIDungeon",
        "light": "LIGHT",
        "planwriterevise": "Plan-Write-Revise",
        "worldgeneration": "WorldGeneration",
        "doc": "DOC",
    }
    return aliases.get(lowered, value)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def expected_dn_image_path(row: dict[str, Any]) -> Path | None:
    explicit_path = resolve_path(row.get("dn_reference_image"))
    if explicit_path is not None:
        return explicit_path
    source_json = resolve_path(row.get("source_text_json"))
    if source_json is not None:
        return source_json.with_suffix(".png")
    return None


def parse_segment_index(record_id: str) -> int | None:
    if "/seg_" not in record_id:
        return None
    suffix = record_id.rsplit("/seg_", 1)[-1]
    try:
        return int(suffix)
    except ValueError:
        return None


def parse_game_id(row: dict[str, Any]) -> str | None:
    game_id = row.get("game_id")
    if game_id:
        return str(game_id)
    record_id = row.get("id")
    if isinstance(record_id, str) and "/" in record_id:
        return record_id.split("/", 1)[0]
    return None


def load_sequence_records(index_path: Path, baseline: str) -> list[SequenceRecord]:
    records: list[SequenceRecord] = []
    for row in read_jsonl(index_path):
        game_id = parse_game_id(row)
        record_id = row.get("id")
        segment_index = row.get("segment_index")
        if segment_index is None and isinstance(record_id, str):
            segment_index = parse_segment_index(record_id)
        image_path = resolve_path(row.get("image_path"))
        if not game_id or segment_index is None or image_path is None:
            continue
        records.append(
            SequenceRecord(
                baseline=baseline,
                game_id=game_id,
                segment_index=int(segment_index),
                image_path=image_path,
                image_exists=image_path.is_file(),
                source_file=index_path,
            )
        )
    return records


def build_candidate_pairs(records: list[SequenceRecord], baseline: str) -> list[dict[str, Any]]:
    by_game: dict[str, list[SequenceRecord]] = defaultdict(list)
    for record in records:
        by_game[record.game_id].append(record)

    pairs: list[dict[str, Any]] = []
    for game_id, game_records in by_game.items():
        ordered = sorted(game_records, key=lambda item: item.segment_index)
        for left, right in zip(ordered, ordered[1:]):
            pair_id = f"{game_id}_seg_{left.segment_index:03d}_to_{right.segment_index:03d}"
            pairs.append(
                {
                    "pair_id": pair_id,
                    "game_id": game_id,
                    "group": baseline,
                    "ref": str(left.image_path),
                    "candidate": str(right.image_path),
                    "ref_exists": left.image_exists,
                    "candidate_exists": right.image_exists,
                    "ref_segment_index": left.segment_index,
                    "candidate_segment_index": right.segment_index,
                    "source_file": str(left.source_file),
                    "pair_type": "next_turn_continuity",
                }
            )
    return pairs


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def summarize_index_baseline(index_path: Path) -> dict[str, Any]:
    baseline = normalize_display_name(index_path.parent.name)
    records = load_sequence_records(index_path, baseline=baseline)
    candidate_pairs = build_candidate_pairs(records, baseline=baseline)
    valid_pairs = [row for row in candidate_pairs if row["ref_exists"] and row["candidate_exists"]]
    missing_pairs = len(candidate_pairs) - len(valid_pairs)
    local_image_records = sum(1 for row in records if row.image_exists)
    image_path_missing = sum(1 for row in read_jsonl(index_path) if "image_path" not in row)

    notes: list[str] = [
        "Pairs are built as adjacent segments within the same game (seg_n -> seg_n+1).",
    ]
    blocker = None
    if not candidate_pairs:
        blocker = "index_present_but_no_adjacent_segment_pairs"
    elif not valid_pairs:
        blocker = "no_local_images_for_any_candidate_pair"
    if image_path_missing:
        notes.append(f"{image_path_missing} index rows did not expose an image_path field.")
        if blocker is None and local_image_records == 0:
            blocker = "index_missing_image_paths_or_local_images"

    return {
        "baseline": baseline,
        "slug": slugify(baseline),
        "source_kind": "image_sequence_index",
        "artifact_roots": [str(index_path)],
        "records_found": len(records),
        "games_found": len({row.game_id for row in records}),
        "local_image_records": local_image_records,
        "candidate_next_turn_pairs": len(candidate_pairs),
        "evaluable_pairs": len(valid_pairs),
        "evaluable_now": bool(valid_pairs),
        "blocker": blocker,
        "notes": notes,
        "candidate_pairs": candidate_pairs,
        "valid_pairs": valid_pairs,
    }


def summarize_dn_manifest(manifest_path: Path) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None

    baseline = "DN"
    records: list[SequenceRecord] = []
    raw_rows = read_jsonl(manifest_path)
    for row in raw_rows:
        game_id = parse_game_id(row)
        segment_index = row.get("segment_index")
        image_path = expected_dn_image_path(row)
        if not game_id or segment_index is None or image_path is None:
            continue
        records.append(
            SequenceRecord(
                baseline=baseline,
                game_id=game_id,
                segment_index=int(segment_index),
                image_path=image_path,
                image_exists=image_path.is_file(),
                source_file=manifest_path,
            )
        )

    candidate_pairs = build_candidate_pairs(records, baseline=baseline)
    valid_pairs = [row for row in candidate_pairs if row["ref_exists"] and row["candidate_exists"]]
    local_image_records = sum(1 for row in records if row.image_exists)
    blocker = None
    if not candidate_pairs:
        blocker = "dn_manifest_present_but_no_adjacent_segment_pairs"
    elif not valid_pairs:
        blocker = "dn_manifest_has_no_local_valid_image_pairs"

    return {
        "baseline": baseline,
        "slug": slugify(baseline),
        "source_kind": "dn_reference_image_manifest",
        "artifact_roots": [str(manifest_path)],
        "records_found": len(records),
        "games_found": len({row.game_id for row in records}),
        "local_image_records": local_image_records,
        "candidate_next_turn_pairs": len(candidate_pairs),
        "evaluable_pairs": len(valid_pairs),
        "evaluable_now": bool(valid_pairs),
        "blocker": blocker,
        "notes": [
            "Pairs are built as adjacent DN reference segment images within the same game (seg_n -> seg_n+1).",
            "This uses the same local-only next-turn DINOv2 protocol as the image baselines.",
        ],
        "candidate_pairs": candidate_pairs,
        "valid_pairs": valid_pairs,
    }


def discover_index_baselines(run_dir: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for index_path in sorted(run_dir.glob("*/index.jsonl")):
        if index_path.parent.name in {"manifest", "reports"}:
            continue
        inventory.append(summarize_index_baseline(index_path))
    return inventory


def merge_inventory(existing: dict[str, dict[str, Any]], incoming: dict[str, Any]) -> None:
    slug = incoming["slug"]
    current = existing.get(slug)
    if current is None:
        existing[slug] = incoming
        return

    merged_roots = sorted(set(current.get("artifact_roots", [])) | set(incoming.get("artifact_roots", [])))
    merged_notes = list(current.get("notes", []))
    for note in incoming.get("notes", []):
        if note not in merged_notes:
            merged_notes.append(note)
    current["artifact_roots"] = merged_roots
    current["notes"] = merged_notes
    if incoming.get("source_kind") not in str(current.get("source_kind")):
        current["source_kind"] = f"{current['source_kind']}+{incoming['source_kind']}"


def discover_paper_metadata(existing: dict[str, dict[str, Any]]) -> None:
    if not PAPER_BASELINES_DIR.is_dir():
        return
    for path in sorted(PAPER_BASELINES_DIR.glob("baseline_*")):
        if not path.is_dir():
            continue
        baseline = normalize_display_name(path.name.removeprefix("baseline_"))
        merge_inventory(
            existing,
            {
                "baseline": baseline,
                "slug": slugify(baseline),
                "source_kind": "paper_metadata_only",
                "artifact_roots": [str(path)],
                "records_found": 0,
                "games_found": 0,
                "local_image_records": 0,
                "candidate_next_turn_pairs": 0,
                "evaluable_pairs": 0,
                "evaluable_now": False,
                "blocker": "no_local_image_artifacts_in_paper_method_view_dir",
                "notes": ["Protocol/raw_run/summaries exist, but no local images were found in the workspace."],
                "candidate_pairs": [],
                "valid_pairs": [],
            },
        )


def discover_normalized_runs(existing: dict[str, dict[str, Any]]) -> None:
    if not NORMALIZED_RUNS_DIR.is_dir():
        return

    for manifest_path in sorted(NORMALIZED_RUNS_DIR.glob("**/manifest.json")):
        payload = read_json(manifest_path)
        baseline = normalize_display_name(str(payload.get("baseline_id", manifest_path.parent.name)))
        merge_inventory(
            existing,
            {
                "baseline": baseline,
                "slug": slugify(baseline),
                "source_kind": "normalized_run_metadata_only",
                "artifact_roots": [str(manifest_path.parent)],
                "records_found": 0,
                "games_found": 0,
                "local_image_records": 0,
                "candidate_next_turn_pairs": 0,
                "evaluable_pairs": 0,
                "evaluable_now": False,
                "blocker": "normalized_run_contains_text_or_manifest_without_local_images",
                "notes": ["Normalized run metadata exists, but no local image artifacts were found for visual evaluation."],
                "candidate_pairs": [],
                "valid_pairs": [],
            },
        )

    for normalized_path in sorted(NORMALIZED_RUNS_DIR.glob("*.normalized.json")):
        payload = read_json(normalized_path)
        baseline = normalize_display_name(str(payload.get("baseline_id", normalized_path.stem)))
        merge_inventory(
            existing,
            {
                "baseline": baseline,
                "slug": slugify(baseline),
                "source_kind": "normalized_run_metadata_only",
                "artifact_roots": [str(normalized_path)],
                "records_found": 0,
                "games_found": 0,
                "local_image_records": 0,
                "candidate_next_turn_pairs": 0,
                "evaluable_pairs": 0,
                "evaluable_now": False,
                "blocker": "normalized_run_contains_text_or_manifest_without_local_images",
                "notes": ["Normalized run metadata exists, but no local image artifacts were found for visual evaluation."],
                "candidate_pairs": [],
                "valid_pairs": [],
            },
        )


def inventory_rows_for_json(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "baseline": item["baseline"],
                "slug": item["slug"],
                "source_kind": item["source_kind"],
                "artifact_roots": item["artifact_roots"],
                "records_found": item["records_found"],
                "games_found": item["games_found"],
                "local_image_records": item["local_image_records"],
                "candidate_next_turn_pairs": item["candidate_next_turn_pairs"],
                "evaluable_pairs": item["evaluable_pairs"],
                "evaluable_now": item["evaluable_now"],
                "blocker": item["blocker"],
                "notes": item["notes"],
            }
        )
    return rows


def write_inventory_markdown(path: Path, items: list[dict[str, Any]]) -> None:
    lines = [
        "# Baseline Inventory",
        "",
        "| Baseline | Source Kind | Local Images | Candidate Pairs | Evaluable Pairs | Evaluable Now | Blocker |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in items:
        blocker = item["blocker"] or ""
        lines.append(
            f"| {item['baseline']} | `{item['source_kind']}` | {item['local_image_records']} | "
            f"{item['candidate_next_turn_pairs']} | {item['evaluable_pairs']} | "
            f"{'yes' if item['evaluable_now'] else 'no'} | {blocker} |"
        )
    lines.append("")
    for item in items:
        lines.append(f"## {item['baseline']}")
        lines.append("")
        for artifact_root in item["artifact_roots"]:
            lines.append(f"- artifact_root: `{artifact_root}`")
        lines.append(f"- source_kind: `{item['source_kind']}`")
        lines.append(f"- local_image_records: `{item['local_image_records']}`")
        lines.append(f"- candidate_next_turn_pairs: `{item['candidate_next_turn_pairs']}`")
        lines.append(f"- evaluable_pairs: `{item['evaluable_pairs']}`")
        lines.append(f"- evaluable_now: `{item['evaluable_now']}`")
        if item["blocker"]:
            lines.append(f"- blocker: `{item['blocker']}`")
        for note in item["notes"]:
            lines.append(f"- note: {note}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    pairs_dir = output_dir / "pairs"
    inventory_json = output_dir / "inventory.json"
    inventory_md = output_dir / "inventory.md"
    pair_build_summary = output_dir / "pair_build_summary.json"

    image_baselines = discover_index_baselines(Path(args.baseline_run_dir))
    inventory_by_slug = {item["slug"]: item for item in image_baselines}
    dn_item = summarize_dn_manifest(Path(args.dn_manifest))
    if dn_item:
        inventory_by_slug[dn_item["slug"]] = dn_item
    discover_paper_metadata(inventory_by_slug)
    discover_normalized_runs(inventory_by_slug)

    inventory_items = sorted(inventory_by_slug.values(), key=lambda item: item["baseline"].lower())

    for item in inventory_items:
        slug = item["slug"]
        candidate_path = pairs_dir / f"{slug}_pair_candidates.csv"
        valid_path = pairs_dir / f"{slug}_pairs.csv"
        write_csv(
            candidate_path,
            item.get("candidate_pairs", []),
            [
                "pair_id",
                "game_id",
                "group",
                "ref",
                "candidate",
                "ref_exists",
                "candidate_exists",
                "ref_segment_index",
                "candidate_segment_index",
                "source_file",
                "pair_type",
            ],
        )
        write_csv(
            valid_path,
            item.get("valid_pairs", []),
            ["pair_id", "game_id", "group", "ref", "candidate"],
        )

    inventory_payload = {
        "protocol": "next_turn_continuity",
        "pair_definition": {
            "ref": "current/pre-turn image",
            "candidate": "next-turn continuation image",
            "current_repo_fallback": "adjacent segment pairing within the same game when only sequential baseline index files exist",
        },
        "inventory": inventory_rows_for_json(inventory_items),
    }
    inventory_json.parent.mkdir(parents=True, exist_ok=True)
    inventory_json.write_text(json.dumps(inventory_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_inventory_markdown(inventory_md, inventory_items)

    pair_summary_payload = {
        "pairs_dir": str(pairs_dir),
        "baseline_count": len(inventory_items),
        "evaluable_baseline_count": sum(1 for item in inventory_items if item["evaluable_now"]),
        "candidate_pair_count": sum(item["candidate_next_turn_pairs"] for item in inventory_items),
        "evaluable_pair_count": sum(item["evaluable_pairs"] for item in inventory_items),
    }
    pair_build_summary.write_text(json.dumps(pair_summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"inventory_json": str(inventory_json), "pairs_dir": str(pairs_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
