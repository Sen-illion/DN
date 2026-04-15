# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json
import urllib.request

# Try CDP - get Chrome tabs via DevTools
CDP_URL = "http://127.0.0.1:28800/json"
try:
    with urllib.request.urlopen(CDP_URL, timeout=5) as resp:
        data = json.loads(resp.read())
    print("CDP Tabs:")
    for tab in data:
        print(f"  - {tab.get('title', 'No title')}: {tab.get('url', 'N/A')}")
except Exception as e:
    print(f"CDP error: {e}")
