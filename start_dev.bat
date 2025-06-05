@echo off
echo 启动飞书消息AI分析系统 - 开发环境
echo ====================================

echo 1. 启动后端服务...
cd backend
start "Backend Server" cmd /k "python feishu_api_server.py"

echo 2. 等待后端启动...
timeout /t 3 /nobreak > nul

echo 3. 启动前端应用...
cd ..\frontend
start "Frontend Server" cmd /k "npm start"

echo 4. 系统启动完成！
echo.
echo 前端地址: http://localhost:3000
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
pause 