from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    repo_root = script_path.parents[6]
    external_repo = repo_root / "experiments" / "external_baselines" / "genagents"
    sample_agent_dir = external_repo / "agent_bank" / "populations" / "single_agent" / "01fd7d2a-0357-4c1b-9f3e-8eade2d537ae"
    subset_path = baseline_root / "protocol" / "genagents_smoke_subset_v1.json"
    out_path = baseline_root / "raw_runs" / "genagents_smoke_2026-04-25.json"

    sys.path.insert(0, str(external_repo))

    start = time.perf_counter()
    from genagents.genagents import GenerativeAgent

    agent = GenerativeAgent(str(sample_agent_dir))
    subset = load_json(subset_path)

    payload = {
        "baseline": "genagents",
        "date": "2026-04-25",
        "external_repo": str(external_repo),
        "sample_agent_dir": str(sample_agent_dir),
        "environment": {
            "python_utf8": os.getenv("PYTHONUTF8"),
            "openai_api_key_present": bool(os.getenv("OPENAI_API_KEY")),
            "genagents_model": os.getenv("GENAGENTS_MODEL", "gpt-4o-mini"),
        },
        "loader_smoke": {
            "loaded": bool(getattr(agent, "scratch", None)),
            "agent_fullname": agent.get_fullname(),
            "scratch_keys": sorted(list(agent.scratch.keys())),
            "memory_node_count": len(agent.memory_stream.seq_nodes),
        },
        "benchmark_subset": subset,
        "active_inference": {
            "attempted": False,
            "success": None,
            "blocked_reason": None,
            "response_preview": None,
        },
        "elapsed_s": None,
    }

    if os.getenv("OPENAI_API_KEY"):
        t0 = time.perf_counter()
        response = agent.utterance([("Interviewer", "Tell me how you would react to a dangerous but uncertain new situation.")])
        payload["active_inference"] = {
            "attempted": True,
            "success": response is not None,
            "blocked_reason": None,
            "response_preview": str(response)[:500],
            "latency_s": round(time.perf_counter() - t0, 3),
        }
    else:
        payload["active_inference"] = {
            "attempted": False,
            "success": None,
            "blocked_reason": "OPENAI_API_KEY missing",
            "response_preview": None,
        }

    payload["elapsed_s"] = round(time.perf_counter() - start, 3)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote smoke result to: {out_path}")
    print(json.dumps(payload["loader_smoke"], ensure_ascii=False, indent=2))
    print(json.dumps(payload["active_inference"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
