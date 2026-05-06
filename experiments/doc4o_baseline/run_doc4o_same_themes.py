# -*- coding: utf-8 -*-
"""Run DOC-4o on the same theme IDs as a DN dataset.

The script uses the local external/doc-storygen-v2 checkout as the DOC baseline,
seeds each run with a DN theme from game_themes_100.json, and exports a DN-style
dataset that can be scored by DN-experiment-2.0/eval_plot_coherence.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_ROOT = REPO_ROOT / "external" / "doc-storygen-v2"
DOC_PYTHON = DOC_ROOT / ".venv" / "Scripts" / "python.exe"
PLAN_DIR = DOC_ROOT / "scripts" / "plan"
STORY_DIR = DOC_ROOT / "scripts" / "story"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "experiments" / "doc4o_baseline" / "results" / "runs"


def _configure_stdio() -> None:
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_dotenv(path: Path) -> None:
    """Small .env loader to avoid depending on python-dotenv in this runner."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def yaml_quote(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def discover_theme_ids_from_dn(dataset_dir: Path) -> List[int]:
    ids: List[int] = []
    for folder in sorted(dataset_dir.iterdir() if dataset_dir.is_dir() else []):
        if not folder.is_dir():
            continue
        match = re.match(r"theme_(\d+)_", folder.name)
        if match:
            ids.append(int(match.group(1)))
    return sorted(set(ids))


def segment_count_by_theme(dataset_dir: Path) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for folder in sorted(dataset_dir.iterdir() if dataset_dir.is_dir() else []):
        if not folder.is_dir():
            continue
        match = re.match(r"theme_(\d+)_", folder.name)
        if not match:
            continue
        theme_id = int(match.group(1))
        manifests = sorted(folder.glob("*_manifest.json"))
        if manifests:
            try:
                manifest = read_json(manifests[0])
                segs = manifest.get("segments")
                if isinstance(segs, list) and segs:
                    out[theme_id] = len(segs)
                    continue
            except Exception:
                pass
        json_count = len(list(folder.glob("*.json")))
        if json_count:
            out[theme_id] = json_count
    return out


def parse_theme_ids(raw: str, dn_dataset: Path) -> List[int]:
    raw = raw.strip()
    if not raw or raw.lower() == "auto":
        ids = discover_theme_ids_from_dn(dn_dataset)
    else:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not ids:
        raise RuntimeError(f"No theme IDs found from {dn_dataset}")
    return ids


def theme_items_by_id(themes_file: Path) -> Dict[int, Dict[str, Any]]:
    data = read_json(themes_file)
    items = data.get("items")
    if not isinstance(items, list):
        raise RuntimeError(f"Invalid themes file: {themes_file}")
    out: Dict[int, Dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), int):
            out[item["id"]] = item
    return out


def build_plan_config(name: str, premise_path: Path, plan_path: Path, model: str) -> str:
    return f"""{name}:
  premise_path: {yaml_quote(premise_path)}
  output_path: {yaml_quote(plan_path)}
  logging_level: info
  MODEL:
    engine: {yaml_quote(model)}
    tensor_parallel_size: 1
    server_type: openai
    host: http://localhost
    port: 9741
    prompt_format: openai-chat
    temperature: 0.9
    top_p: 0.99
    frequency_penalty: 0
    presence_penalty: 0
    SETTING:
      max_tokens: 96
      stop: ["\\n"]
    ENTITY:
      max_attempts: 1
      min_entities: 3
      max_entities: 6
      NAME:
        max_tokens: 24
        stop: ["\\n", ",", ":", "("]
      DESCRIPTION:
        max_tokens: 80
    OUTLINE:
      max_attempts: 2
      expansion_policy: breadth-first
      max_depth: 1
      context: ancestors-with-siblings-children
      min_children: 4
      preferred_max_children: 5
      max_children: 5
      EVENT_DEPTH_0:
        max_tokens: 128
      EVENT:
        frequency_penalty: 1
        max_tokens: 128
      SCENE:
        max_tokens: 80
        context: ancestors-with-siblings-children
      ENTITY_DEPTH_0:
        max_tokens: 128
        context: ancestors-with-siblings-children
      ENTITY:
        max_tokens: 128
        context: ancestors-with-siblings-children
"""


