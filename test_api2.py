# -*- coding: utf-8 -*-
import requests
import json
import sys
import os

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

print("Sending request...", flush=True)
resp = requests.post("http://127.0.0.1:5001/generate-worldview", json=data, timeout=300)
print(f"Status: {resp.status_code}", flush=True)
result = resp.json()
print(f"Response status: {result.get('status', 'N/A')}", flush=True)
print(f"Response keys: {list(result.keys())}", flush=True)

# Print full response structure
for k, v in result.items():
    if isinstance(v, dict):
        print(f"  {k}: dict with keys {list(v.keys())[:10]}", flush=True)
    elif isinstance(v, str) and len(v) > 200:
        print(f"  {k}: {v[:200]}...", flush=True)
    else:
        print(f"  {k}: {v}", flush=True)

# Save to temp
save_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "game_state.json")
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2, default=str)
print(f"Saved to: {save_path}", flush=True)
