# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
try:
    r = requests.head("https://sen-illion.com", timeout=5, allow_redirects=True)
    print(f"Status: {r.status_code}")
    print(f"URL: {r.url}")
    print(f"Headers: {dict(r.headers)}")
except Exception as e:
    print(f"Error: {e}")
