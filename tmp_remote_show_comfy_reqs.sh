cd /root/autodl-tmp/baselines/ComfyUI
python - <<'PY'
from pathlib import Path
p = Path('requirements.txt')
print(p.read_text()[:4000])
PY
