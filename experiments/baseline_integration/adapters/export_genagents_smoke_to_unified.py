from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[3]
    src = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "1_table1_main_visual_efficiency"
        / "baselines"
        / "baseline_genagents"
        / "raw_runs"
        / "genagents_smoke_2026-04-25.json"
    )
    dst = (
        repo_root
        / "experiments"
        / "baseline_integration"
        / "normalized_runs"
        / "genagents_smoke_2026-04-25.normalized.json"
    )

    payload = json.loads(src.read_text(encoding="utf-8"))
    subset_items = payload.get("benchmark_subset", {}).get("items", [])

    normalized = {
        "baseline_id": "genagents",
        "run_id": "genagents_smoke_2026-04-25",
        "mode": "text_planning_smoke",
        "input_bundle": {
            "benchmark_source": payload.get("benchmark_subset", {}).get("benchmark_source"),
            "subset_name": payload.get("benchmark_subset", {}).get("subset_name"),
            "sample_size": payload.get("benchmark_subset", {}).get("sample_size"),
            "benchmark_ids": [item.get("benchmark_id") for item in subset_items],
        },
        "agent_profile": {
            "agent_fullname": payload.get("loader_smoke", {}).get("agent_fullname"),
            "scratch_key_count": len(payload.get("loader_smoke", {}).get("scratch_keys", [])),
            "memory_node_count": payload.get("loader_smoke", {}).get("memory_node_count"),
        },
        "raw_output": payload,
        "success": bool(payload.get("loader_smoke", {}).get("loaded")),
        "latency_s": payload.get("elapsed_s"),
        "failure_reason": payload.get("active_inference", {}).get("blocked_reason"),
        "notes": [
            "Loader smoke passed.",
            "Live model response is credential-gated.",
            "Use this normalized run for integration testing, not final scored comparison.",
        ],
    }

    dst.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote normalized run to: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
