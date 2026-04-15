# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
try:
    import websockets
    print("websockets:", websockets.__version__)
except ImportError as e:
    print("No websockets:", e)
