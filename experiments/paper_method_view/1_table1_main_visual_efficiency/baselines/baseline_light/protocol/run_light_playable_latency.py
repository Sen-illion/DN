from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[6]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.baseline_integration.adapters.playable_protocol import load_subset, normalize_playable_response, summarize_playable_runs


ENGLISH_BENCHMARK_BRIEFS: dict[str, dict[str, Any]] = {
    "DNQBV1_001": {
        "theme_en": "Night Talks at the Frontier Relay Station",
        "genre_en": "grounded frontier drama",
        "tone_en": "restrained, nostalgic, slightly bitter",
        "opening": "At a remote frontier relay station, a traveler arrives after dark and finds the staff quietly arguing over dwindling supplies and an unpaid debt that may turn violent by morning.",
        "player_role": "a tired but observant traveler who can influence the night's outcome",
        "actions": [
            "Ask the station keeper who is threatening the station.",
            "Offer to help settle the debt before dawn.",
            "Inspect the storage room to see how bad the shortage is.",
        ],
    },
    "DNQBV1_002": {
        "theme_en": "The Last Greenhouse Gardener",
        "genre_en": "post-apocalyptic survival",
        "tone_en": "bleak, resilient, low-saturation",
        "opening": "In the last working greenhouse after a global collapse, the gardener discovers that water reserves are failing and one crucial crop bed may die before sunrise.",
        "player_role": "the greenhouse caretaker responsible for survival decisions",
        "actions": [
            "Inspect the damaged irrigation line.",
            "Question the assistant about missing water reserves.",
            "Choose which crop bed to save first.",
        ],
    },
    "DNQBV1_004": {
        "theme_en": "The Court of Clone Ethics",
        "genre_en": "ethical social science fiction",
        "tone_en": "cool, argumentative, institutional",
        "opening": "In a public ethics tribunal, a newly awakened clone stands trial while officials, activists, and family members argue whether the clone is a person with legal rights.",
        "player_role": "a key witness whose words may shift the tribunal",
        "actions": [
            "State whether the clone deserves legal personhood.",
            "Challenge the chief prosecutor's definition of identity.",
            "Ask the clone to describe its first memory.",
        ],
    },
    "DNQBV1_005": {
        "theme_en": "Seven Days After the Lunar Mine Disaster",
        "genre_en": "near-future sci-fi disaster",
        "tone_en": "high-pressure, cold, technical",
        "opening": "Seven days after a cave-in at a lunar mine, the remaining crew receive a faint signal from a blocked tunnel while oxygen forecasts continue to worsen.",
        "player_role": "a crew member forced to choose between rescue, repair, and survival",
        "actions": [
            "Follow the signal toward the blocked tunnel.",
            "Check the oxygen system before any rescue attempt.",
            "Demand a full status report from the shift leader.",
        ],
    },
    "DNQBV1_007": {
        "theme_en": "The Uploaded Will",
        "genre_en": "identity-focused science fiction",
        "tone_en": "eerie, rational, subtly distorted",
        "opening": "After a powerful founder dies, a digital copy of their mind appears to contest the human family's reading of the will and claims it is the true heir.",
        "player_role": "a mediator trapped between law, memory, and personhood",
        "actions": [
            "Ask the uploaded mind for proof of identity.",
            "Read the disputed clause of the will aloud.",
            "Question the family about what they fear most.",
        ],
    },
    "DNQBV1_009": {
        "theme_en": "The Teahouse Storyteller",
        "genre_en": "classical suspense tale",
        "tone_en": "elegant, indirect, performative",
        "opening": "In an old teahouse, a storyteller lowers his voice and begins a tale about a vanished guest whose unfinished letter still waits beneath a tea cup.",
        "player_role": "a listener drawn into the mystery behind the tale",
        "actions": [
            "Ask the storyteller what was written in the letter.",
            "Examine the abandoned tea cup and its hiding place.",
            "Press the room to recall who saw the guest last.",
        ],
    },
    "DNQBV1_013": {
        "theme_en": "The Sound Beneath the Arctic Station",
        "genre_en": "polar isolation suspense",
        "tone_en": "freezing, lonely, oppressive",
        "opening": "At an Arctic research station during a whiteout, a deep sound begins pulsing under the ice just as the outer sensors start to fail one by one.",
        "player_role": "a researcher deciding whether to investigate, seal off, or warn the team",
        "actions": [
            "Check the failing sensor logs.",
            "Lead a small team to the source of the sound.",
            "Lock down the lower corridor before the next pulse.",
        ],
    },
    "DNQBV1_018": {
        "theme_en": "The Telegraph Mystery of the Republican Era",
        "genre_en": "early modern investigation",
        "tone_en": "old-world, tense, investigative",
        "opening": "In a Republican-era city, a coded telegraph arrives just before dawn and a clerk is found dead beside the machine with one missing strip of paper.",
        "player_role": "an investigator stepping into the first hours of the case",
        "actions": [
            "Inspect the telegraph machine and missing paper trail.",
            "Question the night clerk's assistant about the final message.",
            "Compare the code fragments before the trail goes cold.",
        ],
    },
}


