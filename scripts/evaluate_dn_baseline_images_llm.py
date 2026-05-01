import argparse
import base64
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests
from PIL import Image


DIMENSIONS = [
    "text_image_semantic_consistency",
    "subject_character_consistency",
    "scene_key_object_fidelity",
    "style_lighting_consistency",
    "detail_completeness",
    "overall_quality",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate DN reference images against text-only image baselines with a vision LLM.")
    parser.add_argument("--run_dir", required=True)
    parser.add_argument("--dn_root", default="DN-experiment-2.0")
    parser.add_argument("--baselines", nargs="+", default=["SDM-v2", "StoryDiffusion", "IC-LoRA"])
    parser.add_argument("--model", default=None, help="Override VISION_REF_MODEL/COHERENCE model from .env.")
    parser.add_argument("--base_url", default=None, help="Override VISION_REF_BASE_URL/COHERENCE_BASE_URL from .env.")
    parser.add_argument("--api_key", default=None, help="Override API key; prefer env/.env instead of passing this.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--max_prompt_chars", type=int, default=4000)
    parser.add_argument("--image_max_side", type=int, default=768)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_dotenv(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def resolve_config(args: argparse.Namespace) -> Dict[str, str]:
    dotenv = load_dotenv(Path(".env"))
    api_key = args.api_key or os.environ.get("VISION_REF_API_KEY") or dotenv.get("VISION_REF_API_KEY")
    api_key = api_key or os.environ.get("COHERENCE_API_KEY") or dotenv.get("COHERENCE_API_KEY")
    base_url = args.base_url or os.environ.get("VISION_REF_BASE_URL") or dotenv.get("VISION_REF_BASE_URL")
    base_url = base_url or os.environ.get("COHERENCE_BASE_URL") or dotenv.get("COHERENCE_BASE_URL") or "https://api.openai.com/v1"
    model = args.model or os.environ.get("VISION_REF_MODEL") or dotenv.get("VISION_REF_MODEL")
    model = model or os.environ.get("COHERENCE_MODEL") or dotenv.get("CHAIRMAN_MODEL") or "gpt-4o"
    if not api_key:
        raise RuntimeError("No vision LLM API key found. Set VISION_REF_API_KEY, COHERENCE_API_KEY, or .env equivalents.")
    return {"api_key": api_key, "base_url": base_url.rstrip("/"), "model": model}


def image_to_data_uri(path: Path, max_side: int) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((max_side, max_side))
        import io

        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def make_eval_prompt(text_prompt: str, baseline_name: str) -> str:
    dims = "\n".join(f"- {dim}: 1-5" for dim in DIMENSIONS)
    return (
        "You are a strict multimodal evaluator. Compare two generated images against the same text prompt. "
        "Image A is the DN reference result. Image B is the text-only baseline result. "
        "Do not reward either image for matching the other image directly; judge both against the text prompt and visual quality. "
        "Return only valid JSON.\n\n"
        f"Baseline name: {baseline_name}\n"
        f"Text prompt (possibly truncated): {text_prompt}\n\n"
        "Score Image A (DN) and Image B (baseline) on these dimensions:\n"
        f"{dims}\n\n"
        "Use integers or one-decimal floats from 1 to 5. Include concise reasons. JSON schema:\n"
        "{\n"
        '  "dn": {"text_image_semantic_consistency": 0, "subject_character_consistency": 0, "scene_key_object_fidelity": 0, "style_lighting_consistency": 0, "detail_completeness": 0, "overall_quality": 0, "reason": ""},\n'
        '  "baseline": {"text_image_semantic_consistency": 0, "subject_character_consistency": 0, "scene_key_object_fidelity": 0, "style_lighting_consistency": 0, "detail_completeness": 0, "overall_quality": 0, "reason": ""},\n'
        '  "winner": "dn|baseline|tie"\n'
        "}"
    )


def call_vision_llm(config: Dict[str, str], prompt: str, dn_image: Path, baseline_image: Path, args: argparse.Namespace) -> Dict[str, Any]:
    url = f"{config['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"}
    content = [
        {"type": "text", "text": prompt},
        {"type": "text", "text": "Image A: DN reference result"},
        {"type": "image_url", "image_url": {"url": image_to_data_uri(dn_image, args.image_max_side)}},
        {"type": "text", "text": "Image B: baseline result"},
        {"type": "image_url", "image_url": {"url": image_to_data_uri(baseline_image, args.image_max_side)}},
    ]
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,
        "max_tokens": 900,
    }
    last_error = None
    for attempt in range(args.retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
            data = response.json()
            message = data["choices"][0]["message"]["content"]
            if isinstance(message, list):
                message = "".join(part.get("text", "") for part in message if isinstance(part, dict))
            parsed = extract_json(str(message))
            return {"raw_response": message, "parsed": parsed}
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < args.retries:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last_error))


