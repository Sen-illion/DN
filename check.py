# -*- coding: utf-8 -*-
import requests
r = requests.get("http://127.0.0.1:5001/list-saves", timeout=5)
print(r.status_code, r.text[:200])
