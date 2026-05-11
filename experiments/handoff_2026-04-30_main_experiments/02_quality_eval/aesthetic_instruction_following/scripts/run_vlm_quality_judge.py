# -*- coding: utf-8 -*-
"""Run VLM-as-judge scoring for formal20 visual quality.

The script evaluates existing images only. It never regenerates images.
It uses OpenAI-compatible Chat Completions by default:

    $env:OPENAI_API_KEY="..."
    python run_vlm_quality_judge.py --mode both --judge-model gpt-4.1

Use --validate-only to check the manifest and output paths without making API calls.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[5]
PKG_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = PKG_DIR / "results"
PROMPTS_DIR = PKG_DIR / "prompts"

MANIFEST_PATH = RESULTS_DIR / "quality_eval_manifest_formal20_v1.jsonl"
GROUPS_PATH = RESULTS_DIR / "quality_eval_groups_formal20_v1.json"
INSTRUCTION_OUT = RESULTS_DIR / "per_image_instruction_following_scores.jsonl"
AESTHETIC_OUT = RESULTS_DIR / "per_group_aesthetic_consistency_scores.jsonl"

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"

INSTRUCTION_SCHEMA = {
    "theme_alignment": "integer 1-5",
    "text_image_alignment": "integer 1-5",
    "style_following": "integer 1-5",
    "constraint_coverage": "integer 1-5",
    "forbidden_violation": "integer 1-5, where 5 means no violation",
    "instruction_following_score": "integer 1-5 holistic score",
    "failure_tags": "array of short strings",
    "reason": "short evidence-based explanation",
}

AESTHETIC_SCHEMA = {
    "style_lighting_consistency": "integer 1-5",
    "subject_attribute_consistency": "integer 1-5",
    "scene_world_consistency": "integer 1-5",
    "composition_quality": "integer 1-5",
    "artifact_rate": "integer 1-5, where 5 means no meaningful artifacts",
    "aesthetic_consistency_score": "integer 1-5 holistic score",
    "failure_tags": "array of short strings",
    "reason": "short evidence-based explanation",
}


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_done_ids(path: Path, key: str) -> set[str]:
    if not path.is_file():
        return set()
    return {row.get(key, "") for row in read_jsonl(path) if row.get(key)}


def repo_abs(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def image_data_url(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def system_prompt() -> str:
    path = PROMPTS_DIR / "vlm_judge_system_prompt.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return (
        "You are a strict visual-quality judge for a research benchmark. "
        "Score only what is visible in the images and return valid JSON only."
    )


def compact_context(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "system": rec["system"],
        "output_scope": rec["output_scope"],
        "benchmark_id": rec["benchmark_id"],
        "turn_type": rec["turn_type"],
        "theme": rec.get("theme", ""),
        "expected_genre": rec.get("expected_genre", ""),
        "expected_tone": rec.get("expected_tone", ""),
        "image_style": rec.get("image_style", {}),
        "must_have_constraints": rec.get("must_have_constraints", []),
        "forbidden_issues": rec.get("forbidden_issues", []),
        "scene_text": rec.get("scene_text", "")[:2500],
        "generation_prompt": rec.get("generation_prompt", "")[:2500],
    }


def call_chat_completion(
    *,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_retries: int,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_error: Optional[BaseException] = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(OPENAI_CHAT_URL, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return json.loads(content)
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"judge request failed after retries: {last_error}")


def instruction_messages(rec: Dict[str, Any]) -> List[Dict[str, Any]]:
    image_path = repo_abs(rec["image_path"])
    prompt = {
        "task": "score_instruction_following_theme_alignment_for_one_image",
        "score_range": "1=failed, 2=mostly wrong, 3=usable with clear issues, 4=mostly correct, 5=excellent",
        "required_json_schema": INSTRUCTION_SCHEMA,
        "record": compact_context(rec),
    }
    return [
        {"role": "system", "content": system_prompt()},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": json.dumps(prompt, ensure_ascii=False)},
                {"type": "image_url", "image_url": {"url": image_data_url(image_path), "detail": "low"}},
            ],
        },
    ]


def aesthetic_messages(group_key: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prompt = {
        "task": "score_aesthetic_consistency_for_images_from_one_system_and_one_benchmark",
        "group_key": group_key,
        "score_range": "1=failed, 2=mostly inconsistent, 3=usable with clear issues, 4=mostly consistent, 5=excellent",
        "required_json_schema": AESTHETIC_SCHEMA,
        "records": [compact_context(rec) for rec in records],
    }
    content: List[Dict[str, Any]] = [{"type": "text", "text": json.dumps(prompt, ensure_ascii=False)}]
    for rec in records:
        content.append({"type": "text", "text": f"Image for sample_id={rec['sample_id']} turn_type={rec['turn_type']}"})
        content.append({
            "type": "image_url",
            "image_url": {"url": image_data_url(repo_abs(rec["image_path"])), "detail": "low"},
        })
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": content},
    ]


def validate_paths(records: Iterable[Dict[str, Any]]) -> int:
    missing = []
    for rec in records:
        if not repo_abs(rec["image_path"]).is_file():
            missing.append(rec["sample_id"])
    if missing:
        print(f"Missing images: {len(missing)}", file=sys.stderr)
        for sample_id in missing[:20]:
            print(f"  {sample_id}", file=sys.stderr)
    else:
        print("Manifest image paths are valid.")
    return len(missing)


def run_instruction(args: argparse.Namespace, records: List[Dict[str, Any]], api_key: str) -> None:
    done = load_done_ids(INSTRUCTION_OUT, "sample_id") if args.resume else set()
    todo = [rec for rec in records if rec["sample_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    for idx, rec in enumerate(todo, start=1):
        score = call_chat_completion(
            api_key=api_key,
            model=args.judge_model,
            messages=instruction_messages(rec),
            temperature=args.temperature,
            max_retries=args.max_retries,
        )
        append_jsonl(INSTRUCTION_OUT, {
            "sample_id": rec["sample_id"],
            "system": rec["system"],
            "benchmark_id": rec["benchmark_id"],
            "turn_type": rec["turn_type"],
            "judge_model": args.judge_model,
            "judge_id": args.judge_id,
            **score,
        })
        print(f"[instruction {idx}/{len(todo)}] {rec['sample_id']}")


def run_aesthetic(args: argparse.Namespace, records: List[Dict[str, Any]], api_key: str) -> None:
    by_id = {rec["sample_id"]: rec for rec in records}
    groups = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    done = load_done_ids(AESTHETIC_OUT, "group_key") if args.resume else set()
    todo = [(key, [by_id[sid] for sid in sample_ids if sid in by_id]) for key, sample_ids in groups.items() if key not in done]
    todo = [(key, recs) for key, recs in todo if recs]
    if args.limit:
        todo = todo[: args.limit]
    for idx, (key, recs) in enumerate(todo, start=1):
        score = call_chat_completion(
            api_key=api_key,
            model=args.judge_model,
            messages=aesthetic_messages(key, recs),
            temperature=args.temperature,
            max_retries=args.max_retries,
        )
        system, benchmark_id = key.split("::", 1)
        append_jsonl(AESTHETIC_OUT, {
            "group_key": key,
            "system": system,
            "benchmark_id": benchmark_id,
            "sample_ids": [rec["sample_id"] for rec in recs],
            "judge_model": args.judge_model,
            "judge_id": args.judge_id,
            **score,
        })
        print(f"[aesthetic {idx}/{len(todo)}] {key}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["instruction", "aesthetic", "both"], default="both")
    parser.add_argument("--judge-model", default=os.getenv("VLM_JUDGE_MODEL", "gpt-4.1"))
    parser.add_argument("--judge-id", default=os.getenv("VLM_JUDGE_ID", "judge1"))
    parser.add_argument("--limit", type=int, default=0, help="Limit items/groups for smoke tests.")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", dest="resume", action="store_false")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-retries", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = read_jsonl(MANIFEST_PATH)
    missing = validate_paths(records)
    if missing:
        return 1
    if args.validate_only:
        print(f"Validation-only complete: {len(records)} manifest records.")
        return 0
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set. Use --validate-only or fill the human rating template.", file=sys.stderr)
        return 2
    if args.mode in {"instruction", "both"}:
        run_instruction(args, records, api_key)
    if args.mode in {"aesthetic", "both"}:
        run_aesthetic(args, records, api_key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
