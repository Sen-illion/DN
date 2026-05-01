import argparse
import base64
import csv
import io
import json
import os
import re
import statistics
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from PIL import Image


DIMENSIONS = [
    "semantic_alignment",
    "character_consistency",
    "scene_object_fidelity",
    "style_lighting_consistency",
    "detail_completeness",
    "overall_quality",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM vision evaluation for baseline images versus DN reference images.")
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--baseline", default="sdm_v2")
    parser.add_argument("--eval_name", default="llm_eval")
    parser.add_argument("--model", default="")
    parser.add_argument("--base_url", default="")
    parser.add_argument("--api_key_env", default="Camera_Analyst_API_KEY")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--max_image_side", type=int, default=768)
    parser.add_argument("--timeout", type=int, default=180)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def image_data_url(path: Path, max_side: int) -> str:
    image = Image.open(path).convert("RGB")
    image.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def extract_message_text(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise ValueError(f"Missing choices in response: {json.dumps(body, ensure_ascii=False)[:500]}")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(part for part in parts if part).strip()
    return str(content).strip()


def score_average(obj: dict[str, Any], prefix: str) -> float:
    values = []
    scores = obj.get(prefix, {})
    for dim in DIMENSIONS:
        raw = scores.get(dim)
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            pass
    return round(statistics.mean(values), 4) if values else 0.0


def normalize_score(value: Any) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 < number < 1:
        number *= 5
    return max(1, min(5, int(round(number))))


def normalize_scores(scores: dict[str, Any]) -> dict[str, int]:
    return {dim: normalize_score(scores.get(dim)) for dim in DIMENSIONS}


def evaluate_one(
    row: dict[str, Any],
    project_root: Path,
    endpoint: str,
    headers: dict[str, str],
    model: str,
    max_side: int,
    timeout: int,
) -> dict[str, Any]:
    baseline_image = project_root / row["baseline_image_path"]
    dn_image = project_root / row["dn_reference_image"]
    text_prompt = row["text_prompt"][:1200]

    system = (
        "You are a strict multimodal research evaluator. Return one compact JSON object only."
    )
    user_text = {
        "type": "text",
        "text": (
            "Evaluate two images for the same text prompt. Image A is the DN reference result. "
            "Image B is the baseline-generated result. The baseline was generated from text only. "
            "Do not assume either image is correct; score both independently against the text.\n\n"
            f"TEXT PROMPT:\n{text_prompt}\n\n"
            "Use integer scores from 1 to 5 only, where 5 is best. Keep the summary under 18 words.\n"
            "Return exactly this JSON shape and nothing else:\n"
            "{"
            "\"dn_scores\":{\"semantic_alignment\":5,\"character_consistency\":5,\"scene_object_fidelity\":5,"
            "\"style_lighting_consistency\":5,\"detail_completeness\":5,\"overall_quality\":5},"
            "\"baseline_scores\":{\"semantic_alignment\":5,\"character_consistency\":5,\"scene_object_fidelity\":5,"
            "\"style_lighting_consistency\":5,\"detail_completeness\":5,\"overall_quality\":5},"
            "\"winner\":\"dn|baseline|tie\","
            "\"summary\":\"short phrase\""
            "}"
        ),
    }
    content = [
        user_text,
        {"type": "text", "text": "Image A: DN reference."},
        {"type": "image_url", "image_url": {"url": image_data_url(dn_image, max_side)}},
        {"type": "text", "text": "Image B: baseline result."},
        {"type": "image_url", "image_url": {"url": image_data_url(baseline_image, max_side)}},
    ]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "temperature": 0,
        "max_tokens": 260,
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    text = extract_message_text(body)
    if not text:
        raise ValueError(f"Empty model content: {json.dumps(body, ensure_ascii=False)[:500]}")
    parsed = extract_json(text)
    dn_scores = normalize_scores(parsed.get("dn_scores", {}))
    baseline_scores = normalize_scores(parsed.get("baseline_scores", {}))
    return {
        **row,
        "eval_status": "success",
        "dn_scores": dn_scores,
        "baseline_scores": baseline_scores,
        "dn_average": round(statistics.mean(dn_scores.values()), 4),
        "baseline_average": round(statistics.mean(baseline_scores.values()), 4),
        "delta_baseline_minus_dn": round(
            statistics.mean(baseline_scores.values()) - statistics.mean(dn_scores.values()), 4
        ),
        "winner": parsed.get("winner", ""),
        "summary": parsed.get("summary", ""),
        "eval_model": model,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    flat_rows: list[dict[str, Any]] = []
    for row in rows:
        flat = {k: v for k, v in row.items() if k not in ("dn_scores", "baseline_scores")}
        for prefix in ("dn_scores", "baseline_scores"):
            for dim, value in (row.get(prefix) or {}).items():
                flat[f"{prefix}.{dim}"] = value
        flat_rows.append(flat)
    if not flat_rows:
        return
    fields = sorted({key for row in flat_rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat_rows)


def main() -> None:
    load_dotenv(".env")
    args = parse_args()
    run_dir = Path(args.run_dir)
    project_root = Path.cwd()
    model = args.model or os.getenv("Camera_Analyst_MODEL") or os.getenv("VISION_REF_MODEL")
    base_url = (args.base_url or os.getenv("Camera_Analyst_BASE_URL") or os.getenv("VISION_REF_BASE_URL") or "").rstrip("/")
    api_key = os.getenv(args.api_key_env) or os.getenv("VISION_REF_API_KEY")
    if not model or not base_url or not api_key:
        raise SystemExit("Missing model/base_url/api key for LLM vision evaluation.")

    endpoint = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    index = run_dir / "indexes" / "baseline_dataset_index.jsonl"
    rows = [
        row
        for row in read_jsonl(index)
        if row["baseline_name"] == args.baseline
        and row["generation_status"] == "success"
        and row["dn_reference_image_exists"]
    ]
    if args.limit:
        rows = rows[: args.limit]

    out_dir = run_dir / "eval" / args.baseline / args.eval_name
    out_path = out_dir / "llm_eval_results.jsonl"
    fail_path = out_dir / "llm_eval_failures.jsonl"
    completed = {row["id"] if "id" in row else f"{row['game_id']}/seg_{int(row['segment_index']):03d}" for row in read_jsonl(out_path)}
    failed_ids = {
        row["id"] if "id" in row else f"{row['game_id']}/seg_{int(row['segment_index']):03d}"
        for row in read_jsonl(fail_path)
    }

    for row in rows:
        row_id = f"{row['game_id']}/seg_{int(row['segment_index']):03d}"
        if row_id in completed:
            continue
        try:
            result = evaluate_one(row, project_root, endpoint, headers, model, args.max_image_side, args.timeout)
            result["id"] = row_id
            append_jsonl(out_path, result)
            print(f"ok {row_id} baseline_avg={result['baseline_average']} dn_avg={result['dn_average']}")
        except Exception as exc:
            fail = {**row, "id": row_id, "eval_status": "failed", "error": repr(exc), "eval_model": model}
            if row_id not in failed_ids:
                append_jsonl(fail_path, fail)
                failed_ids.add(row_id)
            print(f"failed {row_id}: {exc}")
        time.sleep(args.sleep)

    results = read_jsonl(out_path)
    write_csv(out_dir / "llm_eval_results.csv", results)
    failures = read_jsonl(fail_path)
    summary = {
        "baseline": args.baseline,
        "model": model,
        "eligible_pairs": len(rows),
        "evaluated_pairs": len(results),
        "failed_eval_calls": len(failures),
        "dn_average": round(statistics.mean([r["dn_average"] for r in results]), 4) if results else 0,
        "baseline_average": round(statistics.mean([r["baseline_average"] for r in results]), 4) if results else 0,
    }
    summary["delta_baseline_minus_dn"] = round(summary["baseline_average"] - summary["dn_average"], 4)
    (out_dir / "llm_eval_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
