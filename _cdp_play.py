# -*- coding: utf-8 -*-
"""
CDP 控制游戏页面：导航 + 点击 + 轮询选项
"""
import sys
import json
import time
import socket
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    import websocket
    print("websocket-client available")
    HAS_WS = True
except ImportError:
    print("No websocket library, using urllib only")
    HAS_WS = False

GAME_URL = "http://127.0.0.1:5001"
CDP_HOST = "127.0.0.1"
CDP_PORT = 28800
WS_BASE = f"ws://{CDP_HOST}:{CDP_PORT}"

def get_tabs():
    import urllib.request
    url = f"http://{CDP_HOST}:{CDP_PORT}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read())

def ws_command(ws, method, params=None, id=1):
    msg = json.dumps({"id": id, "method": method, "params": params or {}})
    ws.send(msg)
    resp = json.loads(ws.recv())
    return resp

def main():
    print("=" * 50)
    print("CDP 游戏控制")
    print("=" * 50)

    tabs = get_tabs()
    print(f"找到 {len(tabs)} 个标签页")
    for t in tabs:
        print(f"  {t.get('id')} | {t.get('title')} | {t.get('url')}")

    # 找到 about:blank 标签
    target = None
    for t in tabs:
        if t.get('url') == 'about:blank':
            target = t
            break

    if not target:
        print("没有找到 about:blank 标签")
        return

    target_id = target['id']
    ws_url = target.get('webSocketDebuggerUrl')
    print(f"\n目标标签: {target_id}")
    print(f"WebSocket URL: {ws_url}")

    if not ws_url:
        print("没有 WebSocket URL，无法连接")
        return

    print("\n通过 CDP 导航到游戏...")
    import websocket
    ws = websocket.create_connection(ws_url, timeout=10)
    print("WebSocket 已连接")

    # 导航到游戏
    ws_command(ws, "Page.navigate", {"url": GAME_URL})
    print("已发送导航请求，等待加载...")
    time.sleep(5)

    for i in range(3):
        resp = ws.recv()
        data = json.loads(resp)
        print(f"  收到: {data.get('method', 'response')}")

    print("\n检查页面内容...")
    result = ws_command(ws, "Runtime.evaluate", {
        "expression": """
(function() {
    var btns = document.querySelectorAll('button');
    var info = [];
    btns.forEach(function(b) {
        if (b.offsetParent !== null) {
            info.push({id: b.id, text: b.textContent.trim(), w: b.offsetWidth, h: b.offsetHeight});
        }
    });
    return JSON.stringify({buttons: info, title: document.title, url: location.href});
})()
""",
        "returnByValue": True
    })
    print("页面状态:", json.dumps(result.get('result', {}).get('result', {}), ensure_ascii=False)[:500])
    ws.close()

if __name__ == "__main__":
    main()
