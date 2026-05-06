# -*- coding: utf-8 -*-
"""Run DOC Story Generation V2 as a DN text baseline.

This adapter keeps DOC as the generation method, but feeds it DN themes and
exports the generated story in the manifest/segment layout used by DN evaluators.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DOC_ROOT = REPO_ROOT / "external" / "doc-storygen-v2"
DEFAULT_THEMES_FILE = REPO_ROOT / "game_themes_100.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "experiments" / "baselines" / "text_doc"


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


def load_themes(path: Path, theme_ids: List[int], max_themes: int) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    items = [item for item in payload.get("items", []) if isinstance(item, dict)]
    if theme_ids:
        wanted = set(theme_ids)
        items = [item for item in items if int(item.get("id", -1)) in wanted]
    if max_themes > 0:
        items = items[:max_themes]
    return items


def parse_theme_ids(raw: str) -> List[int]:
    values: List[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part:
            values.append(int(part))
    return values


def slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return text.strip("_")[:64] or "doc"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_plan_config(args: argparse.Namespace, premise_path: Path, output_path: Path) -> Dict[str, Any]:
    return {
        "dn_run": {
            "premise_path": str(premise_path),
            "output_path": str(output_path),
            "logging_level": "info",
            "MODEL": {
                "engine": args.model,
                "tensor_parallel_size": 1,
                "server_type": "openai",
                "host": "http://localhost",
                "port": 9741,
                "prompt_format": "openai-chat",
                "temperature": 1.0,
                "top_p": 0.99,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "SETTING": {"max_tokens": 256, "stop": ["\n"]},
                "ENTITY": {
                    "max_attempts": 5,
                    "min_entities": 3,
                    "max_entities": 10,
                    "NAME": {"max_tokens": 32, "stop": ["\n", ",", ":", "("]},
                    "DESCRIPTION": {"max_tokens": 128},
                },
                "OUTLINE": {
                    "max_attempts": 5,
                    "expansion_policy": "breadth-first",
                    "max_depth": args.outline_depth,
                    "context": "ancestors-with-siblings-children",
                    "min_children": 2,
                    "preferred_max_children": 4,
                    "max_children": 5,
                    "EVENT_DEPTH_0": {"max_tokens": 256},
                    "EVENT": {"frequency_penalty": 1, "max_tokens": 256},
                    "SCENE": {"max_tokens": 128},
                    "ENTITY_DEPTH_0": {"max_tokens": 256},
                    "ENTITY": {"max_tokens": 256},
                },
            },
        }
    }


def build_story_config(args: argparse.Namespace, plan_path: Path, story_path: Path, pkl_path: Path, partial_prefix: Path) -> Dict[str, Any]:
    scorers = ["length"] if args.stable_no_logprobs else ["relevance", "coherence", "commentary", "length"]
    return {
        "dn_run": {
            "plan_path": str(plan_path),
            "output_path": str(story_path),
            "output_pkl": str(pkl_path),
            "intermediate_prefix": str(partial_prefix),
            "delete_old_intermediates": True,
            "logging_level": "info",
            "MODEL": {
                "engine": args.model,
                "tensor_parallel_size": 1,
                "server_type": "openai",
                "host": "http://localhost",
                "port": 9741,
                "prompt_format": "openai-chat",
                "temperature": 1.0,
                "top_p": 0.99,
                "frequency_penalty": 1,
                "presence_penalty": 0,
                "STORY": {
                    "rendering_policy": "leaves",
                    "min_passages_per_node": args.min_passages_per_node,
                    "max_passages_per_node": args.max_passages_per_node,
                    "passage_beam_width": 1,
                    "outline_node_beam_width": 1,
                    "ancestor_nodes_in_premise": True,
                    "previous_node_entity_descriptions": False,
                    "collapse_previous_events": True,
                    "include_previous_events": 0,
                    "include_next_events": 0,
                    "previous_summary_context": "previous-node",
                    "autoregressive_context": "current-node",
                    "ending_policy": "append-node",
                    "ending_stop": "\n",
                    "include_prefix_space": True,
                    "PASSAGE": {
                        "max_tokens": args.passage_max_tokens,
                        "n": 1 if args.stable_no_logprobs else args.passage_candidates,
                        "stop": ["*"],
                    },
                    "SUMMARY": {"max_tokens": 128, "stop": ["\n"]},
                    "SCORE": {
                        "scorers": scorers,
                        "RELEVANCE": {"max_tokens": 5, "logprobs": 5},
                        "COHERENCE": {"max_tokens": 5, "logprobs": 5, "max_prefix_passages": 10},
                        "COMMENTARY": {"max_tokens": 5, "logprobs": 5},
                    },
                },
            },
        }
    }


def run_doc_step(doc_root: Path, step: str, config_payload: Dict[str, Any], env: Dict[str, str], doc_python: Path) -> None:
    step_dir = doc_root / "scripts" / step
    config_path = step_dir / "dn_run_config.yaml"
    write_json(config_path, config_payload)
    try:
        subprocess.run(
            [str(doc_python), "generate.py", "--configs", "dn_run"],
            cwd=str(step_dir),
            env=env,
            check=True,
        )
    finally:
        try:
            config_path.unlink()
        except FileNotFoundError:
            pass


def split_story(story_text: str, segments: int) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", story_text) if p.strip()]
    if not paragraphs:
        paragraphs = [story_text.strip()]
    buckets = [[] for _ in range(max(1, segments))]
    for idx, paragraph in enumerate(paragraphs):
        buckets[min(idx * segments // max(1, len(paragraphs)), segments - 1)].append(paragraph)
    return ["\n\n".join(bucket).strip() for bucket in buckets if bucket]


def export_dn_layout(out_dir: Path, game_id: str, theme_id: int, theme: str, story_text: str, segments: int, doc_artifacts: Dict[str, str]) -> None:
    parts = split_story(story_text, segments)
    manifest_segments = []
    for i, scene in enumerate(parts, start=1):
        name = f"{game_id}_{i:03d}.json"
        write_json(
            out_dir / name,
            {
                "scene": scene,
                "theme_item_id": theme_id,
                "baseline": "DOC",
                "source": "doc-storygen-v2",
            },
        )
        manifest_segments.append({"index": i, "json": name})
    write_json(
        out_dir / f"{game_id}_manifest.json",
        {
            "game_id": game_id,
            "theme_item_id": theme_id,
            "theme": theme,
            "segment_count": len(parts),
            "text_only": True,
            "baseline": "DOC",
            "doc_artifacts": doc_artifacts,
            "segments": manifest_segments,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DOC StoryGen V2 on DN themes and export DN evaluator format.")
    parser.add_argument("--doc-root", type=Path, default=DEFAULT_DOC_ROOT)
    parser.add_argument("--doc-python", type=Path, default=None, help="Python executable for the DOC environment.")
    parser.add_argument("--themes-file", type=Path, default=DEFAULT_THEMES_FILE)
    parser.add_argument("--theme-ids", default="1,2,3,4,5,6,12,18,54,73")
    parser.add_argument("--max-themes", type=int, default=0)
    parser.add_argument("--segments", type=int, default=10)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--model", default=os.environ.get("DOC_OPENAI_MODEL") or os.environ.get("Origin_Segment_Analyst_MODEL") or "gpt-4o")
    parser.add_argument("--api-base-url", default="", help="OpenAI-compatible API base URL, e.g. https://yunwu.ai/v1.")
    parser.add_argument("--api-key", default="", help="OpenAI-compatible API key. Prefer leaving empty to read from .env.")
    parser.add_argument("--outline-depth", type=int, default=2, help="DOC outline depth. Use 3 for fuller but slower DOC.")
    parser.add_argument("--min-passages-per-node", type=int, default=1)
    parser.add_argument("--max-passages-per-node", type=int, default=2)
    parser.add_argument("--passage-max-tokens", type=int, default=256)
    parser.add_argument("--passage-candidates", type=int, default=4)
    parser.add_argument("--stable-no-logprobs", action="store_true", help="Disable DOC logprob rerankers for API providers that do not support logprobs.")
    parser.add_argument("--language", default="Chinese")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    doc_root = args.doc_root.resolve()
    if args.doc_python is None:
        default_python = doc_root / ".venv" / "Scripts" / "python.exe"
        args.doc_python = default_python if default_python.is_file() else Path(sys.executable)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(doc_root) + os.pathsep + env.get("PYTHONPATH", "")
    api_key = (
        args.api_key
        or env.get("Origin_Segment_Analyst_API_KEY")
        or env.get("COHERENCE_API_KEY")
        or env.get("DOC_OPENAI_API_KEY")
        or env.get("OPENAI_API_KEY")
        or ""
    )
    api_base_url = (
        args.api_base_url
        or env.get("Origin_Segment_Analyst_BASE_URL")
        or env.get("COHERENCE_BASE_URL")
        or env.get("DOC_OPENAI_BASE_URL")
        or env.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    env["DOC_OPENAI_API_KEY"] = api_key
    env["DOC_OPENAI_BASE_URL"] = api_base_url
    env["DOC_OPENAI_MODEL"] = args.model

    missing = [key for key in ("DOC_OPENAI_API_KEY", "DOC_OPENAI_BASE_URL") if not env.get(key)]
    if missing:
        raise RuntimeError(f"Missing API environment variables: {', '.join(missing)}")
    print(f"DOC API base URL: {env['DOC_OPENAI_BASE_URL']}")
    print(f"DOC API model: {args.model}")

    themes = load_themes(args.themes_file, parse_theme_ids(args.theme_ids), args.max_themes)
    args.output_root.mkdir(parents=True, exist_ok=True)
    run_root = doc_root / "scripts" / "dn_runs"
    run_root.mkdir(parents=True, exist_ok=True)

    for item in themes:
        theme_id = int(item.get("id"))
        theme = str(item.get("theme") or "").strip()
        if not theme:
            continue
        game_id = f"doc_theme{theme_id:03d}_{int(time.time())}_{slug(theme)[:20]}"
        work_dir = run_root / game_id
        out_dir = args.output_root / f"theme_{theme_id:03d}_{game_id}"
        work_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        premise_path = work_dir / "premise.json"
        plan_path = work_dir / "plan.json"
        story_path = work_dir / "story.txt"
        pkl_path = work_dir / "story.pkl"
        partial_prefix = work_dir / "story_partial"
        premise_text = (
            f"Generate a coherent long-form adventure story in {args.language}. "
            f"The story must be based on this DN game theme: {theme}. "
            "Keep the protagonist, setting, main conflict, and causal progression consistent."
        )
        write_json(premise_path, {"title": f"DN Theme {theme_id}: {theme[:40]}", "premise": premise_text})

        print(f"[DOC baseline] theme_id={theme_id} plan generation")
        run_doc_step(doc_root, "plan", build_plan_config(args, premise_path, plan_path), env, args.doc_python)
        print(f"[DOC baseline] theme_id={theme_id} story generation")
        run_doc_step(doc_root, "story", build_story_config(args, plan_path, story_path, pkl_path, partial_prefix), env, args.doc_python)

        story_text = story_path.read_text(encoding="utf-8", errors="replace")
        shutil.copy2(premise_path, out_dir / "doc_premise.json")
        shutil.copy2(plan_path, out_dir / "doc_plan.json")
        shutil.copy2(story_path, out_dir / "doc_story.txt")
        export_dn_layout(
            out_dir,
            game_id,
            theme_id,
            theme,
            story_text,
            args.segments,
            {
                "premise": str(out_dir / "doc_premise.json"),
                "plan": str(out_dir / "doc_plan.json"),
                "story": str(out_dir / "doc_story.txt"),
            },
        )

    print(f"DOC baseline exported to: {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
