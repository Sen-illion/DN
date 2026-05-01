set +e
env | grep -E '^(HF_TOKEN|HUGGINGFACE_HUB_TOKEN)=' || true
