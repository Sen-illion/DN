# -*- coding: utf-8 -*-
import os
import stat

path = r"C:\Users\User\Desktop\DN-main"
print(f"Checking: {path}")
print(f"Exists: {os.path.exists(path)}")
print(f"Is dir: {os.path.isdir(path)}")

# List contents
try:
    items = os.listdir(path)
    print(f"Items ({len(items)}):")
    for name in sorted(items):
        if "dataset" in name.lower():
            full = os.path.join(path, name)
            st = os.stat(full)
            mode = st.st_mode
            print(f"  {name}: {'DIR' if stat.S_ISDIR(mode) else 'FILE'}, size={st.st_size}")
except Exception as e:
    print(f"Error listing: {e}")

# Check if dataset is a file
dataset_path = os.path.join(path, "dataset")
print(f"\n'dataset' path: {dataset_path}")
print(f"Exists: {os.path.exists(dataset_path)}")
if os.path.exists(dataset_path):
    print(f"Is file: {os.path.isfile(dataset_path)}")
    print(f"Is dir: {os.path.isdir(dataset_path)}")
    st = os.stat(dataset_path)
    print(f"Mode: {oct(st.st_mode)}")
    print(f"Size: {st.st_size}")
