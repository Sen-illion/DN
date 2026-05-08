# -*- coding: utf-8 -*-
"""Run Rolling-4o as a DN text baseline.

The baseline is intentionally simple: generate a 10-segment story from each DN
theme using only the theme, style hint, rolling summary, and previous segment.
It exports the same theme_*/manifest/segment layout consumed by DN evaluators.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit("Missing dependency: openai. Install requirements or run inside the DN venv.") from exc


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_THEMES_FILE = REPO_ROOT / "game_themes_100.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "experiments" / "baselines" / "text_rolling_4o"
BASELINE_NAME = "Rolling-4o"

STYLE_HINTS = {
    "realistic": "写实风格：细节可信、光影自然、人物动机现实。",
    "cyberpunk": "赛博朋克风格：霓虹、科技异化、地下网络、阶层冲突。",
    "ink_painting": "水墨画风格：留白、笔墨意象、古典气质、含蓄叙事。",
    "watercolor": "水彩风格：柔和色彩、透明层次、清新但有情绪张力。",
    "anime": "动漫风格：鲜明角色、强情绪表达、镜头感和奇幻行动。",
    "oil_painting": "油画风格：厚重质感、戏剧光影、古典构图。",
}


class ApiError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def first_env(keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value.strip()
    return default


def parse_theme_ids(raw: str) -> List[int]:
    values: List[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", 1)
            values.extend(range(int(left), int(right) + 1))
        else:
            values.append(int(part))
    return values


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return slug.strip("_")[:48] or "theme"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_themes(path: Path, theme_ids: List[int], max_themes: int) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = [item for item in data.get("items", []) if isinstance(item, dict)]
    if theme_ids:
        wanted = set(theme_ids)
        items = [item for item in items if int(item.get("id", -1)) in wanted]
    items.sort(key=lambda item: int(item.get("id", 0)))
    if max_themes > 0:
        items = items[:max_themes]
    return items


def style_prompt(item: Dict[str, Any]) -> str:
    style = item.get("image_style") or {}
    style_type = style.get("type", "") if isinstance(style, dict) else ""
    subtype = style.get("subtype", "") if isinstance(style, dict) else ""
    label = item.get("style_label_zh") or style_type or "未指定风格"
    hint = STYLE_HINTS.get(style_type, "按主题需要保持稳定的视觉与叙事风格。")
    if subtype:
        hint += f" 子风格：{subtype}。"
    return f"{label} / {style_type}. {hint}"


def build_segment_messages(item: Dict[str, Any], index: int, summary: str, previous_segment: str) -> List[Dict[str, str]]:
    theme = str(item.get("theme", "")).strip()
    style = style_prompt(item)
    system = (
        "你是游戏剧情 baseline 生成器。严格按 Rolling baseline 工作：不做大纲规划，"
        "不引用图片，不创造隐藏的外部设定；每次只根据当前主题、风格、滚动摘要和上一段继续写。"
        "输出只写剧情正文，不要标题、编号、解释或 JSON。"
    )
    if index == 1:
        user = f"""主题：{theme}
风格：{style}
任务：生成游戏开场剧情，作为第 1 段。要求：
- 中文。
- 260-420 字。
- 有明确场景、主角处境、核心悬念和玩家可感知的目标。
- 保持游戏叙事感，但不要写选项列表。
- 只输出剧情正文。"""
    else:
        user = f"""主题：{theme}
风格：{style}
前文滚动摘要（不超过 200 字）：{summary or '无'}
上一段剧情：
{previous_segment}

