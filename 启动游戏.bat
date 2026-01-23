@echo off
chcp 65001 >nul
echo ====================================
echo     AI文本冒险游戏 - 启动脚本
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查Python环境...
python --version

echo.
echo [2/3] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖包安装失败，请检查网络连接
        pause
        exit /b 1
    )
) else (
    echo [提示] 依赖包已安装
)

echo.
echo [3/3] 启动游戏服务器...
echo.
echo ====================================
echo   游戏将在浏览器中自动打开
echo   访问地址: http://127.0.0.1:5001
echo ====================================
echo.
echo 按 Ctrl+C 可停止服务器
echo.

REM 启动服务器
python game_server.py

pause
