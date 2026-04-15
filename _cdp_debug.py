# -*- coding: utf-8 -*-
"""Debug: inspect modal and screen state"""
import sys
import json
import time
import asyncio
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

async def main():
    ws_url = f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{TARGET_ID}"
    async with websockets.connect(ws_url, open_timeout=10) as ws:
        print("Connected")

        # Drain
        try:
            while True: await asyncio.wait_for(ws.recv(), timeout=0.5)
        except asyncio.TimeoutError: pass

        # Get full page state
        state_js = """
(function(){
  var screens = ['menu-screen','attr-selection-screen','difficulty-selection-screen',
                 'theme-selection-screen','game-screen','save-screen'];
  var visible = [];
  screens.forEach(function(id){
    var el = document.getElementById(id);
    if(el){
      var cl = el.className || '';
      visible.push({id: id, hidden: cl.includes('hidden'), display: window.getComputedStyle(el).display});
    }
  });

  // Modal
  var modal = document.getElementById('difficulty-modal') || document.querySelector('.modal');
  var modalInfo = {found: !!modal};
  if(modal){
    modalInfo.className = modal.className.substring(0,100);
    modalInfo.display = window.getComputedStyle(modal).display;
    modalInfo.visibility = window.getComputedStyle(modal).visibility;
    modalInfo.zIndex = window.getComputedStyle(modal).zIndex;
  }

  // Overlay
  var overlay = document.querySelector('.modal-overlay, .overlay, [class*=overlay]');

  // Difficulty state
  var diffBtns = document.querySelectorAll('[data-difficulty], .difficulty-card');
  var diffInfo = [];
  diffBtns.forEach(function(d){
    diffInfo.push({tag: d.tagName, cls: d.className.substring(0,80), data: d.dataset, sel: d.className.includes('selected')||d.className.includes('active')});
  });

  // All buttons
  var allBtns = [];
  document.querySelectorAll('button').forEach(function(b){
    if(b.offsetParent !== null){
      allBtns.push({id: b.id, cls: b.className.substring(0,60), txt: b.textContent.trim().substring(0,50), disabled: b.disabled});
    }
  });

  return JSON.stringify({
    screens: visible,
    modal: modalInfo,
    difficultyCards: diffInfo,
    buttons: allBtns
  }, null, 2);
})()
"""
        result = await eval_js(ws, state_js)
        try:
            data = json.loads(result)
            print("=== SCREENS ===")
            for s in data.get("screens", []):
                print(f"  {s['id']}: hidden={s['hidden']}, display={s['display']}")

            print("\n=== MODAL ===")
            print(json.dumps(data.get("modal", {}), indent=2))

            print("\n=== DIFFICULTY CARDS ===")
            for d in data.get("difficultyCards", []):
                print(f"  [{d['tag']}] cls={d['cls']}, data={d['data']}, selected={d['sel']}")

            print(f"\n=== ALL VISIBLE BUTTONS ({len(data.get('buttons', []))}) ===")
            for b in data.get("buttons", []):
                print(f"  [{b['id'] or '-':30}] cls={b['cls'][:40]} | '{b['txt']}' | disabled={b['disabled']}")

        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Raw: {result[:500]}")

asyncio.run(main())
