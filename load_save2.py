# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import random
import json

BASE = "http://127.0.0.1:5001"

# Load the other save
save_name = "夏天-烟花-我的尸体"
print(f"=== 加载存档: {save_name} ===")
r = requests.post(f"{BASE}/load-game", json={"saveName": save_name}, timeout=30)
result = r.json()
print(f"status: {result.get('status')}")
if result.get("status") == "success":
    gs = result.get("globalState", {})
    print(f"game_id: {gs.get('game_id', 'N/A')}")
    cw = gs.get("core_worldview", {})
    print(f"title: {cw.get('title', 'N/A')}")
    
    # Check all keys
    print(f"\nglobalState keys: {list(gs.keys())}")
    
    # Try to find options and current scene
    current_scene = gs.get("current_scene", "")
    options = gs.get("options", [])
    initial_opts = gs.get("initial_options", [])
    
    print(f"\ncurrent_scene: {str(current_scene)[:300]}")
    print(f"options: {options[:5] if options else 'empty'}")
    print(f"initial_options: {initial_opts}")
    
    # Check gameplay state
    layer1 = gs.get("layer1", {})
    layer2 = gs.get("layer2", {})
    print(f"\nlayer1 keys: {list(layer1.keys())[:10] if layer1 else 'empty'}")
    print(f"layer2 keys: {list(layer2.keys())[:10] if layer2 else 'empty'}")
    
    # Try to play an option
    # First, let's see what options are available in layer1
    if layer1:
        first_key = list(layer1.keys())[0]
        first_data = layer1[first_key]
        print(f"\nFirst layer1 key: {first_key}")
        print(f"Data type: {type(first_data)}")
        if isinstance(first_data, dict):
            print(f"Data keys: {list(first_data.keys())}")
            scene = first_data.get("scene", "")
            opts = first_data.get("next_options", [])
            print(f"Scene: {str(scene)[:200]}")
            print(f"Options: {opts[:5]}")
else:
    print(f"Error: {result.get('message', 'unknown')}")
