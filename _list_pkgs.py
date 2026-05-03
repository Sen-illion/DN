# -*- coding: utf-8 -*-
import sys
import os
from project_paths import path_in_project
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Check site-packages
sp = path_in_project(".venv", "Lib", "site-packages")
print("Site-packages contents:")
for item in sorted(os.listdir(sp)):
    print(f"  {item}")