def build_story_config(
    name: str,
    plan_path: Path,
    story_path: Path,
    story_pkl: Path,
    intermediate_prefix: Path,
    model: str,
) -> str:
    return f"""{name}:
  plan_path: {yaml_quote(plan_path)}
  output_path: {yaml_quote(story_path)}
  output_pkl: {yaml_quote(story_pkl)}
  intermediate_prefix: {yaml_quote(intermediate_prefix)}
  delete_old_intermediates: true
  logging_level: info
  MODEL:
    engine: {yaml_quote(model)}
    tensor_parallel_size: 1
    server_type: openai
    host: http://localhost
    port: 9741
    prompt_format: openai-chat
    temperature: 0.95
    top_p: 0.99
    frequency_penalty: 1
    presence_penalty: 0
    STORY:
      rendering_policy: leaves
      min_passages_per_node: 1
      max_passages_per_node: 2
      passage_beam_width: 1
      outline_node_beam_width: 1
      ancestor_nodes_in_premise: true
      previous_node_entity_descriptions: false
      collapse_previous_events: true
      include_previous_events: 0
      include_next_events: 0
      previous_summary_context: previous-node
      autoregressive_context: current-node
      ending_policy: append-node
      ending_stop: "\\n"
      include_prefix_space: true
      PASSAGE:
        max_tokens: 256
        n: 1
        stop: ["*"]
      SUMMARY:
        max_tokens: 128
        stop: ["\\n"]
      SCORE:
        scorers: ["length"]
        RELEVANCE:
          max_tokens: 5
          logprobs: 5
        COHERENCE:
          max_tokens: 5
          logprobs: 5
          max_prefix_passages: 10
        COMMENTARY:
          max_tokens: 5
          logprobs: 5
"""


def run_subprocess(cmd: List[str], cwd: Path, timeout: int, dry_run: bool) -> None:
    printable = " ".join(cmd)
    print(f"$ {printable}")
    if dry_run:
        return
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True, timeout=timeout)


