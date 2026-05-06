from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import string
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parents[6]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.baseline_integration.adapters.playable_protocol import (
    load_subset,
    normalize_playable_response,
    summarize_playable_runs,
)

WG_ROOT = REPO_ROOT / "experiments" / "external_baselines" / "worldgeneration" / "rule-based" / "binary_data"
BASELINE_ROOT = Path(__file__).resolve().parents[1]

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "at",
    "for",
    "with",
    "from",
    "after",
    "before",
    "into",
    "near",
    "by",
    "his",
    "her",
    "their",
    "its",
    "this",
    "that",
    "these",
    "those",
}

TITLE_WORDS = {"mr", "mrs", "ms", "dr", "sir", "lady", "lord", "colonel", "inspector", "captain", "queen", "king"}


@dataclass
class WorldState:
    graph: nx.DiGraph
    current_location: str
    source_story: str
    opening_line: str


def stable_pick(options: list[Path], key: str) -> Path:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(options)
    return sorted(options)[idx]


def choose_source_story(item: dict[str, Any]) -> Path:
    text = " ".join(
        [
            str(item.get("theme", "")),
            str(item.get("expected_genre", "")),
            str(item.get("expected_tone", "")),
            " ".join(item.get("must_have_constraints") or []),
        ]
    )
    mystery_cues = ("调查", "推理", "悬疑", "侦探", "历史", "谋杀", "线索", "疑案", "suspense", "investigation")
    fairy_cues = ("奇幻", "童话", "王国", "魔法", "妖精", "神话", "fairy", "fantasy")
    if any(cue in text for cue in mystery_cues):
        folder = WG_ROOT / "mystery"
    elif any(cue in text for cue in fairy_cues):
        folder = WG_ROOT / "fairy"
    else:
        folder = WG_ROOT / ("mystery" if int(item["benchmark_id"][-3:]) % 2 else "fairy")
    options = list(folder.glob("*_binary.txt"))
    if not options:
        raise FileNotFoundError(f"no upstream WorldGeneration binary stories found in {folder}")
    return stable_pick(options, item["benchmark_id"])


def normalize_phrase(text: str) -> str:
    text = text.replace('"', "").replace("'", "")
    text = text.replace("L:", "").replace("T:", "")
    text = text.translate(str.maketrans("", "", string.punctuation.replace("-", "")))
    tokens = [tok.strip() for tok in text.split() if tok.strip()]
    filtered = [tok for tok in tokens if tok.lower() not in STOPWORDS]
    if not filtered:
        filtered = tokens
    cleaned = " ".join(filtered[:6]).strip()
    return cleaned.title() if cleaned else ""


def classify_entity(name: str) -> str:
    raw_tokens = [tok for tok in re.split(r"\s+", name) if tok]
    lowered = {tok.lower().strip(".") for tok in raw_tokens}
    if lowered & TITLE_WORDS:
        return "character"
    capitalized = sum(1 for tok in raw_tokens if tok[:1].isupper())
    if capitalized >= 1 and len(raw_tokens) <= 4:
        return "character"
    return "object"


def parse_binary_story(binary_path: Path) -> tuple[OrderedDict[str, list[str]], str]:
    location_map: OrderedDict[str, list[str]] = OrderedDict()
    current_location = "Starting Area"
    opening_line = ""
    with binary_path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            if not line[:1].isdigit():
                if not opening_line:
                    opening_line = line
                continue
            matches = re.findall(r"\((.*?)\)", line)
            if not matches:
                continue
            triple = matches[-1]
            parts = [part.strip() for part in triple.split(";")]
            if len(parts) != 3:
                continue
            head, _, tail = parts
            if tail.startswith("L:"):
                candidate_location = normalize_phrase(tail)
                if candidate_location:
                    current_location = candidate_location
                    location_map.setdefault(current_location, [])
                anchor = normalize_phrase(head)
                if anchor:
                    location_map.setdefault(current_location, []).append(anchor)
                continue
            if tail.startswith("T:"):
                continue
            location_map.setdefault(current_location, [])
            for entity in (normalize_phrase(head), normalize_phrase(tail)):
                if entity and entity != current_location and entity not in location_map[current_location]:
                    location_map[current_location].append(entity)
    if not location_map:
        location_map["Starting Area"] = ["Mysterious Clue", "Unknown Figure"]
    return location_map, opening_line


