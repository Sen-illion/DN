# -*- coding: utf-8 -*-
import requests
try:
    r = requests.get("http://127.0.0.1:5001/list-saves", timeout=10)
    print(f"Server alive: {r.status_code}")
    print(r.text[:200])
except Exception as e:
    print(f"Server error: {e}")
