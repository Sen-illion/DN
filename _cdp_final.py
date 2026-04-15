# -*- coding: utf-8 -*-
"""CDP game controller - complete game flow"""
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
_id = 0

async def cdp(ws, method, params=None):
    global _id; _id += 1
    await ws.send(json.dumps({"id": _id, "method": method, "params": params or {}}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        d = json.loads(raw)
        if d.get("id") == _id:
            return d

async def eval_js(ws, code):
    r = await cdp(ws, "Runtime.evaluate", {"expression": code, "returnByValue": True})
    return r.get("result", {}).get("result", {}).get("value", "")

async def get_buttons(ws):
    js = """(function(){
  var r=[];
  document.querySelectorAll('button').forEach(function(b){
    if(b.offsetParent!==null){
      r.push({i:b.id||'',t:b.textContent.trim().substring(0,120),w:Math.round(b.getBoundingClientRect().width),dis:b.disabled});
    }
  });
  return JSON.stringify(r);
})()"""
    val = await eval_js(ws, js)
    try: return json.loads(val)
    except: return []

async def get_active_screen(ws):
    """Get the currently visible (non-hidden) screen ID"""
    js = """(function(){
  var screens=['menu-screen','attr-selection-screen','difficulty-selection-screen',
               'tone-selection-screen','theme-input-screen','image-style-selection-screen',
               'game-screen','save-screen'];
  var active=null;
  screens.forEach(function(id){
    var el=document.getElementById(id);
    if(el){
      var cls=el.className||'';
      var disp=window.getComputedStyle(el).display;
      if(!cls.includes('hidden')&&disp!=='none')active=id;
    }
  });
  return active;
})()"""
    return await eval_js(ws, js)

async def click_id(ws, btn_id):
    return await eval_js(ws,
        "var b=document.getElementById('%s');if(b&&b.offsetParent!==null){b.click();'ok';}else{'not_found';}" % btn_id)

async def click_text_kw(ws, kw):
    return await eval_js(ws,
        "(function(){var bs=document.querySelectorAll('button');"
        "for(var i=0;i<bs.length;i++){"
        "var t=bs[i].textContent.trim();"
        "if(t.includes('%s')&&bs[i].offsetParent!==null){bs[i].click();return t;}}}"
        "return 'not_found';})()" % kw)

async def click_data_card(ws, data_attr, data_value):
    """Click an element with data-<attr>='<value>'"""
    return await eval_js(ws,
        "(function(){"
        "var els=document.querySelectorAll('[data-%s]');"
        "for(var i=0;i<els.length;i++){"
        "if(els[i].getAttribute('data-%s')==='%s'&&els[i].offsetParent!==null){"
        "els[i].click();return 'clicked';}}"
        "return 'not_found';"
        "})()" % (data_attr, data_attr, data_value))

async def type_input(ws, input_id, text):
    """Type text into an input field"""
    js = """
(function(){
  var el=document.getElementById('%s');
  if(!el||el.offsetParent===null)return 'not_found';
  el.value='';
  el.dispatchEvent(new Event('input',{bubbles:true}));
  var nativeSetter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  nativeSetter.call(el,'%s');
  el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));
  return 'ok:'+el.value;
})()
""" % (input_id, text)
    return await eval_js(ws, js)

async def main():
    ws_url = f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{TARGET_ID}"
    print("=" * 55)
    print("CDP Game - Complete Walkthrough")
    print("=" * 55)

    async with websockets.connect(ws_url, open_timeout=10, close_timeout=5) as ws:
        print("Connected!")

        # Drain
        try:
            while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
        except asyncio.TimeoutError: pass

        choices = []

        # ======== SETUP PHASE ========
        print("\n=== Setup Phase ===")
        for step in range(30):
            await asyncio.sleep(2)
            screen = await get_active_screen(ws)
            buttons = await get_buttons(ws)
            print(f"\n  Step {step}: screen={screen}")
            for b in buttons:
                print(f"    [{b['i'] or '-':35}] w={b['w']} | '{b['t'][:50]}'")

            if screen == 'menu-screen':
                print("  -> main menu: clicking start-btn")
                await click_id(ws, 'start-btn')

            elif screen == 'difficulty-selection-screen':
                # Select a random difficulty card
                diffs = ['简单', '中等', '困难']
                chosen_diff = random.choice(diffs)
                print(f"  -> selecting difficulty: {chosen_diff}")
                await click_data_card(ws, 'difficulty', chosen_diff)
                await asyncio.sleep(1)
                print("  -> clicking confirm-difficulty-btn")
                await click_id(ws, 'confirm-difficulty-btn')

            elif screen == 'tone-selection-screen':
                # Select a random tone card
                tones = ['happy_ending', 'normal_ending', 'humorous', 'aesthetic']
                chosen_tone = random.choice(tones)
                tone_labels = {'happy_ending': '圆满结局', 'normal_ending': '普通结局',
                              'humorous': '幽默', 'aesthetic': '唯美'}
                print(f"  -> selecting tone: {chosen_tone} ({tone_labels.get(chosen_tone, '')})")
                await click_data_card(ws, 'tone', chosen_tone)
                await asyncio.sleep(1)
                print("  -> clicking confirm-tone-btn")
                await click_id(ws, 'confirm-tone-btn')

            elif screen == 'theme-input-screen':
                themes = ['便利店深夜', '校园天台', '古风江南', '都市霓虹', '深海航行']
                chosen_theme = random.choice(themes)
                print(f"  -> typing theme: {chosen_theme}")
                await type_input(ws, 'theme-input', chosen_theme)
                await asyncio.sleep(1)
                print("  -> clicking submit-theme-btn")
                await click_id(ws, 'submit-theme-btn')

            elif screen == 'image-style-selection-screen':
                styles = ['anime', '水彩', '油画', '水墨']
                chosen_style = random.choice(styles)
                print(f"  -> selecting image style: {chosen_style}")
                await click_text_kw(ws, chosen_style)
                await asyncio.sleep(1)
                # Find confirm button
                for kw in ["确认", "开始游戏"]:
                    r = await click_text_kw(ws, kw)
                    if r != 'not_found':
                        print(f"  -> clicked [{kw}]: {r}")
                        break

            elif screen == 'game-screen':
                print("\n=== GAME SCREEN REACHED ===")
                break

            else:
                print(f"  Unknown screen, trying generic confirm...")
                for kw in ["确认", "开始游戏", "下一步"]:
                    r = await click_text_kw(ws, kw)
                    if r != 'not_found':
                        print(f"  -> [{kw}]: {r}")
                        break

        # ======== GAME LOOP ========
        print("\n=== GAME LOOP ===")
        for rnd in range(1, 12):
            await asyncio.sleep(4)

            # Drain events
            try:
                while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError: pass

            screen = await get_active_screen(ws)
            buttons = await get_buttons(ws)
            print(f"\n-- Round {rnd} | screen={screen} --")
            for b in buttons:
                print(f"  [{b['i'] or '-':35}] w={b['w']} | '{b['t'][:60]}'")

            if screen != 'game-screen':
                print("  Not in game screen, trying to continue...")
                for kw in ["确认", "继续", "开始"]:
                    r = await click_text_kw(ws, kw)
                    if r != 'not_found':
                        print(f"  -> [{kw}]: {r}")
                        break
                continue

            # Filter game option buttons
            skip_ids = {"start-btn","load-btn","save-manage-btn","exit-btn",
                        "confirm-btn","back-btn","auto-btn","fancy-btn","perf-btn",
                        "modal-confirm","modal-cancel","confirm-difficulty-btn",
                        "confirm-attr-btn","confirm-theme-btn","confirm-tone-btn",
                        "confirm-image-style-btn","submit-theme-btn",""}
            skip_texts = {"自动（推荐）", "华丽", "性能", "确认", "取消", "下一步",
                         "重新分配", "提交主题", "开始游戏", ""}

            game_btns = [b for b in buttons
                        if b['i'] not in skip_ids
                        and b['t'] not in skip_texts
                        and b['w'] >= 100
                        and len(b['t']) > 3]

            if not game_btns:
                print("  No game buttons found. Stop.")
                break

            chosen = random.choice(game_btns)
            choices.append(chosen['t'][:80])
            print(f"  --> CHOICE: [{chosen['i'] or '-':35}] {chosen['t'][:60]}")

            if chosen['i']:
                r = await eval_js(ws,
                    "var b=document.getElementById('%s');if(b&&b.offsetParent!==null){b.click();'ok';}else{'not_found';}" % chosen['i'])
            else:
                esc = chosen['t'].replace("'", "\\'")
                r = await eval_js(ws,
                    "(function(){var bs=document.querySelectorAll('button');"
                    "for(var i=0;i<bs.length;i++){"
                    "if(bs[i].textContent.trim()==='%s'&&bs[i].offsetParent!==null)"
                    "{bs[i].click();return 'ok';}}return 'not_found';})()" % esc)
            print(f"  Click: {r}")

            await asyncio.sleep(3)

            # Check for ending
            end = await eval_js(ws,
                "(function(){var k=['结局','THE END','Game Over','通关'];"
                "var t=document.body.innerText;"
                "for(var i=0;i<k.length;i++)if(t.indexOf(k[i])>=0)return k[i];"
                "return null;})()")
            if end:
                print(f"\n*** ENDING DETECTED: {end} ***")
                await asyncio.sleep(3)
                break

        # Summary
        print("\n" + "=" * 55)
        print("GAME SUMMARY")
        print("=" * 55)
        print(f"Rounds played: {len(choices)}")
        for i, c in enumerate(choices):
            print(f"  Round {i+1}: {c}")
        print("=" * 55)
        print("DONE!")

asyncio.run(main())