def build_graph(location_map: OrderedDict[str, list[str]], opening_line: str) -> nx.DiGraph:
    graph = nx.DiGraph()
    locations = list(location_map.keys())
    for idx, location in enumerate(locations):
        flavortext = opening_line if idx == 0 and opening_line else f"You arrive at {location}, where the situation demands a decision."
        graph.add_node(location, type="location", flavortext=flavortext)
        if idx > 0:
            previous = locations[idx - 1]
            graph.add_edge(previous, location, type="connected")
            graph.add_edge(location, previous, type="connected")
        for entity in location_map[location]:
            entity_type = classify_entity(entity)
            if entity not in graph:
                graph.add_node(
                    entity,
                    type=entity_type,
                    flavortext=f"You examine {entity}. It may matter to the unfolding situation in {location}.",
                )
            graph.add_edge(location, entity, type="in")
    return graph


def room_snapshot(graph: nx.DiGraph, location: str) -> tuple[list[str], list[str], list[str]]:
    characters: list[str] = []
    objects: list[str] = []
    exits: list[str] = []
    for neighbor in graph.neighbors(location):
        edge_type = str(graph.edges[location, neighbor].get("type", ""))
        node_type = str(graph.nodes[neighbor].get("type", ""))
        if edge_type == "connected" and node_type == "location":
            exits.append(neighbor)
        elif edge_type == "in" and node_type == "character":
            characters.append(neighbor)
        elif edge_type == "in":
            objects.append(neighbor)
    return characters, objects, exits


def render_playable_response(state: WorldState) -> tuple[str, str, str, list[str]]:
    characters, objects, exits = room_snapshot(state.graph, state.current_location)
    scene_setup = state.graph.nodes[state.current_location].get("flavortext") or f"You arrive at {state.current_location}."
    player_state = f"You are inside the WorldGeneration scenario at {state.current_location} and need to decide how to proceed."
    narrative_bits = [scene_setup]
    if characters:
        narrative_bits.append("People here: " + ", ".join(characters[:3]) + ".")
    if objects:
        narrative_bits.append("Objects worth checking: " + ", ".join(objects[:4]) + ".")
    if exits:
        narrative_bits.append("Reachable locations: " + ", ".join(exits[:3]) + ".")
    actions: list[str] = []
    if characters:
        actions.append(f"Talk to {characters[0]}.")
    if objects:
        actions.append(f"Inspect {objects[0]}.")
    if exits:
        actions.append(f"Travel to {exits[0]}.")
    actions.append("Search for the strongest clue in the area.")
    return scene_setup, player_state, " ".join(narrative_bits), actions[:4]


