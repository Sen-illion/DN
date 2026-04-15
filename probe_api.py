# -*- coding: utf-8 -*-
import json, urllib.request

def api_post(endpoint, payload, timeout=300):
    url = f"http://127.0.0.1:5001/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}

print("测试 generate-worldview 响应结构...")
r = api_post("generate-worldview", {
    "gameTheme": "高三同桌",
    "imageStyle": "水彩风格",
    "protagonistAttr": {"name": "林小雨", "personality": "内向温柔"},
    "difficulty": "中等",
    "toneKey": "romantic_ending"
}, timeout=300)

# 打印顶层 keys
print("顶层 keys:", list(r.keys()) if isinstance(r, dict) else type(r))
if isinstance(r, dict):
    for k, v in r.items():
        if isinstance(v, (str, int, float, bool)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: dict with keys {list(v.keys())[:5]}")
        elif isinstance(v, list):
            print(f"  {k}: list len={len(v)}")
        else:
            print(f"  {k}: {type(v)}")
