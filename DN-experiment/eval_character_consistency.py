# -*- coding: utf-8 -*-
"""
角色一致性评估实验：双标注 + Cohen's Kappa + 仲裁。

两个 LLM 标注员独立对每条故事打分（角色一致性、流畅度、整体质量），
计算 Cohen's Kappa 衡量一致性，分差 ≥ 2 时由第三个 LLM 仲裁。

运行：
  python DN-experiment/eval_character_consistency.py
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 路径 & 编码
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXPERIMENT_DIR = Path(__file__).resolve().parent

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_LOG_DIR = _EXPERIMENT_DIR / "eval_results"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(_LOG_DIR / "eval_run.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")

# ---------------------------------------------------------------------------
# OpenAI SDK (通过 yunwu.ai 代理访问所有模型)
# ---------------------------------------------------------------------------
from openai import OpenAI  # noqa: E402
from tenacity import (  # noqa: E402
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

DIMENSIONS = ["character_consistency", "fluency", "overall_quality"]
DIMENSION_ZH = {
    "character_consistency": "角色一致性",
    "fluency": "流畅度",
    "overall_quality": "整体质量",
}
_ZH_TO_EN = {v: k for k, v in DIMENSION_ZH.items()}

# ---------------------------------------------------------------------------
# 模型配置（复用 .env 中已有的密钥）
# ---------------------------------------------------------------------------
ANNOTATOR_A = {
    "name": "claude-haiku",
    "model": os.getenv("Origin_Segment_Analyst_MODEL", "claude-haiku-4-5-20251001-thinking"),
    "api_key": os.getenv("Origin_Segment_Analyst_API_KEY", ""),
    "base_url": os.getenv("Origin_Segment_Analyst_BASE_URL", "https://yunwu.ai/v1"),
}

ANNOTATOR_B = {
    "name": "gemini-3.1-pro",
    "model": os.getenv("VISION_REF_MODEL", "gemini-3.1-pro-preview"),
    "api_key": os.getenv("VISION_REF_API_KEY", ""),
    "base_url": os.getenv("VISION_REF_BASE_URL", "https://yunwu.ai/v1"),
}

ARBITRATOR = {
    "name": "claude-opus",
    "model": os.getenv("Camera_Analyst_MODEL", "claude-opus-4-6"),
    "api_key": os.getenv("Camera_Analyst_API_KEY", ""),
    "base_url": os.getenv("Camera_Analyst_BASE_URL", "https://yunwu.ai/v1"),
}


def _build_client(cfg: dict) -> OpenAI:
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


# ---------------------------------------------------------------------------
# 1. 数据加载
# ---------------------------------------------------------------------------
def load_game_data() -> List[Dict[str, Any]]:
    """扫描 DN-experiment 下所有 game 文件夹，拼接双段剧情。"""
    games: List[Dict[str, Any]] = []

    for folder in sorted(_EXPERIMENT_DIR.iterdir()):
        if not folder.is_dir() or folder.name.startswith(("__", "eval_results")):
            continue
        jsons = sorted(folder.glob("*.json"))
        if not jsons:
            continue

        segments: Dict[int, Dict] = {}
        for jf in jsons:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            idx = data.get("segment_index")
            if isinstance(idx, int):
                segments[idx] = data

        if 1 not in segments:
            continue

        seg1 = segments[1]
        seg2 = segments.get(2)

        full_scene = seg1.get("scene", "")
        if seg2:
            full_scene += "\n\n---\n\n" + seg2.get("scene", "")

        char_setting = _extract_character_setting(seg1.get("prompt", ""))

        protagonist_canonical = seg1.get("protagonist_canonical") or (seg2.get("protagonist_canonical") if seg2 else None)
        protagonist_block = ""
        if isinstance(protagonist_canonical, dict) and protagonist_canonical:
            parts_pc = []
            for k, v in protagonist_canonical.items():
                if v:
                    parts_pc.append(f"- {k}: {v}")
            if parts_pc:
                protagonist_block = "【主角规范信息（叙事用）】\n" + "\n".join(parts_pc)

        games.append({
            "game_id": seg1.get("game_id", folder.name),
            "folder": folder.name,
            "theme_item_id": seg1.get("theme_item_id"),
            "full_scene": full_scene,
            "character_setting": char_setting,
            "protagonist_canonical": protagonist_block,
            "segment_count": 2 if seg2 else 1,
        })

    return games


def _extract_character_setting(prompt_raw: str) -> str:
    """从 prompt 字段中提取角色设定（subject / face_system / clothing_system）。"""
    if not prompt_raw:
        return ""

    json_str = prompt_raw
    fence_match = re.search(r"```(?:json)?\s*(\{.*)", prompt_raw, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1)
        end = json_str.rfind("```")
        if end != -1:
            json_str = json_str[:end]

    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError:
        brace_start = json_str.find("{")
        if brace_start == -1:
            return ""
        depth, end_idx = 0, brace_start
        for i, ch in enumerate(json_str[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_idx = i + 1
                    break
        try:
            obj = json.loads(json_str[brace_start:end_idx])
        except json.JSONDecodeError:
            return ""

    parts: List[str] = []

    subject = obj.get("subject")
    if isinstance(subject, dict):
        for key in ("body_traits", "outfit", "pose"):
            items = subject.get(key, [])
            if isinstance(items, list) and items:
                parts.append(f"【{key}】\n" + "\n".join(f"- {x}" for x in items))

    for section in ("face_system", "hair_system", "clothing_system"):
        items = obj.get(section, [])
        if isinstance(items, list) and items:
            parts.append(f"【{section}】\n" + "\n".join(f"- {x}" for x in items))

    env_chars = obj.get("environment", {}).get("characters", [])
    if isinstance(env_chars, list) and env_chars:
        parts.append("【配角描述】\n" + "\n".join(f"- {x}" for x in env_chars))

    mood = obj.get("mood", [])
    if isinstance(mood, list) and mood:
        parts.append("【氛围/情绪基调】\n" + "\n".join(f"- {x}" for x in mood))

    return "\n\n".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# 2. 评估 Prompt
# ---------------------------------------------------------------------------
EVAL_SYSTEM_PROMPT = """\
你是一名专业的文学评论家和叙事分析师。你的任务是对一段互动小说/故事进行质量评估。
请严格按照给定的评分标准打分，并给出简短理由。
你必须返回且仅返回一个 JSON 对象，不要添加任何其他文字。"""

EVAL_USER_TEMPLATE = """\
## 角色设定参考（图像描述）

