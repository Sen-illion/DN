# -*- coding: utf-8 -*-
"""启动服务器脚本 - 禁用debug模式"""
import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ['FLASK_ENV'] = 'production'

from game_server import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
