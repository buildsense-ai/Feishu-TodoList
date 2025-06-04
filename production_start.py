#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
生产环境启动脚本
飞书AI项目管理系统 - 正式版
"""

import subprocess
import sys
import time
import requests
from datetime import datetime

def check_dependencies():
    """检查依赖项"""
    print("🔍 检查依赖项...")
    try:
        import fastapi
        import uvicorn
        import mysql.connector
        import requests
        print("✅ 所有依赖项已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖项: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_system_health():
    """检查系统健康状态"""
    print("🏥 检查系统健康状态...")
    try:
        # 等待服务器启动
        time.sleep(3)
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 系统状态: {health_data['status']}")
            print(f"📊 版本: {health_data['version']}")
            print(f"🤖 AI可用: {'是' if health_data['ai_available'] else '否'}")
            return True
        else:
            print(f"❌ 系统健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def main():
    """主启动函数"""
    print("🚀 飞书AI项目管理系统 - 生产环境启动")
    print("=" * 60)
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查依赖项
    if not check_dependencies():
        sys.exit(1)
    
    print("\n🔧 系统配置:")
    print("- 主服务器: feishu_api_server.py")
    print("- 端口: 8000")
    print("- API文档: http://localhost:8000/docs")
    print("- 健康检查: http://localhost:8000/health")
    
    print("\n💡 核心功能:")
    print("- 📋 每日ToDoList生成 (POST /daily-todolist)")
    print("- 🔍 飞书消息智能分析")
    print("- 👥 团队任务自动分配")
    print("- 💾 MySQL数据库存储")
    print("- 📊 工作负载统计分析")
    
    print("\n🚀 启动服务器...")
    
    try:
        # 启动主服务器
        process = subprocess.Popen([
            sys.executable, "feishu_api_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 检查系统健康状态
        if check_system_health():
            print("\n✅ 系统启动成功！")
            print("\n🎯 使用方法:")
            print("1. 浏览器访问: http://localhost:8000/docs")
            print("2. 生成ToDoList: POST /daily-todolist")
            print("3. 查看任务: GET /db/latest-todolist")
            
            print("\n📋 工作流程:")
            print("- 会议后: 整理会议记录 → 发送飞书群")
            print("- 每天上午10:30: 自动生成ToDoList")
            
            print(f"\n🔥 系统已上线，运行中...")
            print("按 Ctrl+C 停止服务")
            
            # 保持运行
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n⏹️ 收到停止信号，正在关闭服务...")
                process.terminate()
                process.wait()
                print("✅ 服务已停止")
        else:
            print("❌ 系统启动失败")
            process.terminate()
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 