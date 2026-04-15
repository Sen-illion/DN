# -*- coding: utf-8 -*-
import urllib.request
import json

try:
    with urllib.request.urlopen("http://127.0.0.1:5001/list-saves", timeout=5) as r:
        print("HTTP OK:", r.status)
        body = r.read().decode("utf-8", errors="replace")
        print("Body:", body[:300])
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
