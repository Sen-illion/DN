# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
try:
    from selenium import webdriver
    print("Selenium found:", webdriver.__file__)
except ImportError as e:
    print("Selenium not found:", e)
