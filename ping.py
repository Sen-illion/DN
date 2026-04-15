# -*- coding: utf-8 -*-
import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:5001/list-saves', timeout=5)
    print('OK:', r.read().decode()[:100])
except Exception as e:
    print('ERROR:', e)