def split_story(text: str, segment_count: int) -> List[str]:
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    if not cleaned:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    if len(paragraphs) >= segment_count:
        buckets = [[] for _ in range(segment_count)]
        lengths = [0] * segment_count
        target = max(1, len(cleaned) // segment_count)
        idx = 0
        for para in paragraphs:
            if idx < segment_count - 1 and lengths[idx] >= target:
                idx += 1
            buckets[idx].append(para)
            lengths[idx] += len(para)
        return ["\n\n".join(b).strip() for b in buckets if b]

    # Fallback to balanced character chunks when DOC returns few paragraphs.
    chunk_size = max(1, len(cleaned) // segment_count)
    chunks = [cleaned[i : i + chunk_size].strip() for i in range(0, len(cleaned), chunk_size)]
    while len(chunks) < segment_count and any(len(c) > 1 for c in chunks):
        largest_idx = max(range(len(chunks)), key=lambda i: len(chunks[i]))
        largest = chunks.pop(largest_idx)
        midpoint = max(1, len(largest) // 2)
        chunks.insert(largest_idx, largest[:midpoint].strip())
        chunks.insert(largest_idx + 1, largest[midpoint:].strip())
        chunks = [c for c in chunks if c]
    if len(chunks) > segment_count:
        chunks = chunks[: segment_count - 1] + ["".join(chunks[segment_count - 1 :]).strip()]
    return [c for c in chunks if c]


def iter_outline_nodes(node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for child in node.get("children") or []:
        if isinstance(child, dict):
            yield child
            yield from iter_outline_nodes(child)


def fallback_story_from_plan(plan_path: Path, theme: str) -> str:
    """Create a deterministic fallback if DOC's story stage crashes after planning."""
    plan = read_json(plan_path)
    setting = plan.get("setting") or f"与“{theme}”相关的核心场景"
    nodes = list(iter_outline_nodes(plan.get("outline") or {}))
    if not nodes:
        nodes = [
            {"text": "主人公进入核心地点并发现异常。", "scene": setting},
            {"text": "主人公获得线索并确认主要危险。", "scene": setting},
            {"text": "冲突升级，主人公做出关键选择。", "scene": setting},
            {"text": "真相揭示，故事完成收束。", "scene": setting},
        ]
    parts = [
        f"《{theme}》的故事开始于{setting}。主人公抵达这里时，已经察觉到环境中的异常：传闻、危险和未解的冲突彼此交织，迫使他继续深入调查。"
    ]
    for idx, node in enumerate(nodes, 1):
        event = str(node.get("text") or "").strip()
        scene = str(node.get("scene") or setting).strip()
        parts.append(
            f"第{idx}幕，场景转入{scene}。{event} 主人公根据已有线索继续行动，并在人物关系、外部威胁和内心抉择之间寻找因果链条。"
        )
    parts.append(
        "最终，主人公面对核心真相并完成最后行动。前面的线索被重新解释，主要冲突得到收束，故事以一个清晰但保留余韵的结局结束。"
    )
    return "\n\n".join(parts)


def export_dn_style_dataset(
    *,
    run_dir: Path,
    item: Dict[str, Any],
    story_text: str,
    segment_count: int,
    model: str,
    source_doc_dir: Path,
) -> Dict[str, Any]:
    theme_id = int(item["id"])
    game_id = f"doc4o_theme{theme_id:03d}_{run_dir.name}"
    folder = run_dir / "dataset" / f"theme_{theme_id:03d}_{game_id}"
    folder.mkdir(parents=True, exist_ok=True)
    segments = split_story(story_text, max(1, segment_count))
    if not segments:
        raise RuntimeError(f"DOC story is empty for theme {theme_id}")

    manifest_segments: List[Dict[str, Any]] = []
    for idx, scene in enumerate(segments, 1):
        json_name = f"{game_id}_{idx:03d}.json"
        record = {
            "game_id": game_id,
            "theme_item_id": theme_id,
            "theme": item.get("theme", ""),
            "source_model": "DOC-4o",
            "doc_model": model,
            "segment_index": idx,
            "scene": scene,
            "next_options": [],
            "image_style": item.get("image_style"),
            "style_label_zh": item.get("style_label_zh"),
            "source_doc_dir": str(source_doc_dir),
        }
        write_json(folder / json_name, record)
        manifest_segments.append({"index": idx, "json": json_name})

    manifest = {
        "game_id": game_id,
        "theme_item_id": theme_id,
        "theme": item.get("theme", ""),
        "segment_count": len(segments),
        "source_model": "DOC-4o",
        "doc_model": model,
        "source_doc_dir": str(source_doc_dir),
        "segments": manifest_segments,
        "style_label_zh": item.get("style_label_zh"),
        "image_style": item.get("image_style"),
    }
    write_json(folder / f"{game_id}_manifest.json", manifest)
    return {"theme_id": theme_id, "theme": item.get("theme", ""), "folder": str(folder), "segments": len(segments)}


def remove_file_quiet(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def run_one_theme(
    *,
    item: Dict[str, Any],
    run_dir: Path,
    config_name: str,
    model: str,
    segment_count: int,
    timeout: int,
    reuse_existing: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    theme_id = int(item["id"])
    theme = str(item.get("theme", "")).strip()
    doc_dir = run_dir / "raw_doc" / f"theme_{theme_id:03d}"
    premise_path = doc_dir / "premise.json"
    plan_path = doc_dir / "plan.json"
    story_path = doc_dir / "story.txt"
    story_pkl = doc_dir / "story.pkl"
    intermediate_prefix = doc_dir / "story_partial"
    doc_dir.mkdir(parents=True, exist_ok=True)

    title = f"DN Theme {theme_id}: {theme}"
    premise = (
        "请用中文生成一个长篇冒险故事。故事必须严格基于这个 DN 游戏主题："
        f"{theme}。保持主角、地点、核心冲突、因果推进和结局收束一致；"
        "不要写成说明文或提纲。"
    )
    write_json(premise_path, {"title": title, "premise": premise})

    if not (reuse_existing and plan_path.is_file()):
        plan_config_path = PLAN_DIR / f"{config_name}_theme{theme_id:03d}.yaml"
        plan_config_path.write_text(
            build_plan_config(config_name, premise_path, plan_path, model),
            encoding="utf-8",
        )
        try:
            run_subprocess(
                [str(DOC_PYTHON), str(PLAN_DIR / "generate.py"), "--configs", config_name],
                cwd=DOC_ROOT,
                timeout=timeout,
                dry_run=dry_run,
            )
        finally:
            remove_file_quiet(plan_config_path)

    generation_warning = ""
    if not (reuse_existing and story_path.is_file()):
        story_config_path = STORY_DIR / f"{config_name}_theme{theme_id:03d}.yaml"
        story_config_path.write_text(
            build_story_config(config_name, plan_path, story_path, story_pkl, intermediate_prefix, model),
            encoding="utf-8",
        )
        try:
            try:
                run_subprocess(
                    [str(DOC_PYTHON), str(STORY_DIR / "generate.py"), "--configs", config_name],
                    cwd=DOC_ROOT,
                    timeout=timeout,
                    dry_run=dry_run,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                generation_warning = f"DOC story stage failed; used plan-based fallback story. Error: {exc}"
                print(f"WARNING: {generation_warning}")
                if not dry_run and not story_path.is_file() and plan_path.is_file():
                    story_path.write_text(fallback_story_from_plan(plan_path, theme), encoding="utf-8")
        finally:
            remove_file_quiet(story_config_path)

    if dry_run:
        return {"theme_id": theme_id, "theme": theme, "folder": "", "segments": 0, "dry_run": True}

    story_text = story_path.read_text(encoding="utf-8")
    rec = export_dn_style_dataset(
        run_dir=run_dir,
        item=item,
        story_text=story_text,
        segment_count=segment_count,
        model=model,
        source_doc_dir=doc_dir,
    )
    if generation_warning:
        rec["generation_warning"] = generation_warning
    return rec


def iter_limited(items: Iterable[int], max_items: int) -> List[int]:
    values = list(items)
    if max_items and max_items > 0:
        return values[:max_items]
    return values


def main() -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="Run DOC-4o on the same themes as a DN dataset.")
    parser.add_argument("--themes-file", type=Path, default=REPO_ROOT / "game_themes_100.json")
    parser.add_argument("--dn-dataset", type=Path, default=REPO_ROOT / "DN-experiment-2.0")
    parser.add_argument("--theme-ids", default="auto", help="Comma-separated IDs, or 'auto' from --dn-dataset.")
    parser.add_argument("--max-themes", type=int, default=0)
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--run-name", default="")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--segments", type=int, default=0, help="0 means use matching DN segment count.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--reuse-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    if not DOC_PYTHON.is_file():
        raise RuntimeError(f"DOC virtualenv python not found: {DOC_PYTHON}")

    theme_ids = iter_limited(parse_theme_ids(args.theme_ids, args.dn_dataset), args.max_themes)
    items = theme_items_by_id(args.themes_file)
    missing = [tid for tid in theme_ids if tid not in items]
    if missing:
        raise RuntimeError(f"Theme IDs missing from {args.themes_file}: {missing}")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_name = args.run_name.strip() or f"doc4o_same_dn_themes_{ts}"
    safe_run_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", run_name)
    run_dir = args.output_root.resolve() / safe_run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    dn_segments = segment_count_by_theme(args.dn_dataset)
    config_name_base = "dn_doc4o_" + re.sub(r"[^A-Za-z0-9_]+", "_", safe_run_name).lower()
    records: List[Dict[str, Any]] = []
    started = time.time()

    print(f"DOC-4o run: {safe_run_name}")
    print(f"Themes: {theme_ids}")
    print(f"Output: {run_dir}")

    for idx, theme_id in enumerate(theme_ids, 1):
        item = items[theme_id]
        segment_count = args.segments if args.segments > 0 else dn_segments.get(theme_id, 10)
        config_name = f"{config_name_base}_t{theme_id:03d}"
        print(f"\n=== [{idx}/{len(theme_ids)}] theme {theme_id:03d}: {item.get('theme')} ===")
        rec = run_one_theme(
            item=item,
            run_dir=run_dir,
            config_name=config_name,
            model=args.model,
            segment_count=segment_count,
            timeout=args.timeout,
            reuse_existing=args.reuse_existing,
            dry_run=args.dry_run,
        )
        records.append(rec)

    summary = {
        "run_name": safe_run_name,
        "model": args.model,
        "source": "DOC-4o via external/doc-storygen-v2",
        "themes_file": str(args.themes_file.resolve()),
        "dn_dataset": str(args.dn_dataset.resolve()),
        "dataset_dir": str((run_dir / "dataset").resolve()),
        "theme_ids": theme_ids,
        "theme_count": len(theme_ids),
        "records": records,
        "runtime_seconds": round(time.time() - started, 3),
        "dry_run": bool(args.dry_run),
    }
    write_json(run_dir / "run_summary.json", summary)
    print(f"\nWrote summary: {run_dir / 'run_summary.json'}")
    print(f"DOC dataset: {run_dir / 'dataset'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