def score_mean(section: Dict[str, Any]) -> float | None:
    values = []
    for dim in DIMENSIONS:
        try:
            values.append(float(section[dim]))
        except Exception:
            pass
    return round(sum(values) / len(values), 4) if values else None


def build_generation_dataset(run_dir: Path, baselines: List[str]) -> List[Dict[str, Any]]:
    manifest = {row["id"]: row for row in load_jsonl(run_dir / "manifest" / "manifest.jsonl")}
    rows: List[Dict[str, Any]] = []
    for baseline in baselines:
        for row in load_jsonl(run_dir / baseline / "index.jsonl"):
            sid = row["id"]
            src = manifest.get(sid, {})
            metadata = row.get("metadata", {})
            status = row.get("status") or metadata.get("status") or "unknown"
            rows.append(
                {
                    "id": sid,
                    "baseline": baseline,
                    "theme_id": src.get("theme_id", ""),
                    "game_id": src.get("game_id", sid.split("/")[0]),
                    "segment_index": src.get("segment_index", ""),
                    "source_text_json": src.get("source_text_json", ""),
                    "text_prompt": src.get("text_prompt", row.get("prompt", "")),
                    "baseline_image_path": row.get("image_path") or "",
                    "dn_reference_image": src.get("dn_reference_image", ""),
                    "dn_reference_image_exists": src.get("dn_reference_image_exists", False),
                    "generation_status": status,
                    "generation_error": metadata.get("error", ""),
                }
            )
    return rows


