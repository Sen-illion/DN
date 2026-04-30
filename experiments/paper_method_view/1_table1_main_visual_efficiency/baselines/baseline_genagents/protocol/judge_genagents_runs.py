from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

import openai


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_env_file(repo_root: Path) -> None:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def make_client() -> tuple[openai.OpenAI, str]:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    load_env_file(repo_root)

    api_key = (
        os.getenv("GENAGENTS_API_KEY")
        or os.getenv("Camera_Analyst_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        raise RuntimeError("No API key found for GenAgents judging.")

    base_url = (
        os.getenv("GENAGENTS_BASE_URL")
        or os.getenv("Camera_Analyst_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
    )
    judge_model = (
        os.getenv("GENAGENTS_JUDGE_MODEL")
        or os.getenv("BASELINE_JUDGE_MODEL")
        or os.getenv("Camera_Analyst_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    )

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return openai.OpenAI(**kwargs), judge_model


def json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def extract_json_block(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("{") and part.endswith("}"):
                raw = part
                break
            if part.startswith("json"):
                candidate = part[4:].strip()
                if candidate.startswith("{") and candidate.endswith("}"):
                    raw = candidate
                    break
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Judge response did not contain JSON: {text[:300]}")
    return json.loads(raw[start : end + 1])


def build_conversation_bundle(run: dict[str, Any]) -> str:
    lines: list[str] = []
    for turn in run.get("turn_outputs", []):
        lines.extend(
            [
                f"Turn {turn.get('turn_index')} success: {turn.get('success')}",
                f"Turn {turn.get('turn_index')} prompt:",
                turn.get("prompt") or "",
                f"Turn {turn.get('turn_index')} response:",
                turn.get("response") or f"[BLOCKED] {turn.get('blocked_reason')}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_messages(run: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, str]]:
    rubric = {
        "theme_alignment_1to5": "Whether the response bundle stays inside the intended theme, genre, tone, and scenario pressure.",
        "setting_adherence_1to5": "Whether must-have scenario constraints are actually reflected in the content, not merely adjacent in spirit.",
        "persona_consistency_1to5": "Whether the same narrator identity, motivations, and viewpoint remain stable across turns.",
        "multi_turn_coherence_1to5": "Whether later turns logically continue earlier turns without contradiction or abrupt reset.",
        "actionability_1to5": "Whether the bundle gives concrete, usable decisions, priorities, or next actions under the scenario.",
        "major_error_0or1": "1 if there is a serious failure such as blocked turn, obvious derailment, broken formatting, or severe off-theme behavior; otherwise 0.",
    }

    agent_profile = payload.get("agent_profile", {})
    conversation_bundle = build_conversation_bundle(run)
    user_payload = {
        "agent_fullname": agent_profile.get("agent_fullname"),
        "benchmark_id": run.get("benchmark_id"),
        "theme": run.get("theme"),
        "expected_genre": run.get("expected_genre"),
        "expected_tone": run.get("expected_tone"),
        "focus": run.get("focus"),
        "must_have_constraints": run.get("must_have_constraints", []),
        "forbidden_issues": run.get("forbidden_issues", []),
        "conversation_bundle": conversation_bundle,
    }

    system_prompt = (
        "You are a strict research evaluator for interactive narrative baselines. "
        "Score the run using only the provided evidence. Penalize blocked turns, contradictions, weak actionability, "
        "or failure to stay inside the scenario. Return JSON only."
    )
    user_prompt = (
        "Evaluate the following GenAgents run.\n\n"
        "Rubric fields:\n"
        f"{json_dumps(rubric)}\n\n"
        "Scoring rules:\n"
        "- Every score must be an integer from 1 to 5.\n"
        "- Use 5 only when the evidence is strongly convincing.\n"
        "- If any turn is blocked or missing, multi_turn_coherence_1to5 must be at most 3 and major_error_0or1 should usually be 1.\n"
        "- setting_adherence_1to5 should reflect the must-have constraints, scenario grounding, and forbidden-issue avoidance.\n"
        "- Keep rationales concise and evidence-based.\n\n"
        "Return exactly this JSON schema:\n"
        "{\n"
        '  "theme_alignment_1to5": 0,\n'
        '  "setting_adherence_1to5": 0,\n'
        '  "persona_consistency_1to5": 0,\n'
        '  "multi_turn_coherence_1to5": 0,\n'
        '  "actionability_1to5": 0,\n'
        '  "major_error_0or1": 0,\n'
        '  "rationales": {\n'
        '    "theme_alignment": "",\n'
        '    "setting_adherence": "",\n'
        '    "persona_consistency": "",\n'
        '    "multi_turn_coherence": "",\n'
        '    "actionability": ""\n'
        "  },\n"
        '  "overall_comment": ""\n'
        "}\n\n"
        f"Run evidence:\n{json_dumps(user_payload)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def judge_one_run(client: openai.OpenAI, model: str, run: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(run, payload),
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    judged = extract_json_block(content)
    judged["judge_model"] = model
    judged["judge_raw_response"] = content
    return judged


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    theme_scores = [float(row["theme_alignment_1to5"]) for row in rows]
    setting_scores = [float(row["setting_adherence_1to5"]) for row in rows]
    persona_scores = [float(row["persona_consistency_1to5"]) for row in rows]
    coherence_scores = [float(row["multi_turn_coherence_1to5"]) for row in rows]
    actionability_scores = [float(row["actionability_1to5"]) for row in rows]
    error_flags = [float(row["major_error_0or1"]) for row in rows]
    return {
        "theme_alignment_mean_1to5": mean(theme_scores),
        "setting_adherence_mean_1to5": mean(setting_scores),
        "persona_consistency_mean_1to5": mean(persona_scores),
        "multi_turn_coherence_mean_1to5": mean(coherence_scores),
        "actionability_mean_1to5": mean(actionability_scores),
        "major_error_rate": mean(error_flags),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-raw", default="genagents_consistency_live_2026-04-26_dn_env.json")
    parser.add_argument("--input-summary", default="genagents_consistency_live_summary_2026-04-26_dn_env.json")
    parser.add_argument("--output-json", default="genagents_consistency_judged_live_2026-04-26_dn_env.json")
    parser.add_argument("--output-csv", default="genagents_consistency_judged_live_2026-04-26_dn_env.csv")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    baseline_root = script_path.parents[1]
    raw_payload = load_json(baseline_root / "raw_runs" / args.input_raw)
    existing_summary = load_json(baseline_root / "summaries" / args.input_summary)

    client, judge_model = make_client()
    rows: list[dict[str, Any]] = []

    for run in raw_payload.get("runs", []):
        judged = judge_one_run(client, judge_model, run, raw_payload)
        rows.append(
            {
                "benchmark_id": run.get("benchmark_id"),
                "theme": run.get("theme"),
                "focus": run.get("focus"),
                "all_turns_success": run.get("all_turns_success"),
                "theme_alignment_1to5": judged["theme_alignment_1to5"],
                "setting_adherence_1to5": judged["setting_adherence_1to5"],
                "persona_consistency_1to5": judged["persona_consistency_1to5"],
                "multi_turn_coherence_1to5": judged["multi_turn_coherence_1to5"],
                "actionability_1to5": judged["actionability_1to5"],
                "major_error_0or1": judged["major_error_0or1"],
                "overall_comment": judged.get("overall_comment", ""),
                "theme_alignment_rationale": judged.get("rationales", {}).get("theme_alignment", ""),
                "setting_adherence_rationale": judged.get("rationales", {}).get("setting_adherence", ""),
                "persona_consistency_rationale": judged.get("rationales", {}).get("persona_consistency", ""),
                "multi_turn_coherence_rationale": judged.get("rationales", {}).get("multi_turn_coherence", ""),
                "actionability_rationale": judged.get("rationales", {}).get("actionability", ""),
            }
        )

    aggregate = summarize_rows(rows)
    judged_summary = {
        "baseline": "genagents",
        "run_id": raw_payload.get("run_id"),
        "benchmark_set": raw_payload.get("subset", {}).get("subset_name"),
        "source_raw_run": args.input_raw,
        "source_summary": args.input_summary,
        "sample_size": existing_summary.get("sample_size"),
        "turn_total": existing_summary.get("turn_total"),
        "turn_success_rate": existing_summary.get("turn_success_rate"),
        "item_full_success_rate": existing_summary.get("item_full_success_rate"),
        "latency_mean_s": existing_summary.get("latency_mean_s"),
        "latency_p95_s": existing_summary.get("latency_p95_s"),
        "credential_blocked": existing_summary.get("credential_blocked"),
        "judge_model": judge_model,
        "judge_method": "LLM rubric scoring over full 3-turn conversation bundle, scenario constraints, and failure markers.",
        "judged_metrics": aggregate,
        "per_item": rows,
        "notes": [
            "Judge-based scores replace the earlier heuristic placeholder for paper-facing comparison use.",
            "This judged file should be cited instead of the heuristic-only live summary when discussing quality dimensions.",
        ],
    }

    json_path = baseline_root / "summaries" / args.output_json
    csv_path = baseline_root / "summaries" / args.output_csv
    json_path.write_text(json.dumps(judged_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["benchmark_id"])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    print(f"Wrote judged summary json to: {json_path}")
    print(f"Wrote judged per-item csv to: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
