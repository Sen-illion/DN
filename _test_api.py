# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import random
import time

BASE = "http://127.0.0.1:5001"
TIMEOUT = 600

def api_post(path, data, timeout=TIMEOUT):
    print(f"  -> POST {path}", flush=True)
    resp = requests.post(f"{BASE}{path}", json=data, timeout=timeout)
    result = resp.json()
    print(f"  <- status={result.get('status')}", flush=True)
    if result.get("status") != "success":
        print(f"  ❌ API错误: {result.get('message', 'unknown')}", flush=True)
        return None
    return result

print("=" * 50, flush=True)
print("🎮 开始游戏", flush=True)
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
    print("世界观生成失败！", flush=True)
    sys.exit(1)

gs = gs_result.get("globalState", {})
game_id = gs.get("game_id", "unknown")
print(f"✅ 游戏ID: {game_id}", flush=True)

initial_opts = gs.get("initial_options", [])
if not initial_opts:
    initial_opts = ["深入研究", "四处探索"]
print(f"🗺️ 初始选项: {initial_opts}", flush=True)

# Step 2: 玩5-6轮
current_gs = gs
scene_id = "initial"
all_choices = []

for round_num in range(6):
    if round_num == 0:
        opts = initial_opts
    else:
        opts = current_opts

    if not opts:
        print(f"⚠️ 第{round_num+1}轮没有选项，结束", flush=True)
        break

    idx = random.randint(0, len(opts) - 1)
    chosen = opts[idx]
    opt_text = chosen if isinstance(chosen, str) else chosen.get("text", str(chosen))
    all_choices.append((round_num + 1, opt_text))

    print(f"\n🎮 Round {round_num+1}: 选择「{opt_text}」", flush=True)

    data = {
        "option": opt_text,
        "globalState": current_gs,
        "optionIndex": idx,
        "sceneId": scene_id,
    }
    result = api_post("/generate-option", data)

    if not result:
        print(f"❌ 第{round_num+1}轮失败", flush=True)
        break

    current_gs = result.get("globalState", current_gs)
    scene = result.get("scene", "")
    scene_preview = str(scene).replace('\n', ' ').strip()[:150]
    print(f"📖 场景: {scene_preview}...", flush=True)

    current_opts = result.get("options", [])
    if current_opts:
        print(f"✅ 获得 {len(current_opts)} 个新选项:", flush=True)
        for i, opt in enumerate(current_opts):
            opt_t = opt if isinstance(opt, str) else opt.get("text", str(opt))
            print(f"  [{i}] {opt_t}", flush=True)
    else:
        print("⚠️ 没有更多选项，游戏结束", flush=True)
        break

# 汇总
print("\n" + "=" * 50, flush=True)
print("📊 游戏报告", flush=True)
print("=" * 50, flush=True)
print(f"🎮 游戏ID: {game_id}", flush=True)
print(f"🔀 共 {len(all_choices)} 轮选择:", flush=True)
for r, choice in all_choices:
    print(f"  Round {r}: {choice}", flush=True)
print("✅ 完成！", flush=True)
