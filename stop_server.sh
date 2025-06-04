#!/bin/bash

# 🛑 飞书ToDoList API 停止服务脚本
# 使用方法: chmod +x stop_server.sh && ./stop_server.sh

echo "🛑 停止飞书ToDoList API服务"
echo "================================================"

# 查找并终止所有相关进程
echo "🔍 查找服务进程..."
PIDS=$(pgrep -f "feishu_api_server.py")

if [ -z "$PIDS" ]; then
    echo "ℹ️ 没有找到运行中的ToDoList API服务"
else
    echo "📋 找到以下进程:"
    ps aux | grep feishu_api_server.py | grep -v grep
    
    echo "⏹️ 正在停止服务进程..."
    for PID in $PIDS; do
        echo "🔄 终止进程 $PID"
        kill $PID 2>/dev/null
        sleep 1
        
        # 如果进程仍在运行，强制终止
        if kill -0 $PID 2>/dev/null; then
            echo "💥 强制终止进程 $PID"
            kill -9 $PID 2>/dev/null
        fi
    done
    
    # 等待进程完全终止
    sleep 2
    
    # 再次检查
    REMAINING_PIDS=$(pgrep -f "feishu_api_server.py")
    if [ -z "$REMAINING_PIDS" ]; then
        echo "✅ 所有ToDoList API服务进程已停止"
    else
        echo "⚠️ 仍有进程在运行，请手动检查"
        ps aux | grep feishu_api_server.py | grep -v grep
    fi
fi

# 检查端口占用
echo "🔍 检查端口8000状态..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️ 端口8000仍被占用，可能有其他进程在使用"
    echo "📋 端口占用详情:"
    lsof -Pi :8000 -sTCP:LISTEN
else
    echo "✅ 端口8000已释放"
fi

# 清理日志文件选项
if [ -f "app.log" ]; then
    read -p "🗑️ 是否清理日志文件 app.log? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        > app.log
        echo "✅ 日志文件已清理"
    else
        echo "ℹ️ 保留日志文件，可通过 tail -f app.log 查看"
    fi
fi

echo "================================================"
echo "🏁 ToDoList API服务停止完成！"
echo "🔄 如需重新启动，请运行: ./start_server.sh"
echo "================================================" 