任务：继续生成第 {index} 段剧情。要求：
- 中文。
- 260-420 字。
- 必须承接上一段的因果，不要重启故事。
- 可以引入新冲突，但不能无故改变主角、地点逻辑或核心目标。
- 保持游戏叙事感，但不要写选项列表。
- 只输出剧情正文。"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def build_summary_messages(item: Dict[str, Any], story_so_far: str) -> List[Dict[str, str]]:
    theme = str(item.get("theme", "")).strip()
    system = (
        "你是 rolling summary 压缩器。把已有游戏剧情压缩成给下一段使用的状态摘要。"
        "输出只写摘要正文，不要标题、编号、解释或 JSON。"
    )
    user = f"""主题：{theme}
已有剧情：
{story_so_far}

请压缩成不超过 200 个中文字的滚动摘要。必须保留：主角、当前地点、已发生关键事件、核心目标、未解决悬念。"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def call_chat(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    *,
    temperature: float,
    top_p: float,
    max_tokens: int,
    retries: int,
) -> Tuple[str, Dict[str, Any]]:
    last_error: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        started = time.time()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - started
            content = (resp.choices[0].message.content or "").strip()
            usage = getattr(resp, "usage", None)
            usage_obj = usage.model_dump() if hasattr(usage, "model_dump") else (dict(usage) if usage else {})
            meta = {
                "model": model,
                "elapsed_seconds": elapsed,
                "usage": usage_obj,
                "cost": None,
                "attempt": attempt,
            }
            if not content:
                raise ApiError("empty model response")
            return content, meta
        except Exception as exc:  # noqa: BLE001 - collect provider errors
            last_error = exc
            if attempt < retries:
                time.sleep(min(30, 2 ** attempt))
    raise ApiError(str(last_error))


def run_one_theme(args: argparse.Namespace, client: OpenAI, item: Dict[str, Any]) -> Dict[str, Any]:
    theme_id = int(item["id"])
    theme = str(item.get("theme", "")).strip()
    game_id = f"rolling_theme_{theme_id:03d}"
    out_dir = args.output_root / f"theme_{theme_id:03d}_{safe_slug(theme)}"
    seg_dir = out_dir / "segments"
    manifest_path = out_dir / f"{game_id}_manifest.json"

    if manifest_path.is_file() and args.resume and not args.overwrite:
        return {"theme_id": theme_id, "theme": theme, "status": "skipped_existing", "out_dir": str(out_dir)}

    if args.overwrite and out_dir.exists():
        # Keep this non-destructive: overwrite only files this runner owns.
        for path in list(out_dir.glob("segments/*.json")) + [
            out_dir / "story.txt",
            out_dir / "summary_trace.json",
            out_dir / "run_meta.json",
            manifest_path,
        ]:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    out_dir.mkdir(parents=True, exist_ok=True)
    seg_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    summary = ""
    previous_segment = ""
    segments: List[Dict[str, Any]] = []
    summary_trace: List[Dict[str, Any]] = []
    all_texts: List[str] = []
    total_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    for index in range(1, args.segments + 1):
        summary_before = summary
        messages = build_segment_messages(item, index, summary_before, previous_segment)
        scene, gen_meta = call_chat(
            client,
            args.model,
            messages,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.segment_max_tokens,
            retries=args.retries,
        )
        for key in total_usage:
            total_usage[key] += int((gen_meta.get("usage") or {}).get(key) or 0)

        segment_payload = {
            "theme_item_id": theme_id,
            "baseline": BASELINE_NAME,
            "segment_index": index,
            "theme": theme,
            "style": item.get("image_style") or {},
            "style_label_zh": item.get("style_label_zh", ""),
            "scene": scene,
            "rolling_summary_before": summary_before,
            "model": args.model,
            "generation_meta": gen_meta,
        }
        seg_name = f"segments/{index:03d}.json"
        write_json(out_dir / seg_name, segment_payload)
        segments.append({"index": index, "json": seg_name})
        all_texts.append(scene)
        previous_segment = scene

        story_so_far = "\n\n".join(all_texts)
        summary_messages = build_summary_messages(item, story_so_far)
        summary, summary_meta = call_chat(
            client,
            args.model,
            summary_messages,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.summary_max_tokens,
            retries=args.retries,
        )
        summary = summary.replace("\n", " ").strip()[: args.summary_chars]
        for key in total_usage:
            total_usage[key] += int((summary_meta.get("usage") or {}).get(key) or 0)
        summary_trace.append(
            {
                "after_segment": index,
                "summary": summary,
                "summary_chars": len(summary),
                "model": args.model,
                "generation_meta": summary_meta,
            }
        )

    story_text = "\n\n---\n\n".join(all_texts)
    (out_dir / "story.txt").write_text(story_text, encoding="utf-8")
    write_json(out_dir / "summary_trace.json", summary_trace)

    run_meta = {
        "baseline": BASELINE_NAME,
        "theme_item_id": theme_id,
        "theme": theme,
        "model": args.model,
        "base_url": args.base_url,
        "segments": args.segments,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "started_at": utc_now(),
        "elapsed_seconds": time.time() - started,
        "usage": total_usage,
        "cost": None,
    }
    write_json(out_dir / "run_meta.json", run_meta)

    manifest = {
        "game_id": game_id,
        "theme_item_id": theme_id,
        "theme": theme,
        "segment_count": len(segments),
        "text_only": True,
        "baseline": BASELINE_NAME,
        "style": item.get("image_style") or {},
        "style_label_zh": item.get("style_label_zh", ""),
        "segments": segments,
        "run_meta": "run_meta.json",
    }
    write_json(manifest_path, manifest)

    return {
        "theme_id": theme_id,
        "theme": theme,
        "status": "success",
        "out_dir": str(out_dir),
        "manifest": str(manifest_path),
        "elapsed_seconds": run_meta["elapsed_seconds"],
        "usage": total_usage,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Rolling-4o on DN themes.")
    parser.add_argument("--themes-file", type=Path, default=DEFAULT_THEMES_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--theme-ids", default="1,2,3", help="Comma list or ranges, e.g. 1,2,3 or 1-100.")
    parser.add_argument("--max-themes", type=int, default=0)
    parser.add_argument("--segments", type=int, default=10)
    parser.add_argument("--model", default="")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-p", type=float, default=0.99)
    parser.add_argument("--segment-max-tokens", type=int, default=900)
    parser.add_argument("--summary-max-tokens", type=int, default=320)
    parser.add_argument("--summary-chars", type=int, default=200)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--resume", action="store_true", help="Skip themes that already have a manifest.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite this runner's existing files for selected themes.")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    args.model = args.model or first_env(
        [
            "ROLLING_OPENAI_MODEL",
            "OPENAI_MODEL",
        ],
        "gpt-4o",
    )
    args.api_key = args.api_key or first_env(
        [
            "ROLLING_OPENAI_API_KEY",
            "OPENAI_API_KEY",
            "DOC_OPENAI_API_KEY",
            "YUNWU_API_KEY",
            "COHERENCE_API_KEY",
            "Origin_Segment_Analyst_API_KEY",
        ]
    )
    args.base_url = args.base_url or first_env(
        [
            "ROLLING_OPENAI_BASE_URL",
            "OPENAI_BASE_URL",
            "DOC_OPENAI_BASE_URL",
            "YUNWU_BASE_URL",
            "COHERENCE_BASE_URL",
            "Origin_Segment_Analyst_BASE_URL",
        ],
        "https://api.openai.com/v1",
    )
    if not args.api_key:
        raise SystemExit("No API key found. Set ROLLING_OPENAI_API_KEY, OPENAI_API_KEY, or Origin_Segment_Analyst_API_KEY in .env.")

    args.themes_file = args.themes_file.resolve()
    args.output_root = args.output_root.resolve()
    args.output_root.mkdir(parents=True, exist_ok=True)

    theme_ids = parse_theme_ids(args.theme_ids)
    themes = load_themes(args.themes_file, theme_ids, args.max_themes)
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)

    run_started = time.time()
    results: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    print(f"Running {BASELINE_NAME}: themes={len(themes)} model={args.model} output={args.output_root}", flush=True)

    for item in themes:
        theme_id = int(item.get("id", -1))
        try:
            result = run_one_theme(args, client, item)
            results.append(result)
            print(f"[{result['status']}] theme {theme_id}: {result.get('theme', '')}", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep batch running
            failure = {"theme_id": theme_id, "theme": item.get("theme", ""), "status": "failed", "error": str(exc)}
            failures.append(failure)
            print(f"[failed] theme {theme_id}: {exc}", file=sys.stderr, flush=True)
            if args.max_themes == 1:
                break

    root_meta = {
        "baseline": BASELINE_NAME,
        "themes_file": str(args.themes_file),
        "output_root": str(args.output_root),
        "theme_ids": theme_ids,
        "model": args.model,
        "base_url": args.base_url,
        "segments": args.segments,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "finished_at": utc_now(),
        "elapsed_seconds": time.time() - run_started,
        "success_count": sum(1 for r in results if r.get("status") in {"success", "skipped_existing"}),
        "failure_count": len(failures),
        "results": results,
        "failures": failures,
    }
    write_json(args.output_root / "run_meta.json", root_meta)
    print(json.dumps({"success_count": root_meta["success_count"], "failure_count": len(failures), "output_root": str(args.output_root)}, ensure_ascii=False), flush=True)
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
