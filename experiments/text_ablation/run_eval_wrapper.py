from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\User\Desktop\DN-main")
SITE = ROOT / ".venv2" / "Lib" / "site-packages"
EVAL_SCRIPT = ROOT / "DN-experiment-2.0" / "eval_plot_coherence.py"


def main() -> int:
    sys.path.append(str(SITE))
    sys.argv = [str(EVAL_SCRIPT), *sys.argv[1:]]
    runpy.run_path(str(EVAL_SCRIPT), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
