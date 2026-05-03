import os, sys
root = r"D:\Projects\DN"
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
os.environ["PREGENERATION_ENABLED"] = "true"
os.environ.setdefault("PYTHONUTF8", "1")
os.environ["DN_BENCHMARK_STRICT_FULLREADY"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE"] = "1"
os.environ["GENERATE_OPTION_SYNC_BACKFILL_IMAGE"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE_MAX_WAIT_SECONDS"] = "45"
os.environ["GENERATE_OPTION_SKIP_SYNC_BACKFILL_AFTER_BLOCK_TIMEOUT"] = "1"
os.environ["PREGEN_LAYER2_IMAGE_ENABLED"] = "false"
os.environ["PREGEN_IMAGE_CACHE_WRITE_MAX_WAIT_SECONDS"] = "45"
from game_server import app
app.run(host="127.0.0.1", port=5032, debug=False, threaded=True)