{character_setting}

{protagonist_canonical}

## 完整故事文本

{story_text}

## 评分要求

请从以下 3 个维度对故事打分（1～5 分），并给出简短理由。

### 1. 角色一致性（character_consistency）
评分标准：
- 1 分：完全 OOC（Out Of Character），角色行为性格完全相反
- 2 分：经常崩人设，角色行为与设定频繁矛盾
- 3 分：偶尔崩人设，但大体还行
- 4 分：基本一致，很少崩
- 5 分：全程符合设定，行为、语言、决策完全匹配角色设定

### 2. 流畅度（fluency）
本维度同时评价"局部语言质量"和"结构连贯性"两个方面，取二者的较低分。
- **局部语言质量**：句子是否通顺、用词是否恰当、有无病句或语法错误。
- **结构连贯性**：段落/章节之间是否衔接流畅，有无明显的截断、重复叙述或视角/时间线突变。
评分标准：
- 1 分：语句不通顺且结构严重断裂
- 2 分：语句经常不通顺，或存在明显结构断裂（如文本截断、段落间矛盾重叙）
- 3 分：局部语言尚可但结构衔接有瑕疵，或语言一般但结构完整
- 4 分：语言通顺自然，结构衔接顺畅，仅有微小瑕疵
- 5 分：语言优美流畅，段落衔接无缝，读感极佳

