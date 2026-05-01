set +e
PID=$(cat /root/autodl-tmp/baselines/logs/comfyui_install_bg.pid 2>/dev/null)
ps -fp "$PID" || true
