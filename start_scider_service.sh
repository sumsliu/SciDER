#!/bin/bash
# SciDER 服务启动脚本
# 用法: bash start_scider_service.sh

set -e

SCIDER_DIR="/Users/liuzf/opencode/SciDER"
PORT=8003

echo "========================================="
echo "启动 SciDER 服务"
echo "========================================="

# 进入 SciDER 目录
cd "$SCIDER_DIR"

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 检查端口是否被占用
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "警告: 端口 $PORT 已被占用"
    echo "正在尝试停止旧进程..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 启动服务
echo "启动 SciDER 服务在端口 $PORT..."
uvicorn api_server:app --host 127.0.0.1 --port $PORT --reload

# 注意: 使用 Ctrl+C 停止服务