### 3. 整体质量（overall_quality）
综合逻辑、连贯性、有趣度。
- 1 分：很差
- 2 分：较差
- 3 分：一般
- 4 分：较好
- 5 分：优秀

请返回如下 JSON（不要包含任何其他内容）：
```json
{{
  "character_consistency": {{"score": <1-5>, "reason": "<简短理由>"}},
  "fluency": {{"score": <1-5>, "reason": "<简短理由>"}},
  "overall_quality": {{"score": <1-5>, "reason": "<简短理由>"}}
}}
```"""

ARBITRATOR_SYSTEM_PROMPT = """\
你是一名资深文学评审仲裁员。两位评审员对同一个故事的评分出现了较大分歧，\
你需要查看故事内容和两位评审的评分与理由，给出最终的仲裁评分。
你必须返回且仅返回一个 JSON 对象，不要添加任何其他文字。"""

ARBITRATOR_USER_TEMPLATE = """\
## 角色设定参考（图像描述）

{character_setting}

{protagonist_canonical}

## 完整故事文本

{story_text}

## 两位评审的评分

### 评审 A（{annotator_a_name}）
{annotator_a_scores}

### 评审 B（{annotator_b_name}）
{annotator_b_scores}

## 需要仲裁的维度

以下维度两位评审分差 ≥ 2，请给出你的最终评分和理由：
{dimensions_to_arbitrate}

