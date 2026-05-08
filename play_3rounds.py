# -*- coding: utf-8 -*-
"""自动玩文本冒险游戏并记录日志"""
import sys, io, os, json, time, random
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests

BASE = "http://127.0.0.1:5001"
TIMEOUT = 900  # 15分钟超时

LOG_FILE = "C:/Users/User/AppData/Local/Temp/game_play_log.txt"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)

def api_post(path, data, timeout=TIMEOUT):
    log(f"API请求: {path}")
    t0 = time.time()
    try:
        resp = requests.post(f"{BASE}{path}", json=data, timeout=timeout)
        elapsed = time.time() - t0
        result = resp.json()
        log(f"  <- {result.get('status', '?')} ({elapsed:.0f}s)")
        return result
    except requests.exceptions.Timeout:
        log(f"  <- 超时 ({time.time()-t0:.0f}s)")
        return None
    except Exception as e:
        log(f"  <- 错误: {e}")
        return None

def play_round(gs, choice_text, choice_idx, scene_id):
    log(f"选择: {choice_text}")
    result = api_post("/generate-option", {
        "option": choice_text,
        "globalState": gs,
        "optionIndex": choice_idx,
        "sceneId": scene_id,
    })
    if not result or result.get("status") != "success":
        log("  生成失败!")
        return None, None, []

    new_gs = result.get("globalState", gs)
    scene = result.get("scene", "")
    options = result.get("options", [])
    new_scene_id = result.get("sceneId", scene_id)

    # 记录场景摘要
    scene_preview = str(scene).replace('\n', ' ').strip()[:200]
    log(f"场景: {scene_preview}")

    log(f"选项数: {len(options)}")
    for i, opt in enumerate(options):
        opt_t = opt if isinstance(opt, str) else opt.get("text", str(opt))
        log(f"  [{i}] {opt_t}")

    return new_gs, new_scene_id, options

def main():
    # 日志直接打印到控制台

    log("=" * 50)
    log("开始自动游戏: 新世纪福音战士")
    log("设置: 普通x4 / 困难 / 唯美 / 动漫")
    log("目标: 玩3轮后结束")
    log("=" * 50)

    # Step 1: 生成世界观
    log("--- Step 1: 生成世界观 ---")
    result = api_post("/generate-worldview", {
        "gameTheme": "新世纪福音战士",
        "protagonistAttr": {"looks": "普通", "intelligence": "普通", "stamina": "普通", "charisma": "普通"},
        "difficulty": "困难",
        "toneKey": "aesthetic",
        "imageStyle": "anime"
    })

    if not result or result.get("status") != "success":
        log("世界观生成失败!")
        return

    gs = result.get("globalState", {})
    game_id = gs.get("game_id", "unknown")
    cw = gs.get("core_worldview", {})
    log(f"游戏ID: {game_id}")
    log(f"标题: {cw.get('title', 'N/A')}")

    # 初始选项
    initial_opts = ["深入研究", "四处探索"]
    log(f"初始选项: {initial_opts}")

    # Step 2: 玩3轮
    current_gs = gs
    scene_id = "initial"
    all_choices = []

    for round_num in range(3):
        log(f"\n--- Round {round_num+1} ---")
        opts = initial_opts if round_num == 0 else current_opts

        if not opts:
            log("没有可用选项，结束")
            break

        idx = random.randint(0, len(opts) - 1)
        chosen = opts[idx]
        opt_text = chosen if isinstance(chosen, str) else chosen.get("text", str(chosen))
        all_choices.append(opt_text)

        current_gs, scene_id, current_opts = play_round(current_gs, opt_text, idx, scene_id)

        if current_gs is None:
            log("回合出错，停止")
            break

    # Step 3: 报告
    log("\n" + "=" * 50)
    log("游戏报告")
    log("=" * 50)
    log(f"游戏ID: {game_id}")
    log(f"共玩 {len(all_choices)} 轮")
    for i, c in enumerate(all_choices):
        log(f"  Round {i+1}: {c}")
    log("=" * 50)
    log("完成!")

if __name__ == "__main__":
    main()
