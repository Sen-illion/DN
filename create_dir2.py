# -*- coding: utf-8 -*-
import os

# Try workspace
path = r"C:\Users\User\.qclaw\workspace\dataset"
try:
    os.makedirs(path, exist_ok=True)
    print(f"Created: {path}")
except Exception as e:
    print(f"Error: {e}")

# Try Documents
path2 = r"C:\Users\User\Documents\DN_dataset"
try:
    os.makedirs(path2, exist_ok=True)
    print(f"Created: {path2}")
except Exception as e:
    print(f"Error2: {e}")
