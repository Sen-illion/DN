# -*- coding: utf-8 -*-
import os

path = r"C:\Users\User\Desktop\DN-main\dataset"
try:
    os.makedirs(path, exist_ok=True)
    print(f"Created: {path}")
except Exception as e:
    print(f"Error: {e}")
    print(f"Parent dir writable: {os.access(os.path.dirname(path), os.W_OK)}")
