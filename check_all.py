# -*- coding: utf-8 -*-
import os

paths = [
    r"C:\Users\User\.qclaw\workspace",
    r"C:\Users\User\.qclaw",
    r"C:\Users\User\Desktop",
]

for p in paths:
    print(f"\n{p}:")
    print(f"  exists: {os.path.exists(p)}")
    print(f"  isdir: {os.path.isdir(p)}")
    if os.path.exists(p):
        print(f"  writable: {os.access(p, os.W_OK)}")
        try:
            items = os.listdir(p)
            print(f"  items ({len(items)}): {items[:5]}")
        except Exception as e:
            print(f"  list error: {e}")
