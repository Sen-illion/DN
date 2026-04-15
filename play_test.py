# -*- coding: utf-8 -*-
import requests
import json
import random
import sys
import os

BASE = "http://127.0.0.1:5001"

def generate_worldview():
    data = {
        "gameTheme": "新世纪福音战士",
        "protagonistAttr": {
            "looks": "普通",
            "intelligence": "普通",
            "stamina": "普通",
            "charisma": "普通"
        },
        "difficulty": "困难",
        "toneKey": "aesthetic",
        "imageStyle": "anime"
    }
    print("=== Step 1: Generating worldview ===", flush=True)
    resp = requests.post(f"{BASE}/generate-worldview", json=data, timeout=300)
    result = resp.json()
    print(f"Status: {result.get('status')}", flush=True)
    if result.get("status") != "success":
        print(f"Error: {result.get('message')}", flush=True)
        sys.exit(1)
    
    gs = result.get("globalState", {})
    game_id = gs.get("game_id", "unknown")
    cw = gs.get("core_worldview", {})
    print(f"Game ID: {game_id}", flush=True)
    print(f"Title: {cw.get('title', 'N/A')}", flush=True)
    intro = str(cw.get("introduction", ""))
    print(f"Introduction: {intro[:300]}", flush=True)
    return gs

def play_option(gs, option_text, option_index=0, scene_id=None):
    data = {
        "option": option_text,
        "globalState": gs,
        "optionIndex": option_index,
        "sceneId": scene_id,
    }
    print(f"\n=== Choosing: [{option_index}] {option_text} ===", flush=True)
    resp = requests.post(f"{BASE}/generate-option", json=data, timeout=300)
    result = resp.json()
    print(f"Status: {result.get('status')}", flush=True)
    if result.get("status") != "success":
        print(f"Error: {result.get('message')}", flush=True)
        return None, None, []
    
    new_gs = result.get("globalState", gs)
    scene = result.get("scene", "")
    options = result.get("options", [])
    
    print(f"Scene text: {str(scene)[:300]}", flush=True)
    print(f"Available options:", flush=True)
    for i, opt in enumerate(options):
        opt_text = opt if isinstance(opt, str) else opt.get("text", str(opt))
        print(f"  [{i}] {opt_text}", flush=True)
    
    new_scene_id = result.get("sceneId", scene_id)
    return new_gs, new_scene_id, options

def main():
    # Step 1: Generate worldview
    gs = generate_worldview()
    game_id = gs.get("game_id", "unknown")
    
    # Step 2: Get initial options from the worldview response
    # The worldview response includes initial options
    initial_options = gs.get("initial_options", [])
    # Also check the pregeneration cache endpoint
    print(f"\n=== Getting initial scene ===", flush=True)
    resp = requests.get(f"{BASE}/get-pregenerated-layer2", params={"gameId": game_id}, timeout=30)
    
    # Try to get initial scene data
    # First, let's play by choosing "开始游戏"
    gs, scene_id, options = play_option(gs, "开始游戏", 0, "initial")
    
    if not options:
        print("No options available after initial choice!", flush=True)
        return
    
    # Play 5-6 rounds
    for round_num in range(5):
        if not options:
            print("No more options! Game may have ended.", flush=True)
            break
        
        # Randomly pick an option
        idx = random.randint(0, len(options) - 1)
        chosen = options[idx]
        opt_text = chosen if isinstance(chosen, str) else chosen.get("text", str(chosen))
        
        gs, scene_id, options = play_option(gs, opt_text, idx, scene_id)
        
        if gs is None:
            print("Game encountered an error!", flush=True)
            break
    
    print(f"\n=== Game Complete ===", flush=True)
    print(f"Played 5-6 rounds of EVA themed text adventure", flush=True)
    print(f"Game ID: {game_id}", flush=True)

if __name__ == "__main__":
    main()
