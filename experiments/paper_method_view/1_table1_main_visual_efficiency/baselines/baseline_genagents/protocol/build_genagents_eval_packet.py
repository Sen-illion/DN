from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="genagents_consistency_2026-04-25_pending.json")
    parser.add_argument("--output-csv", default="genagents_eval_packet_2026-04-25.csv")
    parser.add_argument("--output-md", default="genagents_eval_packet_2026-04-25.md")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    raw_path = baseline_root / "raw_runs" / args.input
    payload = load_json(raw_path)

    csv_path = baseline_root / "summaries" / args.output_csv
    md_path = baseline_root / "summaries" / args.output_md

    rows = []
    md_lines = [
        "# GenAgents Eval Packet",
        "",
        f"- baseline: `genagents`",
        f"- run_id: `{payload.get('run_id')}`",
        f"- credential_blocked: `{payload.get('summary', {}).get('credential_blocked')}`",
        "",
        "## Rating suggestion",
        "- theme_alignment_1to5",
        "- persona_consistency_1to5",
        "- multi_turn_coherence_1to5",
        "- actionability_1to5",
        "- major_error_0or1",
        "- comment",
        "",
    ]

    for run in payload.get("runs", []):
        joined_response = "\n\n".join(
            f"Turn {t['turn_index']} prompt:\n{t.get('prompt')}\n\nTurn {t['turn_index']} response:\n{t.get('response') or '[BLOCKED] ' + str(t.get('blocked_reason'))}"
            for t in run.get("turn_outputs", [])
        )
        rows.append(
            {
                "benchmark_id": run.get("benchmark_id"),
                "theme": run.get("theme"),
                "expected_genre": run.get("expected_genre"),
                "expected_tone": run.get("expected_tone"),
                "focus": run.get("focus"),
                "agent_fullname": payload.get("agent_profile", {}).get("agent_fullname"),
                "turn_count": run.get("turn_count"),
                "theme_alignment_1to5": "",
                "persona_consistency_1to5": "",
                "multi_turn_coherence_1to5": "",
                "actionability_1to5": "",
                "major_error_0or1": "",
                "comment": "",
                "conversation_bundle": joined_response,
            }
        )

        md_lines.extend(
            [
                f"## {run.get('benchmark_id')} - {run.get('theme')}",
                f"- genre: {run.get('expected_genre')}",
                f"- tone: {run.get('expected_tone')}",
                f"- focus: {run.get('focus')}",
                "",
                "### Turn bundle",
                "```text",
                joined_response,
                "```",
                "",
            ]
        )

    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["benchmark_id"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote eval packet csv to: {csv_path}")
    print(f"Wrote eval packet md to: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