def advance_state(state: WorldState, player_action: str) -> tuple[WorldState, str, str, str, list[str]]:
    characters, objects, exits = room_snapshot(state.graph, state.current_location)
    action_lower = player_action.lower()
    target_location = state.current_location
    narrative_prefix = f"You act in {state.current_location}."
    if "travel to" in action_lower and exits:
        target_location = exits[0]
        narrative_prefix = f"You leave {state.current_location} and move toward {target_location}."
    elif "talk to" in action_lower and characters:
        narrative_prefix = f"You approach {characters[0]} and draw out a useful response."
    elif "inspect" in action_lower and objects:
        narrative_prefix = f"You inspect {objects[0]} and uncover a fresh detail."
    next_state = WorldState(
        graph=state.graph,
        current_location=target_location,
        source_story=state.source_story,
        opening_line=state.opening_line,
    )
    scene_setup, player_state, narrative, actions = render_playable_response(next_state)
    narrative = f"{narrative_prefix} {narrative}"
    return next_state, scene_setup, player_state, narrative, actions


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "baseline_id",
        "benchmark_id",
        "mode",
        "success",
        "latency_s",
        "source_story",
        "scene_setup",
        "candidate_actions",
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
                    "mode": row.get("mode"),
                    "success": row["success"],
                    "latency_s": row["latency_s"],
                    "source_story": row.get("input_bundle", {}).get("source_story", ""),
                    "scene_setup": normalized.get("scene_setup", ""),
                    "candidate_actions": " | ".join(normalized.get("candidate_actions") or []),
                }
            )


def run_subset(subset_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    first_runs: list[dict[str, Any]] = []
    next_runs: list[dict[str, Any]] = []
    for item in load_subset(subset_path):
        source_story = choose_source_story(item)
        request_start = time.time()
        location_map, opening_line = parse_binary_story(source_story)
        graph = build_graph(location_map, opening_line)
        current_location = next(iter(location_map.keys()))
        state = WorldState(
            graph=graph,
            current_location=current_location,
            source_story=str(source_story),
            opening_line=opening_line,
        )
        scene_setup, player_state, narrative, actions = render_playable_response(state)
        first_ts = time.time()
        first_run = normalize_playable_response(
            baseline_id="worldgeneration",
            benchmark_id=item["benchmark_id"],
            raw_output={"source_story": str(source_story), "nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()},
            scene_setup=scene_setup,
            player_state=player_state,
            narrative_response=narrative,
            candidate_actions=actions,
            supports_next_turn=True,
            request_start_ts=request_start,
            first_playable_ts=first_ts,
            finish_ts=first_ts,
            notes=[
                "Adapted from official WorldGeneration rule-based binary story assets.",
                "NeuralCoref and Stanford NER were replaced with local fallbacks for current-machine reproducibility.",
            ],
        )
        first_run["mode"] = "first_playable"
        first_run["input_bundle"] = {"source_story": str(source_story), "benchmark_theme": item.get("theme", "")}
        first_runs.append(first_run)

        next_request_start = time.time()
        chosen_action = actions[0] if actions else "Search for the strongest clue in the area."
        _, next_scene, next_player_state, next_narrative, next_actions = advance_state(state, chosen_action)
        next_ts = time.time()
        next_run = normalize_playable_response(
            baseline_id="worldgeneration",
            benchmark_id=item["benchmark_id"],
            raw_output={"source_story": str(source_story), "player_action": chosen_action},
            scene_setup=next_scene,
            player_state=next_player_state,
            narrative_response=next_narrative,
            candidate_actions=next_actions,
            supports_next_turn=True,
            request_start_ts=next_request_start,
            first_playable_ts=next_ts,
            finish_ts=next_ts,
            notes=[
                f"Next-turn response generated from action: {chosen_action}",
                "State progression uses the upstream-style room graph reconstructed from official binary story assets.",
            ],
        )
        next_run["mode"] = "next_turn"
        next_run["input_bundle"] = {
            "source_story": str(source_story),
            "benchmark_theme": item.get("theme", ""),
            "player_action": chosen_action,
        }
        next_runs.append(next_run)
    return first_runs, next_runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    args = parser.parse_args()

    first_runs, next_runs = run_subset(Path(args.subset))
    payload = {"runs": first_runs + next_runs}

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    write_csv(Path(args.output_csv), first_runs + next_runs)

    summary = {
        "baseline_id": "worldgeneration",
        "first_playable": summarize_playable_runs("worldgeneration", first_runs, "first_playable"),
        "next_turn": summarize_playable_runs("worldgeneration", next_runs, "next_turn"),
    }
    summary_json = Path(args.summary_json)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
