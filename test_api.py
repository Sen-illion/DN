# -*- coding: utf-8 -*-
import requests
import json
import sys

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

print("Sending request...")
resp = requests.post("http://127.0.0.1:5001/generate-worldview", json=data, timeout=300)
print(f"Status: {resp.status_code}")
result = resp.json()
print(f"Status field: {result.get('status', 'N/A')}")

if result.get("status") == "success":
    gs = result.get("global_state", {})
    worldview = gs.get("core_worldview", {})
    game_id = gs.get("game_id", "N/A")
    print(f"Game ID: {game_id}")
    print(f"Worldview title: {worldview.get('title', 'N/A')}")
    print(f"Worldview intro: {str(worldview.get('introduction', 'N/A'))[:200]}")
    
    # Save full result for later use
    with open("test_game_state.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print("Full state saved to test_game_state.json")
else:
    print(f"Error: {result.get('message', 'Unknown error')}")
    print(f"Full response: {json.dumps(result, ensure_ascii=False)[:500]}")
