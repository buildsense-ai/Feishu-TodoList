#!/bin/bash

# 🚀 飞书ToDoList API 一键启动脚本
# 使用方法: chmod +x start_server.sh && ./start_server.sh

echo "🚀 飞书ToDoList API 服务启动脚本"
echo "================================================"

# 检查Python环境
echo "🔍 检查Python环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi
echo "✅ Python3 已安装: $(python3 --version)"

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖包
echo "📥 安装依赖包..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
else
    echo "📋 requirements.txt 不存在，安装基础依赖..."
    pip install fastapi uvicorn requests pymysql python-multipart -q
fi
echo "✅ 依赖包安装完成"

# 检查必要文件
echo "📋 检查必要文件..."
required_files=("feishu_api_server.py" "database_manager.py" "meeting_database_manager.py")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ 缺少必要文件: $file"
        exit 1
    fi
done
echo "✅ 必要文件检查通过"

# 检查端口占用
echo "🔍 检查端口8000占用情况..."
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️ 端口8000已被占用，尝试终止现有进程..."
    pkill -f feishu_api_server.py
    sleep 2
fi

# 获取服务器IP地址
echo "🌐 获取服务器IP地址..."
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "localhost")

# 启动服务
echo "🚀 启动ToDoList API服务..."
echo "================================================"
echo "📊 服务地址: http://$SERVER_IP:8000"
echo "📖 API文档: http://$SERVER_IP:8000/docs"
echo "🔧 健康检查: http://$SERVER_IP:8000/health"
echo "💾 数据库状态: http://$SERVER_IP:8000/db/health"
echo "================================================"

# 后台启动服务
nohup python feishu_api_server.py > app.log 2>&1 &
SERVICE_PID=$!

echo "✅ 服务已启动！"
echo "🆔 进程ID: $SERVICE_PID"
echo "📋 查看日志: tail -f app.log"
echo "⏹️ 停止服务: kill $SERVICE_PID"

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 测试服务是否正常
echo "🧪 测试服务状态..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 服务启动成功！API正常响应"
    
    # 显示数据库连接状态
    echo "🔍 检查数据库连接..."
    curl -s http://localhost:8000/db/health | grep -q "healthy" && echo "✅ ToDoList数据库连接正常" || echo "⚠️ ToDoList数据库连接异常"
    curl -s http://localhost:8000/meetings/health | grep -q "healthy" && echo "✅ 会议记录数据库连接正常" || echo "⚠️ 会议记录数据库连接异常"
    
else
    echo "❌ 服务启动失败，请检查日志："
    echo "📋 tail -f app.log"
    exit 1
fi

echo "================================================"
echo "🎉 ToDoList API服务启动完成！"
echo "🔗 现在可以通过以下地址访问："
echo "   主页: http://$SERVER_IP:8000"
echo "   API文档: http://$SERVER_IP:8000/docs"
echo "   获取ToDoList: http://$SERVER_IP:8000/db/latest-todolist"
echo "================================================" 