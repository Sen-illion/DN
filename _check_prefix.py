# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
print("sys.prefix:", sys.prefix)
print("sys.base_prefix:", sys.base_prefix)
import site
print("site-packages:", site.getsitepackages())
