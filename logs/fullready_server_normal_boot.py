import os, sys
root = r"D:\Projects\DN"
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
os.environ["PREGENERATION_ENABLED"] = "false"
os.environ.setdefault("PYTHONUTF8", "1")
from game_server import app
app.run(host="127.0.0.1", port=5003, debug=False, threaded=True)
