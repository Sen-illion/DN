# -*- coding: utf-8 -*-
import sys
import os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Check site-packages
sp = r"C:\Users\User\Desktop\DN-main\.venv\Lib\site-packages"
print("Site-packages contents:")
for item in sorted(os.listdir(sp)):
    print(f"  {item}")
