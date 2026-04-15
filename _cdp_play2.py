# -*- coding: utf-8 -*-
import sys
import json
import time
import asyncio
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import websockets
import urllib.request

CDP_HOST = "127.0.0.1"
CDP_PORT = 28800
GAME_URL = "http://127.0.0.1:5001"

async def main():
    print("=" * 50)
    print("CDP 游戏控制 (websockets)")
    print("=" * 50)

    # Get tabs
    url = f"http://{CDP_HOST}:{CDP_PORT}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        tabs = json.loads(resp.read())
    
    target = None
    for t in tabs:
        if t.get('url') == 'about:blank':
            target = t
            break
    
    if not target:
        print("No blank tab found")
        return
    
    ws_url = target['webSocketDebuggerUrl']
    print(f"Connecting to: {ws_url}")
    
    async with websockets.connect(ws_url) as ws:
        print("Connected!")
        
        # Navigate to game
        await ws.send(json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": GAME_URL}}))
        print("Navigating...")
        
        # Wait for navigation
        await asyncio.sleep(6)
        
        # Process events
        try:
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                data = json.loads(msg)
                print(f"  Event: {data.get('method', 'response')}")
        except asyncio.TimeoutError:
            print("  No more events")
        
        # Evaluate JS to get buttons
        await ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": """
(function() {
    var all = document.querySelectorAll('button, .option-btn, [class*=option]');
    var info = [];
    all.forEach(function(e) {
        if (e.offsetParent !== null) {
            info.push({tag: e.tagName, id: e.id, cls: e.className.substring(0,50), text: e.textContent.trim().substring(0,80)});
        }
    });
    return JSON.stringify(info);
})()
""",
                "returnByValue": True
            }
        }))
        
        resp = await asyncio.wait_for(ws.recv(), timeout=10)
        result = json.loads(resp)
        val = result.get('result', {}).get('result', {})
        val_str = val.get('value', 'null')
        buttons = json.loads(val_str)
        print(f"\n找到 {len(buttons)} 个可见元素:")
        for b in buttons:
            print(f"  [{b['tag']}] {b['id']} | {b['text']}")

if __name__ == "__main__":
    asyncio.run(main())