请返回如下 JSON（仅包含需要仲裁的维度）：
```json
{{
  "<dimension>": {{"score": <1-5>, "reason": "<仲裁理由>"}}
}}
```"""


# ---------------------------------------------------------------------------
# 3. LLM 调用
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=5, max=60),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)
def _call_llm(cfg: dict, system: str, user: str) -> str:
    """调用 LLM 并返回文本响应。"""
    client = _build_client(cfg)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=8192,
    )
    content = resp.choices[0].message.content or ""
    return content.strip()


def _strip_thinking(raw: str) -> str:
    """Strip <thinking>...</thinking> and similar blocks from thinking-model responses."""
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<reflection>.*?</reflection>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


def _extract_json_block(raw: str) -> Optional[str]:
    """Extract the outermost JSON object from text, handling nested braces correctly."""
    cleaned = _strip_thinking(raw)

    fence_match = re.search(r"```(?:json)?\s*(\{.*)", cleaned, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
        end_fence = text.find("```")
        if end_fence != -1:
            text = text[:end_fence]
    else:
        first_brace = cleaned.find("{")
        if first_brace == -1:
            return None
        text = cleaned[first_brace:]

    depth, start_idx = 0, None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start_idx = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start_idx is not None:
                return text[start_idx : i + 1]
    return None


def _parse_scores(raw: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """从 LLM 返回中解析评分 JSON。支持中文/英文维度名。"""
    candidate = _extract_json_block(raw)
    if candidate is None:
        return None

    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    # 模型有时用中文维度名返回，统一映射为英文
    normalized: Dict[str, Any] = {}
    for k, v in obj.items():
        en_key = _ZH_TO_EN.get(k, k)
        normalized[en_key] = v

    for dim in DIMENSIONS:
        entry = normalized.get(dim)
        if not isinstance(entry, dict) or "score" not in entry:
            return None
        s = entry["score"]
        if not isinstance(s, (int, float)) or not (1 <= s <= 5):
            return None
        entry["score"] = int(round(s))

    return normalized


def evaluate_story(cfg: dict, game: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    """用指定模型评估单个故事，最多重试 3 次解析。"""
    user_msg = EVAL_USER_TEMPLATE.format(
        character_setting=game["character_setting"] or "（无角色设定参考信息）",
        protagonist_canonical=game.get("protagonist_canonical") or "",
        story_text=game["full_scene"],
    )
    for attempt in range(3):
        try:
            raw = _call_llm(cfg, EVAL_SYSTEM_PROMPT, user_msg)
            scores = _parse_scores(raw)
            if scores is not None:
                return scores
            preview = raw[:500].replace("\n", "\\n")
            log.warning("%s 返回格式解析失败 (attempt %d)，预览: %s", cfg["name"], attempt + 1, preview)
        except Exception as e:
            log.warning("%s 调用异常: %s", cfg["name"], e)
        time.sleep(3)
    return None


def arbitrate(game: Dict[str, Any], scores_a: dict, scores_b: dict,
              name_a: str, name_b: str, dims: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
    """仲裁分歧维度。"""
    def _fmt(scores: dict) -> str:
        lines = []
        for d in DIMENSIONS:
            e = scores[d]
            lines.append(f"- {DIMENSION_ZH[d]}: {e['score']} 分 — {e.get('reason', '')}")
        return "\n".join(lines)

    dims_text = "\n".join(
        f"- {DIMENSION_ZH[d]}：评审A={scores_a[d]['score']}，评审B={scores_b[d]['score']}"
        for d in dims
    )

    user_msg = ARBITRATOR_USER_TEMPLATE.format(
        character_setting=game["character_setting"] or "（无角色设定参考信息）",
        protagonist_canonical=game.get("protagonist_canonical") or "",
        story_text=game["full_scene"],
        annotator_a_name=name_a,
        annotator_b_name=name_b,
        annotator_a_scores=_fmt(scores_a),
        annotator_b_scores=_fmt(scores_b),
        dimensions_to_arbitrate=dims_text,
    )
    for attempt in range(3):
        try:
            raw = _call_llm(ARBITRATOR, ARBITRATOR_SYSTEM_PROMPT, user_msg)
            parsed = _parse_scores_partial(raw, dims)
            if parsed is not None:
                return parsed
            preview = raw[:500].replace("\n", "\\n")
            log.warning("仲裁返回解析失败 (attempt %d)，预览: %s", attempt + 1, preview)
        except Exception as e:
            log.warning("仲裁调用异常: %s", e)
        time.sleep(3)
    return None


def _parse_scores_partial(raw: str, expected_dims: List[str]) -> Optional[Dict[str, Dict[str, Any]]]:
    """解析仲裁返回（可能仅含部分维度）。支持中文/英文维度名。"""
    candidate = _extract_json_block(raw)
    if candidate is None:
        return None

    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    # 模型有时用中文维度名返回，统一映射为英文
    normalized: Dict[str, Any] = {}
    for k, v in obj.items():
        en_key = _ZH_TO_EN.get(k, k)
        normalized[en_key] = v

    result: Dict[str, Dict[str, Any]] = {}
    for dim in expected_dims:
        entry = normalized.get(dim)
        if isinstance(entry, dict) and "score" in entry:
            s = entry["score"]
            if isinstance(s, (int, float)) and 1 <= s <= 5:
                result[dim] = {"score": int(round(s)), "reason": entry.get("reason", "")}

    return result if result else None


# ---------------------------------------------------------------------------
# 4. Cohen's Kappa（二次加权）
# ---------------------------------------------------------------------------
def weighted_cohens_kappa(ratings_a: List[int], ratings_b: List[int], k: int = 5) -> float:
    """计算二次加权 Cohen's Kappa，适用于 1-k 有序量表。"""
    n = len(ratings_a)
    if n == 0:
        return 0.0

    confusion = [[0] * k for _ in range(k)]
    for a, b in zip(ratings_a, ratings_b):
        confusion[a - 1][b - 1] += 1

    weights = [[0.0] * k for _ in range(k)]
    for i in range(k):
        for j in range(k):
            weights[i][j] = ((i - j) ** 2) / ((k - 1) ** 2)

    row_sums = [sum(confusion[i]) for i in range(k)]
    col_sums = [sum(confusion[i][j] for i in range(k)) for j in range(k)]

    po = 0.0
    pe = 0.0
    for i in range(k):
        for j in range(k):
            po += weights[i][j] * confusion[i][j] / n
            pe += weights[i][j] * (row_sums[i] * col_sums[j]) / (n * n)

    if pe == 1.0:
        return 1.0 if po == 0.0 else 0.0

    return 1.0 - po / pe


