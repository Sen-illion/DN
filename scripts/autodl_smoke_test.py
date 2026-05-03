"""Smoke test for DN cloud experiment environments."""

from __future__ import annotations

import importlib
import os
import sys


REQUIRED_MODULES = [
    "flask",
    "dotenv",
    "google.genai",
    "openai",
    "cv2",
    "PIL",
    "requests",
    "tenacity",
]


def check_imports() -> bool:
    ok = True
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"[OK] import {module_name}")
        except Exception as exc:  # noqa: BLE001 - report all dependency failures.
            ok = False
            print(f"[FAIL] import {module_name}: {exc}")
    return ok


def check_cuda() -> bool:
    try:
        import torch
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] torch unavailable: {exc}")
        return False

    print(f"[OK] torch {torch.__version__}")
    print(f"[INFO] cuda available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"[INFO] cuda version: {torch.version.cuda}")
        print(f"[INFO] gpu count: {torch.cuda.device_count()}")
        print(f"[INFO] gpu name: {torch.cuda.get_device_name(0)}")
        x = torch.ones((1024, 1024), device="cuda")
        y = x @ x
        torch.cuda.synchronize()
        print(f"[OK] cuda matmul checksum: {float(y[0, 0].detach().cpu())}")
        return True
    return False


def check_env_keys() -> None:
    expected = [
        "Image_Generation_API_KEY",
        "Image_Generation_BASE_URL",
        "Image_Generation_MODEL",
        "Camera_Analyst_API_KEY",
        "Camera_Analyst_BASE_URL",
        "Camera_Analyst_MODEL",
        "COMFYUI_HOST",
        "ENABLE_MOCK_MODE",
    ]
    missing = [key for key in expected if not os.getenv(key)]
    if missing:
        print("[WARN] missing env keys: " + ", ".join(missing))
    else:
        print("[OK] required env keys are present")


def main() -> int:
    print(f"[INFO] python: {sys.version.split()[0]}")
    imports_ok = check_imports()
    check_cuda()
    check_env_keys()
    return 0 if imports_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
