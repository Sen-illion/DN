# -*- coding: utf-8 -*-
import json, time, urllib.request, urllib.error

def api_post(endpoint, payload, timeout=600):
    url = f"http://127.0.0.1:5001/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            print(f"API call took {elapsed:.1f}s")
            return result
    except Exception as e:
        elapsed = time.time() - t0
        print(f"API call FAILED after {elapsed:.1f}s: {e}")
        return {"error": str(e)}

print("Testing generate-worldview with 600s timeout...")
r = api_post("generate-worldview", {
    "gameTheme": "高三同桌",
    "imageStyle": "水彩风格",
    "protagonistAttr": {"name": "林小雨", "personality": "内向温柔"},
    "difficulty": "中等",
    "toneKey": "romantic_ending"
}, timeout=600)

if "error" in r:
    print(f"Error: {r['error']}")
else:
    gid = r.get("globalState", {}).get("game_id", "NONE")
    print(f"Success! game_id={gid}")
    print(f"Top keys: {list(r.keys())}")
