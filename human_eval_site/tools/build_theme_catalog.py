from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
THEME_ROOT = REPO_ROOT / "DN-experiment-2.0"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "baseline_image_from_dn_text" / "run_20260430_145825"
SITE_DATA_ROOT = REPO_ROOT / "human_eval_site" / "data"
SITE_ASSETS_ROOT = REPO_ROOT / "human_eval_site" / "assets" / "themes"


DIMENSIONS = [
    {"id": "image_consistency", "label": "图片一致性", "help": "连续图片是否与对应文本中的人物、场景、动作、道具和氛围一致。"},
    {"id": "sequence_consistency", "label": "连续性", "help": "5 张图之间的人物形象、场景风格和时间推进是否稳定连续。"},
    {"id": "visual_quality", "label": "视觉质量", "help": "图片是否清晰自然，是否存在明显崩坏、乱码或异常。"},
    {"id": "image_text_alignment", "label": "图文匹配", "help": "整组图片是否准确表达这 5 段中文剧情。"},
    {"id": "overall", "label": "综合评分", "help": "该匿名方案作为一组连续图文结果的总体质量。"},
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def scene_preview(text: str, max_length: int = 22) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1] + "…"


def build_theme_case(theme_dir: Path, segments: int) -> dict | None:
    game_id = theme_dir.name.split("_", 2)[2]
    theme_id = theme_dir.name
    story_segments: list[str] = []
    ours_images: list[str] = []
    baseline_images: list[str] = []
    theme_asset_dir = SITE_ASSETS_ROOT / theme_id
    ours_asset_dir = theme_asset_dir / "ours"
    baseline_asset_dir = theme_asset_dir / "baseline"
    ours_asset_dir.mkdir(parents=True, exist_ok=True)
    baseline_asset_dir.mkdir(parents=True, exist_ok=True)

    for segment_index in range(1, segments + 1):
        json_path = theme_dir / f"{game_id}_{segment_index:03d}.json"
        ours_image = OUTPUT_ROOT / "IC-LoRA" / game_id / f"seg_{segment_index:03d}.png"
        baseline_image = OUTPUT_ROOT / "SDM-v2" / game_id / f"seg_{segment_index:03d}.png"
        if not json_path.exists() or not ours_image.exists() or not baseline_image.exists():
            return None

        sample = load_json(json_path)
        story_segments.append(str(sample.get("scene") or "").strip())
        ours_target = ours_asset_dir / f"seg_{segment_index:03d}.png"
        baseline_target = baseline_asset_dir / f"seg_{segment_index:03d}.png"
        shutil.copy2(ours_image, ours_target)
        shutil.copy2(baseline_image, baseline_target)
        ours_images.append(f"/assets/themes/{theme_id}/ours/seg_{segment_index:03d}.png")
        baseline_images.append(f"/assets/themes/{theme_id}/baseline/seg_{segment_index:03d}.png")

    if not all(story_segments):
        return None

    title = f"{theme_id} | {scene_preview(story_segments[0])}"
    return {
        "themeId": theme_id,
        "gameId": game_id,
        "title": title,
        "case": {
            "id": theme_id,
            "title": title,
            "prompt": [
                "请先完整阅读这 5 段连续中文剧情，再分别评估两个匿名方案的连续 5 张图片。",
                "重点观察人物身份、场景风格、关键动作和时间推进是否能在整组图像中保持稳定。"
            ],
            "context": [
                "每位评测者会被分配到不同的游戏主题，系统会通过邀请链接中的 token 固定该主题。",
                "两个匿名方案对应同一组文本，只比较它们的图像一致性、连续性和整体质量。"
            ],
            "storySegments": story_segments,
            "candidates": [
                {"system": "ours", "images": ours_images},
                {"system": "baseline", "images": baseline_images},
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build theme catalog for human eval site.")
    parser.add_argument("--segments", type=int, default=5, help="Number of story segments and images per theme.")
    parser.add_argument("--max-themes", type=int, default=10, help="Maximum number of themes to include.")
    args = parser.parse_args()

    if SITE_ASSETS_ROOT.exists():
        shutil.rmtree(SITE_ASSETS_ROOT)

    themes = []
    for theme_dir in sorted(THEME_ROOT.glob("theme_*_game_*")):
        built = build_theme_case(theme_dir, args.segments)
        if built is not None:
            themes.append(built)
        if len(themes) >= args.max_themes:
            break

    if not themes:
        raise SystemExit("No complete themes found.")

    catalog = {
        "studyTitle": "DN 游戏主题图文一致性人类测评",
        "instructions": [
            "每个邀请链接会固定分配一个游戏主题，评测者看到的不是同一主题，而是预先分配好的主题包。",
            "请先完整阅读 5 段中文剧情，再比较两个匿名方案各自的连续 5 张图片。",
            "完成评分后，结果会同时保存在浏览器本地，并自动回传到当前服务器。",
        ],
        "dimensions": DIMENSIONS,
        "themes": themes,
    }

    SITE_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    (SITE_DATA_ROOT / "theme_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {len(themes)} themes to {SITE_DATA_ROOT / 'theme_catalog.json'}")


if __name__ == "__main__":
    main()
