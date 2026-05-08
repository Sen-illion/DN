from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

import requests

from experiments.baseline_integration.adapters.playable_protocol import (
    build_first_turn_prompt,
    build_next_turn_prompt,
    load_subset,
    normalize_playable_response,
    summarize_playable_runs,
)

SYSTEM_ID_DEFAULT = "system_2"


def html_to_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?h2>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def parse_generate_response(payload: dict[str, Any], system_id: str) -> tuple[str, str]:
    body = html_to_text(str(payload.get(system_id, "")))
    storyline = ""
    story = body
    if "Storyline" in body and "Story" in body:
        match = re.search(r"Storyline\s*(.*?)\s*Story\s*(.*)", body, re.DOTALL)
        if match:
            storyline = match.group(1).strip()
            story = match.group(2).strip()
    return storyline, story


def parse_storyline_response(payload: dict[str, Any], system_id: str) -> str:
    return html_to_text(str(payload.get(system_id, ""))).strip()


def parse_story_response(payload: dict[str, Any], system_id: str) -> str:
    if isinstance(payload.get("story"), str):
        return html_to_text(str(payload.get("story", ""))).strip()
    return html_to_text(str(payload.get(system_id, ""))).strip()


def derive_candidate_actions(item: dict[str, Any], story_text: str) -> list[str]:
    theme = item.get("theme", "the situation")
    genre = item.get("expected_genre", "interactive narrative")
    actions = [
        f"Investigate the immediate conflict around {theme}.",
        f"Secure the most fragile resource or ally in this {genre} scenario.",
        "Confront the source of pressure before the situation worsens.",
    ]
    genre_l = genre.lower()
    if "mystery" in genre_l or "??" in genre:
        actions[1] = "Follow the most concrete clue before it disappears."
    if "survival" in genre_l or "??" in genre:
        actions[1] = "Stabilize food, shelter, or medicine before taking extra risks."
    if "sci" in genre_l or "??" in genre:
        actions[2] = "Test the dangerous anomaly cautiously and record what changes."
    return actions[:4]


def build_player_state(item: dict[str, Any], story_text: str) -> str:
    sentence = re.split(r"(?<=[.!????])\s+", story_text.strip())[0] if story_text.strip() else ""
    prefix = f"You are the acting protagonist inside the theme '{item.get('theme', '')}'."
    return (prefix + " " + sentence).strip()


def call_generate(base_url: str, topic: str, system_id: str) -> dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        data={
            "id": uuid.uuid4().hex[:8],
            "topic": topic,
            "systems": system_id,
            "use_gold_titles": "FALSE",
        },
        timeout=1800,
    )
    response.raise_for_status()
    return response.json()


def call_collab_storyline(base_url: str, topic: str, storyline: str, system_id: str) -> dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/collab_storyline",
        data={
            "id": uuid.uuid4().hex[:8],
            "topic": topic,
            "system_id": system_id,
            "storyline": storyline,
        },
        timeout=1800,
    )
    response.raise_for_status()
    return response.json()


def call_generate_story(base_url: str, topic: str, storyline: str, system_id: str) -> dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate_story",
        data={
            "id": uuid.uuid4().hex[:8],
            "topic": topic,
            "system_id": system_id,
            "storyline": storyline,
        },
        timeout=1800,
    )
    response.raise_for_status()
    return response.json()


def build_topic(item: dict[str, Any]) -> str:
    return f"{item['theme']} | {item['expected_genre']} | {item['expected_tone']}"


