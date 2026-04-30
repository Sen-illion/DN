from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[3]
    raw_path = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "1_table1_main_visual_efficiency"
        / "baselines"
        / "baseline_genagents"
        / "raw_runs"
        / "genagents_consistency_live_2026-04-26_dn_env_subset_v2.json"
    )
    judged_path = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "1_table1_main_visual_efficiency"
        / "baselines"
        / "baseline_genagents"
        / "summaries"
        / "genagents_consistency_judged_live_2026-04-26_dn_env_subset_v2.json"
    )
    dst = (
        repo_root
        / "experiments"
        / "baseline_integration"
        / "normalized_runs"
        / "genagents_consistency_live_2026-04-26_dn_env_subset_v2.normalized.json"
    )

    raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
    judged_payload = json.loads(judged_path.read_text(encoding="utf-8"))
    subset_items = raw_payload.get("subset", {}).get("items", [])
    turn_outputs = [turn for run in raw_payload.get("runs", []) for turn in run.get("turn_outputs", [])]
    blocked_runs = [
        {
            "benchmark_id": run.get("benchmark_id"),
            "blocked_turns": [
                {
                    "turn_index": turn.get("turn_index"),
                    "blocked_reason": turn.get("blocked_reason"),
                    "success": turn.get("success"),
                }
                for turn in run.get("turn_outputs", [])
                if not turn.get("success")
            ],
        }
        for run in raw_payload.get("runs", [])
        if not run.get("all_turns_success")
    ]

    normalized = {
        "baseline_id": "genagents",
        "run_id": raw_payload.get("run_id"),
        "mode": raw_payload.get("mode"),
        "input_bundle": {
            "benchmark_source": raw_payload.get("subset", {}).get("benchmark_source"),
            "subset_name": raw_payload.get("subset", {}).get("subset_name"),
            "sample_size": raw_payload.get("subset", {}).get("sample_size"),
            "turn_count": raw_payload.get("subset", {}).get("turn_count"),
            "benchmark_ids": [item.get("benchmark_id") for item in subset_items],
        },
        "agent_profile": raw_payload.get("agent_profile"),
        "raw_output": {
            "native_run": raw_payload,
            "judged_summary": judged_payload,
        },
        "success": not raw_payload.get("summary", {}).get("credential_blocked", False),
        "latency_s": judged_payload.get("latency_mean_s"),
        "failure_reason": None if not blocked_runs else "partial item failures present",
        "resource_usage": {
            "provider_base_url": raw_payload.get("environment", {}).get("openai_base_url"),
            "model": raw_payload.get("environment", {}).get("genagents_model"),
            "turn_latency_count": len([t for t in turn_outputs if isinstance(t.get("latency_s"), (int, float))]),
            "latency_p95_s": judged_payload.get("latency_p95_s"),
        },
        "notes": [
            "Normalized export for the current 8-item Table 2 GenAgents baseline run.",
            f"Item full success rate: {judged_payload.get('item_full_success_rate')}.",
            f"Blocked items: {[entry['benchmark_id'] for entry in blocked_runs]}.",
        ],
        "blocked_items": blocked_runs,
        "judged_metrics": judged_payload.get("judged_metrics"),
    }

    dst.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote normalized run to: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
