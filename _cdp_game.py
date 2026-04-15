# -*- coding: utf-8 -*-
"""
CDP 游戏自动化 - 直接连接游戏标签，随机选选项
"""
import sys
import json
import time
import asyncio
import random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import websockets
import urllib.request

CDP_HOST = "127.0.0.1"
CDP_PORT = 28800
TARGET_ID = "FB6498ED4CDB0BB145C17424D5E00673"

async def cdp_send(ws, method, params=None, id_gen=None):
    if id_gen is None:
        id_gen = [1]
    msg_id = id_gen[0]
    id_gen[0] += 1
    await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=15)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data

async def click_by_id(ws, btn_id):
    js = f"""
(function() {{
    var el = document.getElementById('{btn_id}');
    if (el && el.offsetParent !== null) {{
        el.click();
        return 'clicked: ' + el.textContent.trim();
    }}
    return 'not_found: {btn_id}';
}})()
"""
    r = await cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value", "")

async def click_by_text(ws, text):
    js = f"""
(function() {{
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {{
        if (btns[i].textContent.trim() === '{text}' && btns[i].offsetParent !== null) {{
            btns[i].click();
            return 'clicked: ' + btns[i].textContent.trim();
        }}
    }}
    return 'not_found: {text}';
}})()
"""
    r = await cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value", "")

async def click_by_text_contains(ws, keyword):
    js = f"""
(function() {{
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {{
        if (btns[i].textContent.trim().includes('{keyword}') && btns[i].offsetParent !== null) {{
            btns[i].click();
            return 'clicked: ' + btns[i].textContent.trim();
        }}
    }}
    return 'not_found: {keyword}';
}})()
"""
    r = await cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value", "")

async def get_visible_buttons(ws):
    js = """
(function() {
    var all = document.querySelectorAll('button');
    var info = [];
    all.forEach(function(e) {
        if (e.offsetParent !== null) {
            var r = e.getBoundingClientRect();
            info.push({id: e.id, text: e.textContent.trim().substring(0,120), x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height)});
        }
    });
    return JSON.stringify(info);
})()
"""
    r = await cdp_send(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    val_str = r.get("result", {}).get("result", {}).get("value", "[]")
    try:
        return json.loads(val_str)
    except:
        return []

async def main():
    print("=" * 60)
    print("CDP 游戏自动化 - 随机选项")
    print("=" * 60)

    # Connect directly to the game tab
    ws_url = f"ws://{CDP_HOST}:{CDP_PORT}/devtools/page/{TARGET_ID}"
    print(f"直接连接游戏标签: {TARGET_ID}")

    async with websockets.connect(ws_url) as ws:
        print("WebSocket 已连接")

        # Check current page
        r = await cdp_send(ws, "Runtime.evaluate", {
            "expression": "JSON.stringify({title: document.title, url: location.href})",
            "returnByValue": True
        })
        info = json.loads(r.get("result", {}).get("result", {}).get("value", "{}"))
        print(f"当前页面: {info.get('title')} | {info.get('url')}")

        await asyncio.sleep(2)

        # Step 1: Check what's on screen
        buttons = await get_visible_buttons(ws)
        print(f"\n当前 {len(buttons)} 个按钮:")
        for b in buttons:
            print(f"  [{b['id'] or '-':30s}] {b['w']:4d}x{b['h']:4d} | {b['text'][:60]}")

        # Step 2: Click start button if visible
        if any(b['id'] == 'start-btn' for b in buttons):
            print("\n=== 点击「开始新游戏」===")
            res = await click_by_id(ws, "start-btn")
            print(f"  结果: {res}")
            await asyncio.sleep(5)

        # Step 3: Try to configure / confirm game start
        print("\n=== 尝试开始游戏 ===")
        # Try any button that looks like "开始" or "确认"
        for kw in ["开始游戏", "开始", "确认", "生成", "创建"]:
            res = await click_by_text_contains(ws, kw)
            if res.startswith("clicked:"):
                print(f"  点击了「{kw}」: {res}")
                await asyncio.sleep(5)
                break
            else:
                print(f"  [{kw}] {res}")

        # Step 4: Game loop
        print("\n=== 游戏循环 ===")
        for round_num in range(1, 8):
            print(f"\n--- Round {round_num} ---")
            await asyncio.sleep(4)

            buttons = await get_visible_buttons(ws)
            print(f"  {len(buttons)} 个按钮:")
            for b in buttons:
                print(f"    [{b['id'] or '-':30s}] {b['w']:4d}x{b['h']:4d} | {b['text'][:60]}")

            # Filter out system/menu buttons
            system_ids = {"start-btn", "load-btn", "save-manage-btn", "exit-btn", "confirm-btn",
                          "back-btn", "auto-btn", "fancy-btn", "perf-btn"}
            # Filter: look for wide buttons that are game content
            game_buttons = [b for b in buttons
                           if b["id"] not in system_ids
                           and b["w"] >= 120
                           and b["text"].strip()
                           and len(b["text"].strip()) > 3
                           and b["text"].strip() not in {"自动（推荐）", "华丽", "性能"}]

            if not game_buttons:
                print("  没有找到游戏选项，尝试点击第一个宽按钮...")
                wide = [b for b in buttons if b["w"] >= 120 and len(b["text"].strip()) > 0]
                if wide:
                    game_buttons = [wide[0]]
                else:
                    print("  无法继续，未找到可点击按钮")
                    break

            # Random pick
            chosen = random.choice(game_buttons)
            print(f"  随机选择: [{chosen['id'] or '-':30s}] {chosen['text'][:60]}")

            # Click chosen button
            click_js = f"""
(function() {{
    var el = document.getElementById('{chosen["id"]}');
    if (el && el.offsetParent !== null) {{
        el.click();
        return 'ok';
    }}
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++) {{
        var t = btns[i].textContent.trim();
        if (t === '{chosen["text"].strip().replace("'", "\\'")}' && btns[i].offsetParent !== null) {{
            btns[i].click();
            return 'ok_by_text';
        }}
    }}
    return 'failed';
}})()
"""
            r = await cdp_send(ws, "Runtime.evaluate", {"expression": click_js, "returnByValue": True})
            result = r.get("result", {}).get("result", {}).get("value", "")
            print(f"  点击结果: {result}")

            await asyncio.sleep(3)

            # Check for ending
            r = await cdp_send(ws, "Runtime.evaluate", {
                "expression": """
(function() {
    var body = document.body.innerText;
    var kw = ['结局', 'THE END', 'Game Over', '通关', 'THE END'];
    for (var i = 0; i < kw.length; i++) { if (body.includes(kw[i])) return kw[i]; }
    return null;
})()
""",
                "returnByValue": True
            })
            ending = r.get("result", {}).get("result", {}).get("value")
            if ending:
                print(f"\n  🎉 检测到: {ending}")
                await asyncio.sleep(3)
                break

    print("\n" + "=" * 60)
    print("✅ 游戏完成！")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
