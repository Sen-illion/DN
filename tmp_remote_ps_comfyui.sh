set +e
ps -ef | grep -E 'comfyui_install_inner|pip|python' | grep -v grep | tail -n 30
ls -lh /root/autodl-tmp/baselines/logs/comfyui_install_bg.log
