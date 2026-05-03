# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import random
import json
from project_paths import path_in_project

BASE = "http://127.0.0.1:5001"

# 直接读取存档文件
save_path = path_in_project("saves", "main.json")
with open(save_path, "r", encoding="utf-8") as f:
    save_data = json.load(f)

gs = save_data.get("global_state", {})
cw = gs.get("core_worldview", {})
print(f"存档世界观标题: {cw.get('title', 'N/A')}")
print(f"存档属性: {save_data.get('protagonist_attr', {})}")

# 获取存档的游戏配置（用于生成初始选项）
protagonist_attr = save_data.get("protagonist_attr", {})
game_theme = cw.get("game_style", "古典玄幻修仙")
difficulty = save_data.get("difficulty", "中等")

print(f"\n游戏主题: {game_theme}")
print(f"难度: {difficulty}")

# 生成初始选项
print("\n=== 生成初始场景 ===")
# 从存档中提取初始选项
# 这个世界观没有 initial_options，我们需要用 generate-option 来生成第一个场景

# 先试着用 "开始游戏" 作为第一个选项
print("用 '开始游戏' 触发第一个场景...")
r = requests.post(f"{BASE}/generate-option", json={
    "option": "开始游戏",
    "globalState": gs,
    "optionIndex": 0,
    "sceneId": "initial"
}, timeout=600)

result = r.json()
print(f"API状态: {result.get('status')}")
if result.get("status") == "success":
    scene = result.get("scene", "")
    options = result.get("options", [])
    print(f"\n场景: {str(scene)[:300]}")
    print(f"\n选项数: {len(options)}")
    for i, opt in enumerate(options):
        opt_text = opt if isinstance(opt, str) else opt.get("text", str(opt))
        print(f"  [{i}] {opt_text}")
else:
    print(f"错误: {result.get('message', 'unknown')}")
