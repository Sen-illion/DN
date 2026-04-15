# -*- coding: utf-8 -*-
import sys
try:
    from selenium import webdriver
    print("selenium OK")
except ImportError as e:
    print(f"selenium missing: {e}")
    print("Will install...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "selenium"], capture_output=True)
