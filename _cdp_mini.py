# -*- coding: utf-8 -*-
"""Minimal CDP game controller - single-shot per action"""
import sys
import json
import time
import asyncio
import random
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import websockets

TARGET_ID = "FB6498ED4CDB0BB145C17424D5E00673"
CDP_PORT = 28800

async def cdp(ws, method, params=None):
    """Fire-and-forget CDP send with immediate recv"""
    id_ = int(time.time() * 1000) & 0xFFFF
    msg = json.dumps({"id": id_, "method": method, "params": params or {}})
    await ws.send(msg)
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=8)
        return json.loads(raw)
    except asyncio.TimeoutError:
        return {"id": id_, "error": "timeout"}

def btn_text(ws):
    """Get visible button info as text"""
    js = """
(function(){
  var bs=document.querySelectorAll('button');
  var r=[];
  bs.forEach(function(b){
    if(b.offsetParent!==null){
      r.push({id:b.id,t:b.textContent.trim().substring(0,80),w:Math.round(b.getBoundingClientRect().width)});
    }
  });
  return JSON.stringify(r);
})()
"""
    r = asyncio.get_event_loop().run_until_complete(cdp(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True}))
    val = r.get("result",{}).get("result",{}).get("value","[]")
    try:
        return json.loads(val)
    except:
        return []

async def do_click(ws, js_code):
    r = await cdp(ws, "Runtime.evaluate", {"expression": js_code, "returnByValue": True})
    return r.get("result",{}).get("result",{}).get("value","")

async def main():
    ws_url = f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{TARGET_ID}"
    print("=" * 50)
    print("CDP Game Controller")
    print("=" * 50)
    print(f"Connecting to: {TARGET_ID}")

    async with websockets.connect(ws_url, open_timeout=10) as ws:
        print("Connected!")

        # Check page
        r = await cdp(ws, "Runtime.evaluate", {"expression": "JSON.stringify({t:document.title,u:location.href})", "returnByValue": True})
        info = json.loads(r.get("result",{}).get("result",{}).get("value","{}"))
        print(f"Page: {info.get('t')} | {info.get('u')}")

        # Flush events
        try:
            while True:
                r = await asyncio.wait_for(ws.recv(), timeout=1)
        except asyncio.TimeoutError:
            print("(event buffer flushed)")

        # Get buttons
        r = await cdp(ws, "Runtime.evaluate", {"expression": "(function(){var b=document.querySelectorAll('button');var a=[];b.forEach(function(x){if(x.offsetParent!==null)a.push({i:x.id,t:x.textContent.trim().substring(0,80),w:Math.round(x.getBoundingClientRect().width)});});return JSON.stringify(a);})()", "returnByValue": True})
        val = r.get("result",{}).get("result",{}).get("value","[]")
        try:
            buttons = json.loads(val)
        except:
            buttons = []
        print(f"\nButtons ({len(buttons)}):")
        for b in buttons:
            print(f"  [{b['i'] or '-':30}] w={b['w']} | {b['t'][:60]}")

        # Click start-btn if visible
        if any(b['i'] == 'start-btn' for b in buttons):
            print("\nClicking start-btn...")
            res = await do_click(ws, "document.getElementById('start-btn').click();'clicked'")
            print(f"Result: {res}")
            await asyncio.sleep(4)

            # Flush
            try:
                while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError: pass

            # Get buttons again
            r = await cdp(ws, "Runtime.evaluate", {"expression": "(function(){var b=document.querySelectorAll('button');var a=[];b.forEach(function(x){if(x.offsetParent!==null)a.push({i:x.id,t:x.textContent.trim().substring(0,80),w:Math.round(x.getBoundingClientRect().width)});});return JSON.stringify(a);})()", "returnByValue": True})
            val = r.get("result",{}).get("result",{}).get("value","[]")
            try: buttons = json.loads(val)
            except: buttons = []
            print(f"\nAfter start ({len(buttons)}):")
            for b in buttons:
                print(f"  [{b['i'] or '-':30}] w={b['w']} | {b['t'][:60]}")

            # Try to confirm / start game
            for kw in ["开始游戏", "确认", "生成", "开始"]:
                res = await do_click(ws, f"(function(){{var b=document.querySelectorAll('button');for(var i=0;i<b.length;i++){{if(b[i].textContent.trim().includes('{kw}')&&b[i].offsetParent!==null){{b[i].click();return 'clicked:'+b[i].textContent.trim();}}}}return 'not found';}})()")
                if res.startswith("clicked:"):
                    print(f"Clicked [{kw}]: {res}")
                    break
                print(f"  [{kw}]: {res}")

            await asyncio.sleep(5)

            # Flush
            try:
                while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError: pass

        # Game loop
        print("\n=== GAME LOOP ===")
        for rnd in range(1, 8):
            print(f"\n-- Round {rnd} --")
            await asyncio.sleep(4)

            # Flush
            try:
                while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError: pass

            r = await cdp(ws, "Runtime.evaluate", {"expression": "(function(){var b=document.querySelectorAll('button');var a=[];b.forEach(function(x){if(x.offsetParent!==null)a.push({i:x.id,t:x.textContent.trim().substring(0,100),w:Math.round(x.getBoundingClientRect().width)});});return JSON.stringify(a);})()", "returnByValue": True})
            val = r.get("result",{}).get("result",{}).get("value","[]")
            try: buttons = json.loads(val)
            except: buttons = []
            print(f"  Buttons: {len(buttons)}")
            for b in buttons:
                print(f"    [{b['i'] or '-':30}] w={b['w']} | {b['t'][:60]}")

            skip_ids = {"start-btn","load-btn","save-manage-btn","exit-btn","confirm-btn","back-btn","","auto-btn"}
            game_btns = [b for b in buttons if b['i'] not in skip_ids and b['w']>=120 and len(b['t'])>3 and b['t'] not in {"自动（推荐）","华丽","性能"}]

            if not game_btns:
                print("  No game buttons found, trying wide ones...")
                game_btns = [b for b in buttons if b['w']>=100 and len(b['t'])>0]

            if not game_btns:
                print("  STOP: no clickable buttons")
                break

            chosen = random.choice(game_btns)
            print(f"  Choice: [{chosen['i'] or '-':30}] {chosen['t'][:60]}")
            # Build click JS without f-string complexity
            chosen_id = chosen['i']
            chosen_txt = chosen['t']
            click_js = (
                "(function(){"
                "var el=document.getElementById('%s');"
                "if(el&&el.offsetParent!==null){el.click();return 'ok_id';}"
                "var bs=document.querySelectorAll('button');"
                "for(var i=0;i<bs.length;i++){"
                "var t=bs[i].textContent.trim();"
                "if(t==='%s'&&bs[i].offsetParent!==null){bs[i].click();return 'ok_text';}"
                "}"
                "return 'fail';"
                "})()"
            ) % (chosen_id, chosen_txt.replace("'", "\\'"))
            res = await do_click(ws, click_js)
            print(f"  Click result: {res}")

            await asyncio.sleep(3)

            # Check ending
            r = await cdp(ws, "Runtime.evaluate", {"expression": "(function(){var k=['结局','THE END','Game Over','通关'];var t=document.body.innerText;for(var i=0;i<k.length;i++)if(t.indexOf(k[i])>=0)return k[i];return null;})()", "returnByValue": True})
            end = r.get("result",{}).get("result",{}).get("value")
            if end:
                print(f"\n  ENDING DETECTED: {end}")
                break

    print("\n" + "=" * 50)
    print("DONE!")
    print("=" * 50)

asyncio.run(main())
