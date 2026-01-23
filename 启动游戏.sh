#!/bin/bash

echo "===================================="
echo "   AI文本冒险游戏 - 启动脚本"
echo "===================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到Python3，请先安装Python 3.8+"
    exit 1
fi

echo "[1/3] 检查Python环境..."
python3 --version

echo ""
echo "[2/3] 检查依赖包..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "[提示] 正在安装依赖包..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖包安装失败，请检查网络连接"
        exit 1
    fi
else
    echo "[提示] 依赖包已安装"
fi

echo ""
echo "[3/3] 启动游戏服务器..."
echo ""
echo "===================================="
echo "  游戏访问地址: http://127.0.0.1:5001"
echo "===================================="
echo ""
echo "按 Ctrl+C 可停止服务器"
echo ""

# 启动服务器
python3 game_server.py