def run_first_playable(item: dict[str, Any], base_url: str, system_id: str) -> tuple[dict[str, Any], str]:
    topic = build_topic(item)
    request_start = time.time()
    payload = call_generate(base_url, topic, system_id)
    finish_ts = time.time()
    storyline, story = parse_generate_response(payload, system_id)
    scene_setup = re.split(r"(?<=[.!????])\s+", story)[0].strip() if story.strip() else ""
    normalized = normalize_playable_response(
        baseline_id="plan_write_revise",
        benchmark_id=item["benchmark_id"],
        raw_output=payload,
        scene_setup=scene_setup,
        player_state=build_player_state(item, story),
        narrative_response=story,
        candidate_actions=derive_candidate_actions(item, story),
        suggested_next_step="Advance with one of the candidate actions while preserving the same storyline pressure.",
        supports_next_turn=True,
        request_start_ts=request_start,
        first_playable_ts=finish_ts,
        finish_ts=finish_ts,
        notes=[build_first_turn_prompt(item)],
    )
    normalized["mode"] = "first_playable"
    normalized["input_bundle"] = {"topic": topic, "system_id": system_id}
    return normalized, storyline


def run_next_turn(item: dict[str, Any], storyline: str, first_run: dict[str, Any], base_url: str, system_id: str) -> dict[str, Any]:
    actions = first_run["normalized_response"].get("candidate_actions") or ["Press forward carefully."]
    chosen_action = actions[0]
    topic = build_topic(item)
    request_start = time.time()
    storyline_payload = call_collab_storyline(base_url, topic, storyline, system_id)
    next_storyline = parse_storyline_response(storyline_payload, system_id)
    merged_storyline = "->".join([part for part in [storyline, next_storyline] if part])
    story_payload = call_generate_story(base_url, topic, merged_storyline, system_id)
    finish_ts = time.time()
    story_text = parse_story_response(story_payload, system_id)
    scene_setup = re.split(r"(?<=[.!????])\s+", story_text)[0].strip() if story_text.strip() else ""
    normalized = normalize_playable_response(
        baseline_id="plan_write_revise",
        benchmark_id=item["benchmark_id"],
        raw_output={"storyline": storyline_payload, "story": story_payload},
        scene_setup=scene_setup,
        player_state=first_run["normalized_response"].get("player_state", ""),
        narrative_response=story_text,
        candidate_actions=derive_candidate_actions(item, story_text),
        suggested_next_step=f"Chosen action was: {chosen_action}",
        supports_next_turn=True,
        request_start_ts=request_start,
        first_playable_ts=finish_ts,
        finish_ts=finish_ts,
        notes=[build_next_turn_prompt(item, first_run["normalized_response"], chosen_action)],
    )
    normalized["mode"] = "next_turn"
    normalized["input_bundle"] = {
        "topic": topic,
        "system_id": system_id,
        "chosen_action": chosen_action,
        "storyline": merged_storyline,
    }
    return normalized


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "baseline_id", "benchmark_id", "mode", "success", "latency_s",
        "scene_setup", "player_state", "candidate_actions", "suggested_next_step",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            normalized = row["normalized_response"]
            writer.writerow(
                {
                    "baseline_id": row["baseline_id"],
                    "benchmark_id": row["benchmark_id"],
                    "mode": row["mode"],
                    "success": row["success"],
                    "latency_s": row["latency_s"],
                    "scene_setup": normalized.get("scene_setup", ""),
                    "player_state": normalized.get("player_state", ""),
                    "candidate_actions": " | ".join(normalized.get("candidate_actions") or []),
                    "suggested_next_step": normalized.get("suggested_next_step", ""),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5006")
    parser.add_argument("--system-id", default=SYSTEM_ID_DEFAULT)
    parser.add_argument("--subset", required=True)
    parser.add_argument("--run-next-turn", action="store_true")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    args = parser.parse_args()

    items = load_subset(args.subset)
    first_runs: list[dict[str, Any]] = []
    next_runs: list[dict[str, Any]] = []
    for item in items:
        first_run, storyline = run_first_playable(item, args.base_url, args.system_id)
        first_runs.append(first_run)
        if args.run_next_turn:
            next_runs.append(run_next_turn(item, storyline, first_run, args.base_url, args.system_id))

    payload = {"runs": first_runs + next_runs}
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(Path(args.output_csv), first_runs + next_runs)

    summary = {
        "first_playable": summarize_playable_runs("plan_write_revise", first_runs, "first_playable"),
        "next_turn": summarize_playable_runs("plan_write_revise", next_runs, "next_turn") if next_runs else None,
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
