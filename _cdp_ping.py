# -*- coding: utf-8 -*-
import sys
import json
import asyncio
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import websockets
import urllib.request

TARGET_ID = "FB6498ED4CDB0BB145C17424D5E00673"
CDP_PORT = 28800

async def main():
    print("Connecting to game tab via CDP...")
    ws_url = f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{TARGET_ID}"
    print(f"URL: {ws_url}")
    
    try:
        async with websockets.connect(ws_url, open_timeout=10) as ws:
            print("Connected!")
            
            # Send ping
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": "2+2", "returnByValue": True}}))
            print("Sent evaluate, waiting for response...")
            
            # With a short timeout
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                print(f"Response: {raw[:200]}")
            except asyncio.TimeoutError:
                print("TIMEOUT waiting for response!")
                
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