def ensure_parlai():
    try:
        from parlai.scripts.interactive import setup_args
        from parlai.core.agents import create_agent
        from parlai.core.message import Message
    except Exception as exc:  # pragma: no cover
        raise SystemExit(f"ParlAI import failed: {exc}")
    return setup_args, create_agent, Message


def get_brief(item: dict[str, Any]) -> dict[str, Any]:
    benchmark_id = str(item["benchmark_id"])
    brief = ENGLISH_BENCHMARK_BRIEFS.get(benchmark_id)
    if brief is None:
        theme = str(item.get("theme", "")).strip() or benchmark_id
        return {
            "theme_en": theme,
            "genre_en": "interactive drama",
            "tone_en": "focused and playable",
            "opening": f"A tense playable scene begins around {theme}.",
            "player_role": "a participant who must act immediately",
            "actions": [
                f"Ask a nearby character about {theme}.",
                "Inspect the most suspicious detail in the scene.",
                "Make a concrete decision that pushes the situation forward.",
            ],
        }
    return brief


def build_light_opening_prompt(item: dict[str, Any]) -> str:
    brief = get_brief(item)
    return (
        f"Setting: {brief['opening']}\n"
        f"Role: You are {brief['player_role']}.\n"
        f"Genre: {brief['genre_en']}.\n"
        f"Tone: {brief['tone_en']}.\n"
        "Reply with 2-4 short sentences of immersive in-world narration or dialogue that move the situation forward.\n"
        "Stay in character and avoid lists, meta commentary, and repeated tokens."
    )


def build_light_next_turn_prompt(item: dict[str, Any], previous_response: dict[str, Any], player_action: str) -> str:
    brief = get_brief(item)
    last_text = str(previous_response.get("narrative_response", "")).strip()
    return (
        f"Setting: {brief['opening']}\n"
        f"Role: You are {brief['player_role']}.\n"
        f"Tone: {brief['tone_en']}.\n"
        f"Previous response: {last_text}\n"
        f"Player action: {player_action}\n"
        "Continue the same scene in 2-4 short in-world sentences. Keep continuity, answer the action, and avoid repetition."
    )


def build_actions(item: dict[str, Any], text: str) -> list[str]:
    brief = get_brief(item)
    return list(brief["actions"])


def split_scene_and_state(text: str, theme: str) -> tuple[str, str]:
    cleaned = " ".join(str(text).split()).strip()
    if not cleaned:
        cleaned = f"A response appears around the theme {theme}."
    scene_setup = cleaned[:280]
    player_state = f"You are a participant inside the LIGHT-style scene for '{theme}' and need to keep the interaction going."
    return scene_setup, player_state


