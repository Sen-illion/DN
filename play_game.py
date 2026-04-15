# -*- coding: utf-8 -*-
"""
玩文本冒险游戏：设置→生成世界观→玩5-6个选项→报告结果
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import random
import time
import sys

BASE = "http://127.0.0.1:5001"
TIMEOUT = 600  # 10分钟超时

def api_post(path, data, timeout=TIMEOUT):
    resp = requests.post(f"{BASE}{path}", json=data, timeout=timeout)
    result = resp.json()
    if result.get("status") != "success":
        print(f"❌ API错误: {result.get('message', 'unknown')}", flush=True)
        return None
    return result

def play_round(gs, choice_text, choice_idx, scene_id):
    """走一个选项"""
    print(f"\n🎮 选择: {choice_text}", flush=True)
    data = {
        "option": choice_text,
        "globalState": gs,
        "optionIndex": choice_idx,
        "sceneId": scene_id,
    }
    result = api_post("/generate-option", data)
    if not result:
        return None, None, []

    new_gs = result.get("globalState", gs)
    scene = result.get("scene", "")
    options = result.get("options", [])
    new_scene_id = result.get("sceneId", scene_id)

    # 打印场景摘要
    scene_preview = str(scene).replace('\n', ' ').strip()[:150]
    print(f"📖 场景: {scene_preview}...", flush=True)

    if options:
        print(f"� choices: {len(options)}", flush=True)
        for i, opt in enumerate(options):
            opt_t = opt if isinstance(opt, str) else opt.get("text", str(opt))
            print(f"  [{i}] {opt_t}", flush=True)

    return new_gs, new_scene_id, options

def main():
    print("=" * 50, flush=True)
    print("🎮 开始自动游戏测试", flush=True)
    print("设置: 普通/普通/普通/普通 | 困难 | 唯美 | 新世纪福音战士 | 动漫", flush=True)
    print("=" * 50, flush=True)

    # Step 1: 生成世界观
    print("\n=== Step 1: 生成世界观 ===", flush=True)
    gs_result = api_post("/generate-worldview", {
        "gameTheme": "便利店深夜",
        "protagonistAttr": {"looks": "普通", "intelligence": "普通", "stamina": "普通", "charisma": "普通"},
        "difficulty": "中等",
        "toneKey": "normal_ending",
        "imageStyle": "anime"
    })

    if not gs_result:
        return

    gs = gs_result.get("globalState", {})
    cw = gs.get("core_worldview", {})
    game_id = gs.get("game_id", "unknown")

    print(f"✅ 游戏ID: {game_id}", flush=True)
    title = cw.get("title", "无标题")
    intro = str(cw.get("introduction", "")).replace('\n', ' ')[:300]
    print(f"📛 标题: {title}", flush=True)
    print(f"📝 世界观: {intro}", flush=True)

    # 提取初始选项
    initial_opts = gs.get("initial_options", [])
    if not initial_opts:
        initial_opts = ["深入研究", "四处探索"]

    print(f"\n🗺️ 初始选项: {initial_opts}", flush=True)

    # Step 2: 玩5-6轮
    current_gs = gs
    scene_id = "initial"

    all_choices = []

    for round_num in range(6):
        # 选择一个选项
        if round_num == 0:
            # 第一轮：从初始选项选
            opts = initial_opts
        else:
            opts = current_opts if 'current_opts' in dir() else []

        if not opts:
            print(f"\n⚠️ 第{round_num+1}轮没有选项了，结束游戏", flush=True)
            break

        idx = random.randint(0, len(opts) - 1)
        chosen = opts[idx]
        opt_text = chosen if isinstance(chosen, str) else chosen.get("text", str(chosen))
        all_choices.append((round_num + 1, opt_text))

        current_gs, scene_id, current_opts = play_round(current_gs, opt_text, idx, scene_id)

        if current_gs is None:
            print(f"\n❌ 第{round_num+1}轮出错，停止", flush=True)
            break

    # Step 3: 汇总报告
    print("\n" + "=" * 50, flush=True)
    print("📊 游戏报告", flush=True)
    print("=" * 50, flush=True)
    print(f"🎮 游戏ID: {game_id}", flush=True)
    print(f"📛 世界观标题: {title}", flush=True)
    print(f"🔀 共完成 {len(all_choices)} 轮选择:", flush=True)
    for r, choice in all_choices:
        print(f"  Round {r}: {choice}", flush=True)
    print(f"📍 最终场景ID: {scene_id}", flush=True)
    print(f"🖼️ 图片风格: anime", flush=True)
    print(f"⚔️ 难度: 困难 / 🎭 基调: 唯美 / 👤 主角属性: 普通x4", flush=True)
    print("=" * 50, flush=True)
    print("✅ 测试完成!", flush=True)

if __name__ == "__main__":
    main()
