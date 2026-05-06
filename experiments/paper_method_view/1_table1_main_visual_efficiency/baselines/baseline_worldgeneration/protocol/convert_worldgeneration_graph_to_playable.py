from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

try:
    import networkx as nx
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"networkx is required: {exc}")

from experiments.baseline_integration.adapters.playable_protocol import normalize_playable_response, summarize_playable_runs


def load_graph(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".gml":
        return nx.read_gml(path)
    if suffix == ".dot":
        return nx.drawing.nx_pydot.read_dot(path)
    raise ValueError(f"unsupported graph file: {path}")


def graph_to_response(graph) -> tuple[str, str, str, list[str]]:
    locations = []
    objects = []
    characters = []
    for node_name, attrs in graph.nodes(data=True):
        node_type = str(attrs.get("type", "")).lower()
        flavor = str(attrs.get("flavortext", "")).strip()
        if node_type == "location":
            locations.append((str(node_name), flavor))
        elif node_type == "character":
            characters.append(str(node_name))
        else:
            objects.append(str(node_name))
    scene_setup = locations[0][1] if locations and locations[0][1] else (f"You arrive at {locations[0][0]}." if locations else "A playable world was generated.")
    player_state = "You are entering a generated interactive fiction world and must decide how to explore it."
    narrative = scene_setup
    if characters:
        narrative += " Notable characters here include " + ", ".join(characters[:3]) + "."
    if objects:
        narrative += " Important objects in reach: " + ", ".join(objects[:4]) + "."
    actions = []
    if locations:
        actions.append(f"Explore {locations[0][0]} in detail.")
    if characters:
        actions.append(f"Talk to {characters[0]}.")
    if objects:
        actions.append(f"Inspect {objects[0]}.")
    actions.append("Follow the strongest clue to the next location.")
    return scene_setup, player_state, narrative.strip(), actions[:4]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["baseline_id", "benchmark_id", "mode", "success", "latency_s", "scene_setup", "candidate_actions"]
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
                    "candidate_actions": " | ".join(normalized.get("candidate_actions") or []),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-id", required=True)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    args = parser.parse_args()

    graph_path = Path(args.graph)
    request_start = time.time()
    graph = load_graph(graph_path)
    scene_setup, player_state, narrative, actions = graph_to_response(graph)
    finish_ts = time.time()
    run = normalize_playable_response(
        baseline_id="worldgeneration",
        benchmark_id=args.benchmark_id,
        raw_output={"graph_path": str(graph_path)},
        scene_setup=scene_setup,
        player_state=player_state,
        narrative_response=narrative,
        candidate_actions=actions,
        supports_next_turn=True,
        request_start_ts=request_start,
        first_playable_ts=finish_ts,
        finish_ts=finish_ts,
        notes=["Graph-to-playable conversion only; upstream graph generation measured separately."],
    )
    run["mode"] = "first_playable"
    run["input_bundle"] = {"graph": str(graph_path)}

    payload = {"runs": [run]}
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(Path(args.output_csv), [run])

    summary = summarize_playable_runs("worldgeneration", [run], "first_playable")
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
