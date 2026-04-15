# -*- coding: utf-8 -*-
import sys
try:
    from playwright.sync_api import sync_playwright
    print("playwright available")
except ImportError:
    print("playwright not available")

try:
    import selenium
    print("selenium available")
except ImportError:
    print("selenium not available")
