from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_error_message(message: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    cleaned = message
    if key:
        cleaned = cleaned.replace(key, "[REDACTED_API_KEY]")
    return cleaned


def find_benchmark_item(items: list[dict], benchmark_id: str) -> dict:
    for item in items:
        if item.get("benchmark_id") == benchmark_id:
            return item
    raise KeyError(f"benchmark item not found: {benchmark_id}")


def build_turn_prompts(item: dict) -> list[str]:
    theme = item["theme"]
    genre = item["expected_genre"]
    tone = item["expected_tone"]
    must = "；".join(item.get("must_have_constraints", []))
    forbidden = "；".join(item.get("forbidden_issues", []))
    return [
        f"你是故事中的当事人。背景主题是：{theme}。请先用第一人称说明你眼下所处的局面。风格应接近{genre}，语气保持{tone}。必须尽量满足这些约束：{must}。避免这些问题：{forbidden}。",
        f"延续刚才的情境，不要改掉你的身份和处境。请说明你接下来最想做的两件具体事情，并解释原因。仍然保持{genre}和{tone}。",
        f"继续保持同一人物和同一世界。现在出现新的不确定风险，请给出你的即时判断、行动优先级和一句简短自我反思。避免跳出{theme}的设定。",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", default="genagents_consistency_subset_v1.json")
    parser.add_argument("--output", default="genagents_consistency_2026-04-25_pending.json")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    repo_root = script_path.parents[6]
    external_repo = repo_root / "experiments" / "external_baselines" / "genagents"
    benchmark_path = repo_root / "experiments" / "benchmark" / "dn_quality_benchmark_v1.json"
    subset_path = baseline_root / "protocol" / args.subset
    sample_agent_dir = external_repo / "agent_bank" / "populations" / "single_agent" / "01fd7d2a-0357-4c1b-9f3e-8eade2d537ae"
    out_path = baseline_root / "raw_runs" / args.output

    sys.path.insert(0, str(external_repo))
    from simulation_engine.settings import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_VERS
    from genagents.genagents import GenerativeAgent

    benchmark = load_json(benchmark_path)
    subset = load_json(subset_path)
    agent = GenerativeAgent(str(sample_agent_dir))
    has_key = bool(OPENAI_API_KEY)
    all_items = benchmark.get("items", [])

    started = time.perf_counter()
    run_date = date.today().isoformat()
    runs = []
    for entry in subset.get("items", []):
        item = find_benchmark_item(all_items, entry["benchmark_id"])
        turn_prompts = build_turn_prompts(item)
        dialogues = []
        turn_outputs = []
        for idx, prompt in enumerate(turn_prompts, start=1):
            turn_record = {
                "turn_index": idx,
                "prompt": prompt,
                "success": None,
                "latency_s": None,
                "response": None,
                "blocked_reason": None,
            }
            if has_key:
                try:
                    t0 = time.perf_counter()
                    dialogues.append(("Interviewer", prompt))
                    response = agent.utterance(dialogues)
                    turn_record["latency_s"] = round(time.perf_counter() - t0, 3)
                    turn_record["response"] = response
                    turn_record["success"] = response is not None
                    dialogues.append((agent.get_fullname(), response))
                except Exception as exc:
                    turn_record["success"] = False
                    turn_record["blocked_reason"] = sanitize_error_message(f"{type(exc).__name__}: {exc}")
            else:
                turn_record["success"] = False
                turn_record["blocked_reason"] = "OPENAI_API_KEY missing"
            turn_outputs.append(turn_record)

        runs.append(
            {
                "benchmark_id": item["benchmark_id"],
                "theme": item["theme"],
                "expected_genre": item["expected_genre"],
                "expected_tone": item["expected_tone"],
                "must_have_constraints": item.get("must_have_constraints", []),
                "forbidden_issues": item.get("forbidden_issues", []),
                "focus": entry.get("focus"),
                "turn_count": len(turn_outputs),
                "turn_outputs": turn_outputs,
                "all_turns_success": all(t["success"] for t in turn_outputs),
            }
        )

    payload = {
        "baseline": "genagents",
        "run_id": out_path.stem,
        "date": run_date,
        "mode": "3_turn_consistency",
        "environment": {
            "openai_api_key_present": has_key,
            "openai_base_url": OPENAI_BASE_URL,
            "genagents_model": LLM_VERS,
        },
        "agent_profile": {
            "agent_fullname": agent.get_fullname(),
            "memory_node_count": len(agent.memory_stream.seq_nodes),
        },
        "subset": subset,
        "runs": runs,
        "summary": {
            "sample_size": len(runs),
            "turn_count": subset.get("turn_count", 3),
            "full_success_count": sum(1 for r in runs if r["all_turns_success"]),
            "full_success_rate": round(sum(1 for r in runs if r["all_turns_success"]) / len(runs), 3) if runs else 0.0,
            "credential_blocked": not has_key,
            "elapsed_s": round(time.perf_counter() - started, 3),
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote consistency run to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