def interpret_kappa(kappa: float) -> str:
    if kappa >= 0.81:
        return "几乎完全一致 (Almost Perfect)"
    if kappa >= 0.61:
        return "高度一致 (Substantial)"
    if kappa >= 0.41:
        return "中等一致 (Moderate)"
    if kappa >= 0.21:
        return "一般一致 (Fair)"
    if kappa >= 0.0:
        return "轻微一致 (Slight)"
    return "低于随机 (Poor)"


# ---------------------------------------------------------------------------
# 5. 主流程
# ---------------------------------------------------------------------------
def _save_results(results: List[Dict], all_a: Dict, all_b: Dict) -> None:
    """Save results incrementally so partial progress is preserved on crash."""
    out_dir = _EXPERIMENT_DIR / "eval_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    kappa_results: Dict[str, float] = {}
    for d in DIMENSIONS:
        if len(all_a[d]) < 2:
            kappa_results[d] = float("nan")
            continue
        kappa_results[d] = weighted_cohens_kappa(all_a[d], all_b[d])

    all_ratings_a: List[int] = []
    all_ratings_b: List[int] = []
    for d in DIMENSIONS:
        all_ratings_a.extend(all_a[d])
        all_ratings_b.extend(all_b[d])
    overall_kappa = weighted_cohens_kappa(all_ratings_a, all_ratings_b) if len(all_ratings_a) >= 2 else float("nan")

    payload = {
        "meta": {
            "eval_time_utc": datetime.now(timezone.utc).isoformat(),
            "annotator_a": {"name": ANNOTATOR_A["name"], "model": ANNOTATOR_A["model"]},
            "annotator_b": {"name": ANNOTATOR_B["name"], "model": ANNOTATOR_B["model"]},
            "arbitrator": {"name": ARBITRATOR["name"], "model": ARBITRATOR["model"]},
            "total_games": len(results),
        },
        "kappa": {**{d: kappa_results[d] for d in DIMENSIONS}, "overall": overall_kappa},
        "results": results,
    }
    (out_dir / "eval_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
    )

    with open(out_dir / "eval_summary.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        header = ["game_id", "folder", "theme_id"]
        for d in DIMENSIONS:
            header.extend([f"{d}_A", f"{d}_B", f"{d}_final", f"{d}_source"])
        writer.writerow(header)
        for r in results:
            row = [r["game_id"], r["folder"], r["theme_item_id"]]
            for d in DIMENSIONS:
                row.append(r["annotator_a"]["scores"][d]["score"])
                row.append(r["annotator_b"]["scores"][d]["score"])
                row.append(r["final_scores"][d]["score"])
                row.append(r["final_scores"][d]["source"])
            writer.writerow(row)

    arb_count = sum(1 for r in results if r["dims_arbitrated"])
    lines = [
        "=" * 50, "  Cohen's Kappa 一致性报告", "=" * 50,
        f"  评估时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"  标注员 A: {ANNOTATOR_A['name']} ({ANNOTATOR_A['model']})",
        f"  标注员 B: {ANNOTATOR_B['name']} ({ANNOTATOR_B['model']})",
        f"  仲裁员:   {ARBITRATOR['name']} ({ARBITRATOR['model']})",
        f"  评估故事数: {len(results)}", "",
        "--- 各维度 Kappa ---",
    ]
    for d in DIMENSIONS:
        k = kappa_results[d]
        lines.append(f"  {DIMENSION_ZH[d]:　<8s}: {k:.4f}  {interpret_kappa(k)}")
    lines.extend([
        "", f"  总体 Kappa: {overall_kappa:.4f}  {interpret_kappa(overall_kappa)}", "",
        f"  可靠性: {'可靠 (Kappa >= 0.7)' if overall_kappa >= 0.7 else '不够可靠 (Kappa < 0.7)'}",
        "", "--- 原始评分对比 ---",
    ])
    for d in DIMENSIONS:
        a_vals, b_vals = all_a[d], all_b[d]
        lines.append(f"  {DIMENSION_ZH[d]}:")
        lines.append(f"    A: {a_vals}")
        lines.append(f"    B: {b_vals}")
        diffs = [abs(a - b) for a, b in zip(a_vals, b_vals)]
        lines.append(f"    差值: {diffs}")
        lines.append(f"    平均差值: {sum(diffs)/len(diffs):.2f}" if diffs else "    无数据")
    lines.extend(["", f"  仲裁触发: {arb_count}/{len(results)} 个故事", ""])
    (out_dir / "kappa_report.txt").write_text("\n".join(lines), encoding="utf-8")

    return kappa_results, overall_kappa


def _load_existing_results() -> Tuple[List[Dict[str, Any]], Dict[str, List[int]], Dict[str, List[int]], set]:
    """Load previously saved results to support resuming."""
    results_path = _EXPERIMENT_DIR / "eval_results" / "eval_results.json"
    if not results_path.exists():
        return [], {d: [] for d in DIMENSIONS}, {d: [] for d in DIMENSIONS}, set()

    try:
        payload = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception:
        return [], {d: [] for d in DIMENSIONS}, {d: [] for d in DIMENSIONS}, set()

    results = payload.get("results", [])
    all_a: Dict[str, List[int]] = {d: [] for d in DIMENSIONS}
    all_b: Dict[str, List[int]] = {d: [] for d in DIMENSIONS}
    evaluated_folders: set = set()

    for r in results:
        evaluated_folders.add(r["folder"])
        for d in DIMENSIONS:
            all_a[d].append(r["annotator_a"]["scores"][d]["score"])
            all_b[d].append(r["annotator_b"]["scores"][d]["score"])

    return results, all_a, all_b, evaluated_folders


def main() -> int:
    log.info("=" * 60)
    log.info("  角色一致性评估实验")
    log.info("  双标注 + Cohen's Kappa + 仲裁")
    log.info("=" * 60)

    games = load_game_data()
    if not games:
        log.error("未在 DN-experiment 下找到任何有效 game 数据")
        return 1
    log.info("共加载 %d 个 game", len(games))
    for g in games:
        log.info("  - %s (segments=%d, scene_len=%d)", g["folder"], g["segment_count"], len(g["full_scene"]))

    results, all_a, all_b, evaluated_folders = _load_existing_results()
    if evaluated_folders:
        log.info("已有 %d 个已评估结果，将跳过这些 game", len(evaluated_folders))

    remaining = [g for g in games if g["folder"] not in evaluated_folders]
    if not remaining:
        log.info("所有 game 已评估完毕，重新生成汇总报告")
        _save_results(results, all_a, all_b)
        log.info("报告已更新")
        return 0

    log.info("待评估: %d 个 game", len(remaining))
    skipped: List[str] = []

    for i, game in enumerate(remaining):
        log.info("─" * 50)
        log.info("[%d/%d] 评估: %s (总进度 %d/%d)", i + 1, len(remaining), game["folder"],
                 len(results) + 1, len(games))
        log.info("─" * 50)

        log.info("  → 标注员 A (%s) 评估中...", ANNOTATOR_A["name"])
        scores_a = evaluate_story(ANNOTATOR_A, game)
        if scores_a is None:
            log.warning("  标注员 A 评估失败，跳过此 game")
            skipped.append(game["folder"])
            continue

        for d in DIMENSIONS:
            log.info("    %s: %d 分", DIMENSION_ZH[d], scores_a[d]["score"])

        log.info("  → 标注员 B (%s) 评估中...", ANNOTATOR_B["name"])
        scores_b = evaluate_story(ANNOTATOR_B, game)
        if scores_b is None:
            log.warning("  标注员 B 评估失败，跳过此 game")
            skipped.append(game["folder"])
            continue

        for d in DIMENSIONS:
            log.info("    %s: %d 分", DIMENSION_ZH[d], scores_b[d]["score"])

        for d in DIMENSIONS:
            all_a[d].append(scores_a[d]["score"])
            all_b[d].append(scores_b[d]["score"])

        dims_need_arb = [
            d for d in DIMENSIONS
            if abs(scores_a[d]["score"] - scores_b[d]["score"]) >= 2
        ]

        final_scores: Dict[str, Dict[str, Any]] = {}
        arb_scores: Optional[Dict] = None

        if dims_need_arb:
            log.info("  ⚠ 分歧维度（差≥2）: %s", ", ".join(DIMENSION_ZH[d] for d in dims_need_arb))
            log.info("  → 仲裁员 (%s) 仲裁中...", ARBITRATOR["name"])
            arb_scores = arbitrate(
                game, scores_a, scores_b,
                ANNOTATOR_A["name"], ANNOTATOR_B["name"],
                dims_need_arb,
            )
            if arb_scores:
                for d in dims_need_arb:
                    if d in arb_scores:
                        log.info("    仲裁 %s: %d 分", DIMENSION_ZH[d], arb_scores[d]["score"])

        for d in DIMENSIONS:
            if arb_scores and d in arb_scores:
                final_scores[d] = arb_scores[d]
                final_scores[d]["source"] = "arbitration"
            else:
                avg = (scores_a[d]["score"] + scores_b[d]["score"]) / 2.0
                final_scores[d] = {
                    "score": round(avg),
                    "reason": f"平均值 ({scores_a[d]['score']}+{scores_b[d]['score']})/2={avg:.1f}",
                    "source": "average",
                }

        results.append({
            "game_id": game["game_id"],
            "folder": game["folder"],
            "theme_item_id": game["theme_item_id"],
            "annotator_a": {"name": ANNOTATOR_A["name"], "model": ANNOTATOR_A["model"], "scores": scores_a},
            "annotator_b": {"name": ANNOTATOR_B["name"], "model": ANNOTATOR_B["model"], "scores": scores_b},
            "arbitration": arb_scores,
            "final_scores": final_scores,
            "dims_arbitrated": dims_need_arb,
        })

        _save_results(results, all_a, all_b)
        log.info("  ✓ 已保存（累计 %d/%d 成功, %d 跳过）", len(results), len(games), len(skipped))

    if not results:
        log.error("所有 game 评估均失败")
        return 1

    kappa_results, overall_kappa = _save_results(results, all_a, all_b)

    log.info("=" * 60)
    log.info("  Cohen's Kappa 分析")
    log.info("=" * 60)
    for d in DIMENSIONS:
        k = kappa_results[d]
        log.info("  %s: Kappa = %.4f  [%s]", DIMENSION_ZH[d], k, interpret_kappa(k))
    log.info("  " + "─" * 40)
    log.info("  总体 Kappa: %.4f  [%s]", overall_kappa, interpret_kappa(overall_kappa))
    log.info("  可靠性判定: %s", "✓ 可靠 (Kappa >= 0.7)" if overall_kappa >= 0.7 else "✗ 不够可靠 (Kappa < 0.7)")

    log.info("=" * 60)
    log.info("  评分统计")
    log.info("=" * 60)
    for d in DIMENSIONS:
        finals = [r["final_scores"][d]["score"] for r in results]
        avg_f = sum(finals) / len(finals) if finals else 0
        log.info("  %s: 平均=%.2f  最低=%d  最高=%d", DIMENSION_ZH[d], avg_f, min(finals), max(finals))

    arb_count = sum(1 for r in results if r["dims_arbitrated"])
    log.info("  仲裁触发次数: %d/%d 个故事", arb_count, len(results))
    if skipped:
        log.info("  跳过的故事 (%d): %s", len(skipped), ", ".join(skipped))

    log.info("=" * 60)
    log.info("  评估完成 (%d/%d 成功)", len(results), len(games))
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
