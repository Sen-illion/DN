# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import random

BASE = "http://127.0.0.1:5001"

# Step 1: 列出存档
print("=== 存档列表 ===")
r = requests.get(f"{BASE}/list-saves", timeout=10)
print(r.json())

# Step 2: 加载存档 (main)
print("\n=== 加载存档 'main' ===")
r = requests.post(f"{BASE}/load-game", json={"saveName": "main"}, timeout=30)
result = r.json()
print(f"status: {result.get('status')}")
if result.get("status") == "success":
    gs = result.get("globalState", {})
    print(f"game_id: {gs.get('game_id', 'N/A')}")
    cw = gs.get("core_worldview", {})
    print(f"title: {cw.get('title', 'N/A')}")
    
    # Check what screen we're on
    print(f"current_screen: {gs.get('current_screen', 'N/A')}")
    
    # Get current options from gameplay screen
    # The gameplay options are stored in the globalState
    current_scene = gs.get("current_scene", "")
    options = gs.get("options", [])
    
    print(f"\ncurrent_scene: {str(current_scene)[:200]}")
    print(f"options: {options}")
else:
    print(f"Error: {result.get('message', 'unknown')}")