def summarize(scores: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    by_baseline: Dict[str, List[Dict[str, Any]]] = {}
    by_theme: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for row in scores:
        by_baseline.setdefault(row["baseline"], []).append(row)
        by_theme.setdefault((row["baseline"], row["theme_id"]), []).append(row)

    baseline_rows = []
    for baseline, group in sorted(by_baseline.items()):
        baseline_rows.append(
            {
                "baseline": baseline,
                "evaluated_pairs": len(group),
                "dn_avg": round(sum(float(r["dn_avg"]) for r in group) / len(group), 4),
                "baseline_avg": round(sum(float(r["baseline_avg"]) for r in group) / len(group), 4),
                "delta_baseline_minus_dn": round(sum(float(r["delta_baseline_minus_dn"]) for r in group) / len(group), 4),
            }
        )

    theme_rows = []
    for (baseline, theme_id), group in sorted(by_theme.items()):
        theme_rows.append(
            {
                "baseline": baseline,
                "theme_id": theme_id,
                "evaluated_pairs": len(group),
                "dn_avg": round(sum(float(r["dn_avg"]) for r in group) / len(group), 4),
                "baseline_avg": round(sum(float(r["baseline_avg"]) for r in group) / len(group), 4),
                "delta_baseline_minus_dn": round(sum(float(r["delta_baseline_minus_dn"]) for r in group) / len(group), 4),
            }
        )
    return baseline_rows, theme_rows


def write_report(run_dir: Path, generation_rows: List[Dict[str, Any]], scores: List[Dict[str, Any]], baseline_summary: List[Dict[str, Any]], theme_summary: List[Dict[str, Any]], failures: List[Dict[str, Any]], config: Dict[str, str]) -> None:
    report = run_dir / "reports" / "baseline_vs_dn_report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    generated = {}
    for row in generation_rows:
        generated.setdefault(row["baseline"], {"success": 0, "total": 0})
        generated[row["baseline"]]["total"] += 1
        if row["generation_status"] == "success":
            generated[row["baseline"]]["success"] += 1

    lines = [
        "# DN Text-to-Image Baseline Comparison",
        "",
        f"- Run directory: `{run_dir.as_posix()}`",
        f"- Vision evaluator: `{config.get('model', 'unavailable')}` via `{config.get('base_url', 'unavailable')}`",
        "- Baseline generation used text prompts only. DN images were referenced only during evaluation.",
        "",
        "## Generation Coverage",
        "",
        "| Baseline | Successful images | Indexed rows |",
        "| --- | ---: | ---: |",
    ]
    for baseline, stats in sorted(generated.items()):
        lines.append(f"| {baseline} | {stats['success']} | {stats['total']} |")
    lines += ["", "## Average Scores", "", "| Baseline | Eval pairs | DN avg | Baseline avg | Delta |", "| --- | ---: | ---: | ---: | ---: |"]
    for row in baseline_summary:
        lines.append(
            f"| {row['baseline']} | {row['evaluated_pairs']} | {row['dn_avg']} | {row['baseline_avg']} | {row['delta_baseline_minus_dn']} |"
        )
    lines += ["", "## Theme Scores", "", "| Baseline | Theme | Eval pairs | DN avg | Baseline avg | Delta |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for row in theme_summary:
        lines.append(
            f"| {row['baseline']} | {row['theme_id']} | {row['evaluated_pairs']} | {row['dn_avg']} | {row['baseline_avg']} | {row['delta_baseline_minus_dn']} |"
        )
    lines += [
        "",
        "## Failures / Skips",
        "",
        f"- Evaluation/generation skip rows: {len(failures)}",
        "- Common skip reasons include missing DN reference images or baselines that only prepared manifests.",
        "",
        "Detailed files:",
        "",
        "- `reports/generation_dataset_index.jsonl`",
        "- `reports/llm_pairwise_scores.jsonl`",
        "- `reports/llm_pairwise_scores.csv`",
        "- `reports/summary_by_baseline.csv`",
        "- `reports/summary_by_theme.csv`",
        "- `reports/evaluation_failures.jsonl`",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    run_dir = Path(args.run_dir)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    config = resolve_config(args)

    generation_rows = build_generation_dataset(run_dir, args.baselines)
    write_jsonl(reports_dir / "generation_dataset_index.jsonl", generation_rows)
    write_csv(reports_dir / "generation_dataset_index.csv", generation_rows)

    scores: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    candidates = [
        row
        for row in generation_rows
        if row["generation_status"] == "success" and row["baseline_image_path"] and row["dn_reference_image_exists"]
    ]
    if args.limit is not None:
        candidates = candidates[: args.limit]

    for idx, row in enumerate(candidates, start=1):
        dn_image = Path(row["dn_reference_image"])
        baseline_image = Path(row["baseline_image_path"])
        if not dn_image.exists() or not baseline_image.exists():
            failures.append({**row, "eval_status": "missing_image_file"})
            continue
        prompt = row["text_prompt"][: args.max_prompt_chars]
        try:
            result = call_vision_llm(config, make_eval_prompt(prompt, row["baseline"]), dn_image, baseline_image, args)
            parsed = result["parsed"]
            dn_avg = score_mean(parsed.get("dn", {}))
            baseline_avg = score_mean(parsed.get("baseline", {}))
            if dn_avg is None or baseline_avg is None:
                raise RuntimeError(f"Missing score dimensions in response: {result['raw_response'][:300]}")
            out = {
                **row,
                "eval_status": "success",
                "dn_avg": dn_avg,
                "baseline_avg": baseline_avg,
                "delta_baseline_minus_dn": round(baseline_avg - dn_avg, 4),
                "winner": parsed.get("winner", ""),
                "dn_reason": parsed.get("dn", {}).get("reason", ""),
                "baseline_reason": parsed.get("baseline", {}).get("reason", ""),
            }
            for dim in DIMENSIONS:
                out[f"dn_{dim}"] = parsed.get("dn", {}).get(dim)
                out[f"baseline_{dim}"] = parsed.get("baseline", {}).get(dim)
            scores.append(out)
            write_jsonl(reports_dir / "llm_pairwise_scores.jsonl", scores)
            print(f"[{idx}/{len(candidates)}] evaluated {row['baseline']} {row['id']}: delta={out['delta_baseline_minus_dn']}")
        except Exception as exc:  # noqa: BLE001
            failure = {**row, "eval_status": "failed", "eval_error": str(exc)}
            failures.append(failure)
            write_jsonl(reports_dir / "evaluation_failures.jsonl", failures)
            print(f"[{idx}/{len(candidates)}] failed {row['baseline']} {row['id']}: {exc}")
        if args.sleep:
            time.sleep(args.sleep)

    # Add non-candidate generation/evaluation skips.
    evaluated_keys = {(row["baseline"], row["id"]) for row in candidates}
    for row in generation_rows:
        if (row["baseline"], row["id"]) in evaluated_keys:
            continue
        reason = "not_evaluated"
        if row["generation_status"] != "success":
            reason = f"generation_{row['generation_status']}"
        elif not row["dn_reference_image_exists"]:
            reason = "missing_dn_reference_image"
        failures.append({**row, "eval_status": "skipped", "eval_error": reason})

    write_jsonl(reports_dir / "llm_pairwise_scores.jsonl", scores)
    write_csv(reports_dir / "llm_pairwise_scores.csv", scores)
    write_jsonl(reports_dir / "evaluation_failures.jsonl", failures)
    write_csv(reports_dir / "evaluation_failures.csv", failures)

    baseline_summary, theme_summary = summarize(scores) if scores else ([], [])
    write_csv(reports_dir / "summary_by_baseline.csv", baseline_summary)
    write_csv(reports_dir / "summary_by_theme.csv", theme_summary)
    (reports_dir / "summary_by_baseline.json").write_text(json.dumps(baseline_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reports_dir / "summary_by_theme.json").write_text(json.dumps(theme_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(run_dir, generation_rows, scores, baseline_summary, theme_summary, failures, {"model": config["model"], "base_url": config["base_url"]})
    print(f"Wrote reports to {reports_dir}")


if __name__ == "__main__":
    main()
