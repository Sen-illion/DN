from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]
DN_EXPERIMENT_ROOT = REPO_ROOT / "DN-experiment-2.0"
ABLATION_ROOT = DN_EXPERIMENT_ROOT / "ablations" / "evaluator_ablation"
ABLATION_RESULTS_DIR = ABLATION_ROOT / "results"
THEMES_JSON = REPO_ROOT / "game_themes_100.json"
LEGACY_EXPERIMENT_ROOT = DN_EXPERIMENT_ROOT / "图片一致性_experiment" / "multiview_image_consistency"
LEGACY_RESULTS_DIR = LEGACY_EXPERIMENT_ROOT / "results"
LEGACY_SCORE_SCRIPT = LEGACY_EXPERIMENT_ROOT / "scripts" / "score_image_consistency_per_game.py"
WORKBOOK_EXPORT_SCRIPT = ABLATION_ROOT / "scripts" / "export_evaluator_ablation_workbook.mjs"
BUNDLED_NODE_MODULES = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "node_modules"
)
LOCAL_NODE_MODULES = ABLATION_ROOT / "node_modules"
LOCAL_ARTIFACT_TOOL = LOCAL_NODE_MODULES / "@oai" / "artifact-tool"
BUNDLED_ARTIFACT_TOOL = BUNDLED_NODE_MODULES / "@oai" / "artifact-tool"

DEFAULT_DIMENSIONS = [
    "semantic_consistency",
    "subject_attribute_consistency",
    "spatial_consistency",
    "style_lighting_consistency",
    "detail_integrity",
]

DEFAULT_JUDGE_GROUPS = [
    {
        "group_id": "gpt_4o_only",
        "group_label": "gpt-4o",
        "judge_models": ["gpt-4o"],
    },
    {
        "group_id": "claude_sonnet_only",
        "group_label": "claude-sonnet-4-20250514",
        "judge_models": ["claude-sonnet-4-20250514"],
    },
    {
        "group_id": "gpt_4o_plus_claude_sonnet",
        "group_label": "gpt-4o + claude-sonnet-4-20250514",
        "judge_models": ["gpt-4o", "claude-sonnet-4-20250514"],
    },
    {
        "group_id": "gpt_4o_plus_claude_sonnet_plus_gemini_flash",
        "group_label": "gpt-4o + claude-sonnet-4-20250514 + gemini-2.5-flash",
        "judge_models": ["gpt-4o", "claude-sonnet-4-20250514", "gemini-2.5-flash"],
    },
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def read_json(path: Path) -> Any:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def copy_latest(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def resolve_repo_path(value: str | Path | None) -> Optional[Path]:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_theme_catalog(path: Path = THEMES_JSON) -> Dict[int, Dict[str, Any]]:
    payload = read_json(path)
    items = payload.get("items") or []
    return {int(item["id"]): item for item in items}


def discover_manifest_paths(experiment_root: Path = DN_EXPERIMENT_ROOT) -> List[Path]:
    return sorted(experiment_root.glob("theme_*/*_image_paths.json"))


def safe_text(value: Any, max_len: int = 1600) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = " ".join(text.split())
    return text[:max_len]


def population_stddev(values: Iterable[float]) -> Optional[float]:
    numbers = [float(v) for v in values]
    if not numbers:
        return None
    if len(numbers) == 1:
        return 0.0
    avg = mean(numbers)
    return math.sqrt(sum((v - avg) ** 2 for v in numbers) / len(numbers))


def mean_or_none(values: Iterable[float]) -> Optional[float]:
    numbers = [float(v) for v in values]
    return mean(numbers) if numbers else None


def round_or_none(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def flatten_group_models(groups: Iterable[Dict[str, Any]]) -> List[str]:
    seen: List[str] = []
    for group in groups:
        for model in group.get("judge_models", []):
            if model not in seen:
                seen.append(model)
    return seen


def find_default_legacy_scores_jsonl() -> Optional[Path]:
    candidates = [
        LEGACY_RESULTS_DIR / "latest_per_game_image_scores.jsonl",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def ensure_local_artifact_tool_link() -> None:
    if (LOCAL_ARTIFACT_TOOL / "dist" / "artifact_tool.mjs").is_file():
        return
    if not (BUNDLED_ARTIFACT_TOOL / "dist" / "artifact_tool.mjs").is_file():
        raise FileNotFoundError(f"Bundled artifact-tool package not found at {BUNDLED_ARTIFACT_TOOL}")
    local_scope = LOCAL_NODE_MODULES / "@oai"
    local_scope.mkdir(parents=True, exist_ok=True)
    if LOCAL_ARTIFACT_TOOL.exists():
        raise RuntimeError(
            f"Local artifact-tool package exists but is incomplete: {LOCAL_ARTIFACT_TOOL}. "
            "Please remove it manually or update the path."
        )
    try:
        os.symlink(BUNDLED_ARTIFACT_TOOL, LOCAL_ARTIFACT_TOOL, target_is_directory=True)
        return
    except OSError:
        pass
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(LOCAL_ARTIFACT_TOOL), str(BUNDLED_ARTIFACT_TOOL)],
        check=True,
        cwd=str(ABLATION_ROOT),
        shell=False,
    )


def find_node_executable() -> str:
    env_node = os.getenv("CODEX_NODE_PATH")
    if env_node and Path(env_node).is_file():
        return env_node
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin"
        / "node.exe"
    )
    if bundled.is_file():
        return str(bundled)
    node = shutil.which("node")
    if node:
        return node
    raise FileNotFoundError("Unable to locate a Node.js executable for workbook export.")


def export_workbook(mode: str, payload_path: Path, output_path: Path) -> None:
    ensure_local_artifact_tool_link()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        find_node_executable(),
        str(WORKBOOK_EXPORT_SCRIPT),
        "--mode",
        mode,
        "--input",
        str(payload_path),
        "--output",
        str(output_path),
    ]
    subprocess.run(command, check=True, cwd=str(ABLATION_ROOT))


def export_workbook_payload(mode: str, payload: Any, output_path: Path) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        temp_path = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    try:
        export_workbook(mode, temp_path, output_path)
    finally:
        temp_path.unlink(missing_ok=True)


_LEGACY_SCORE_MODULE: Any = None


def load_legacy_score_module() -> Any:
    global _LEGACY_SCORE_MODULE
    if _LEGACY_SCORE_MODULE is not None:
        return _LEGACY_SCORE_MODULE
    spec = importlib.util.spec_from_file_location("legacy_multiview_score", LEGACY_SCORE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load legacy scorer from {LEGACY_SCORE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _LEGACY_SCORE_MODULE = module
    return module


def get_dimensions() -> List[str]:
    try:
        module = load_legacy_score_module()
        dims = list(getattr(module, "DIMENSIONS", []))
        return dims or list(DEFAULT_DIMENSIONS)
    except Exception:
        return list(DEFAULT_DIMENSIONS)
