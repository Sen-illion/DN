python - <<'PY'
from pathlib import Path
files = [
'/root/autodl-tmp/baselines/ComfyUI/models/unet/flux1-dev.safetensors',
'/root/autodl-tmp/baselines/ComfyUI/models/vae/ae.safetensors',
'/root/autodl-tmp/baselines/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors',
'/root/autodl-tmp/baselines/ComfyUI/models/clip/t5xxl_fp16.safetensors',
'/root/autodl-tmp/baselines/ComfyUI/models/clip/clip_l.safetensors',
'/root/autodl-tmp/baselines/ComfyUI/models/loras/movie-shots.safetensors',
]
for name in files:
    p = Path(name)
    if p.exists():
        st = p.stat()
        print('FOUND', name, st.st_size)
    else:
        print('MISSING', name)
PY