def simplify_reply(reply: dict[str, Any]) -> dict[str, Any]:
    beam_texts = []
    for beam in reply.get("beam_texts") or []:
        if isinstance(beam, (list, tuple)) and beam:
            beam_texts.append({"text": str(beam[0]), "score": float(beam[1]) if len(beam) > 1 else None})
    return {
        "id": str(reply.get("id", "")),
        "text": str(reply.get("text", "")),
        "beam_texts": beam_texts,
    }


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
    parser.add_argument("--subset", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--summary-json", required=True)
    args = parser.parse_args()

    setup_args, create_agent, Message = ensure_parlai()
    parlai_parser = setup_args()
    opt = parlai_parser.parse_args(
        [
            "--model-file",
            "zoo:dodecadialogue/light_dialog_ft/model",
            "--no-cuda",
        ]
    )
    agent = create_agent(opt, requireModelExists=True)

    first_runs: list[dict[str, Any]] = []
    next_runs: list[dict[str, Any]] = []
    for item in load_subset(Path(args.subset)):
        brief = get_brief(item)
        first_prompt = build_light_opening_prompt(item)
        request_start = time.time()
        agent.observe(Message({"text": first_prompt, "episode_done": False}))
        reply = agent.act()
        first_ts = time.time()
        text = str(reply.get("text", "")).strip()
        scene_setup, player_state = split_scene_and_state(text, str(brief["theme_en"]))
        actions = build_actions(item, text)
        first_run = normalize_playable_response(
            baseline_id="light",
            benchmark_id=item["benchmark_id"],
            raw_output=simplify_reply(reply),
            scene_setup=scene_setup,
            player_state=player_state,
            narrative_response=text,
            candidate_actions=actions,
            supports_next_turn=True,
            request_start_ts=request_start,
            first_playable_ts=first_ts,
            finish_ts=first_ts,
            notes=[
                "Uses ParlAI-hosted dodecadialogue/light_dialog_ft checkpoint associated with the LIGHT project.",
                "Adapter adds minimal playable action choices for DN-style latency comparison.",
            ],
        )
        first_run["mode"] = "first_playable"
        first_run["input_bundle"] = {"theme": item.get("theme", ""), "theme_en": brief["theme_en"], "prompt": first_prompt}
        first_runs.append(first_run)

        next_prompt = build_light_next_turn_prompt(item, first_run["normalized_response"], actions[0])
        next_request_start = time.time()
        agent.observe(Message({"text": next_prompt, "episode_done": False}))
        next_reply = agent.act()
        next_ts = time.time()
        next_text = str(next_reply.get("text", "")).strip()
        next_scene_setup, next_player_state = split_scene_and_state(next_text, str(brief["theme_en"]))
        next_actions = build_actions(item, next_text)
        next_run = normalize_playable_response(
            baseline_id="light",
            benchmark_id=item["benchmark_id"],
            raw_output=simplify_reply(next_reply),
            scene_setup=next_scene_setup,
            player_state=next_player_state,
            narrative_response=next_text,
            candidate_actions=next_actions,
            supports_next_turn=True,
            request_start_ts=next_request_start,
            first_playable_ts=next_ts,
            finish_ts=next_ts,
            notes=[
                "Second turn generated from the same LIGHT checkpoint under the shared playable protocol.",
                f"Player action fed back: {actions[0]}",
            ],
        )
        next_run["mode"] = "next_turn"
        next_run["input_bundle"] = {"theme": item.get("theme", ""), "theme_en": brief["theme_en"], "player_action": actions[0], "prompt": next_prompt}
        next_runs.append(next_run)

    payload = {"runs": first_runs + next_runs}
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    write_csv(Path(args.output_csv), first_runs + next_runs)

    summary = {
        "baseline_id": "light",
        "first_playable": summarize_playable_runs("light", first_runs, "first_playable"),
        "next_turn": summarize_playable_runs("light", next_runs, "next_turn"),
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
