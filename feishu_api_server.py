from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, File, UploadFile
from pydantic import BaseModel
from typing import Optional
import uvicorn
from datetime import datetime, timedelta
from feishu_message_fetcher import FeishuMessageFetcher
from ai_message_processor import AIProjectAnalyzer
from database_manager import get_database_manager, DatabaseManager
from feishu_user_id_mapper import get_user_name_by_feishu_id, replace_user_ids_in_text, get_all_team_members, get_real_team_members, is_real_team_member, normalize_team_member_name
import json
import os
import httpx
import mysql.connector
from mysql.connector import Error
import requests

app = FastAPI(
    title="飞书消息AI分析系统",
    description="""
## 🚀 智能项目管理助手 v2.7.0 - 简化版

### 🎯 核心功能
- **飞书消息智能获取**: 自动拉取群组消息（昨天10:30到今天10:30）
- **用户ID映射**: 自动将sender_id映射为真实姓名
- **AI智能分析**: 基于OpenRouter Gemini 2.5生成ToDoList
- **按人员分组管理**: 自动识别5个团队成员，任务清晰分类
- **数据库持久化**: MySQL存储ToDoList分析结果

### 📋 ToDoList格式
**三大任务分类，按人员细分：**
- **ToDo (待办)**: 新提到的计划、下一步行动
- **Done (已完成)**: 明确提到完成的工作
- **Issues (问题)**: 技术难题、阻塞点

### 👥 团队成员
系统仅为以下5个真实团队成员分配任务：
- **Michael**: 前端UI
- **小钟**: 后端数据库  
- **国伟**: 爬虫数据
- **云起**: AI语音
- **Gauz**: 架构性能

### ⏰ 时间范围
每日ToDoList分析前一天10:30到今天10:30的所有消息，覆盖完整的工作周期。

### 💾 数据库功能
- **ToDoList数据库**: feishu_todolist - 存储任务分析结果
- **历史记录查询**: 可查询历史任何一天的ToDoList
- **工作负载分析**: 成员工作量统计和趋势分析

### 🛠️ 配置要求
- 飞书App ID/Secret  
- OpenRouter API Key (Gemini 2.5)
- MySQL数据库连接

### 📋 使用流程
1. 配置飞书应用、OpenRouter密钥和MySQL数据库
2. 调用 `/daily-todolist` API生成每日ToDoList
3. 使用 `/db/*` API查询历史数据和统计分析

技术栈: FastAPI + Gemini 2.5 + 飞书API + MySQL
    """,
    version="2.7.0",
    contact={
        "name": "飞书AI分析系统", 
        "email": "support@feishu-ai.com"
    }
)

# 配置信息
APP_ID = "cli_a778ea0d0278100e"
APP_SECRET = "9h4EoFmjeTPgR344VWKu8fDmnxW76Cru"
DEFAULT_CONTAINER_ID = "oc_58605a887f1e11e359ceec1782c2d12d"  # 默认群聊ID

# AI配置 - OpenRouter API
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "google/gemini-2.5-pro-preview"  # OpenRouter中的Gemini 2.5模型

# 向后兼容，也支持从环境变量获取
API_KEY = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY)

# 请求模型
class MessageRequest(BaseModel):
    container_id: str  # 群聊ID
    start_time: Optional[str] = None  # 开始时间戳（秒）
    end_time: Optional[str] = None    # 结束时间戳（秒）
    download_files: bool = True       # 是否下载文件
    download_path: str = "./downloads"  # 下载路径

class TimeRangeRequest(BaseModel):
    container_id: str
    days_ago: int = 0  # 几天前，0表示今天，1表示昨天
    download_files: bool = True
    download_path: str = "./downloads"

class AIProcessRequest(BaseModel):
    """AI处理请求"""
    container_id: str = DEFAULT_CONTAINER_ID
    start_time: str = None  # 开始时间，格式：YYYY-MM-DD HH:MM:SS
    end_time: str = None    # 结束时间
    download_files: bool = False  # 是否下载文件
    download_path: str = "downloads"  # 下载路径
    use_ai: bool = True     # 是否使用AI
    ai_api_key: str = None  # 自定义AI API密钥

# 存储任务状态
task_status = {}

@app.get("/")
async def root():
    """根路径，显示API信息"""
    return {
        "message": "飞书消息获取&AI分析API服务",
        "version": "2.7.0",
        "ai_provider": "OpenRouter Gemini 2.5",
        "features": [
            "📥 获取飞书群聊消息",
            "🤖 OpenRouter Gemini 2.5智能项目分析",
            "👥 按团队成员分组任务",
            "📊 TODO/DONE/ISSUES深度提取",
            "⏰ 每日ToDoList定时生成（前一天10:30到今天10:30）",
            "🔄 支持webhook事件接收"
        ],
        "endpoints": [
            "GET /health - 健康检查",
            "POST /fetch-messages - 获取消息（完整参数）",
            "POST /fetch-today - 获取今天的消息",
            "POST /fetch-yesterday - 获取昨天的消息",
            "POST /fetch-async - 异步获取消息",
            "POST /ai-analyze - AI项目分析（按人员分组任务）",
            "POST /ai-analyze-today - AI分析今天的项目讨论",
            "POST /daily-todolist - 生成每日ToDoList（昨天10:30到今天10:30）",
            "GET /task-status/{task_id} - 查询任务状态",
            "POST /webhook/event - 接收飞书事件回调（URL验证）",
            "GET /db/latest-todolist - 从数据库获取最新ToDoList",
            "GET /db/member-workload - 获取成员工作负载统计",
            "GET /db/daily-summary - 获取指定日期ToDoList汇总",
            "GET /db/health - 检查数据库连接健康状态"
        ]
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "ai_available": bool(API_KEY),
        "ai_provider": "OpenRouter Gemini 2.5",
        "ai_model": AI_MODEL,
        "version": "2.7.0",
        "features": {
            "chat_messages": True,
            "ai_analysis": bool(API_KEY),
            "daily_todolist": True,
            "webhook_support": True,
            "database_storage": True,
            "workload_analytics": True
        }
    }

@app.post("/ai-analyze")
async def ai_analyze_project(request: AIProcessRequest):
    """
    AI分析项目对话，按人员分组提取TODO/DONE/ISSUES任务 (纯AI模式)
    """
    try:
        print(f"🔍 开始项目分析请求: {request.container_id}")
        
        # 1. 获取消息
        fetcher = FeishuMessageFetcher(
            app_id=APP_ID,
            app_secret=APP_SECRET,
            download_path=request.download_path
        )
        
        messages_data = fetcher.get_all_messages(
            container_id=request.container_id,
            start_time=request.start_time,
            end_time=request.end_time,
            download_files=request.download_files
        )
        
        # 2. AI项目分析 (仅使用AI)
        ai_api_key = request.ai_api_key or API_KEY
        if not ai_api_key:
            raise ValueError("需要OpenRouter API密钥才能进行分析")
            
        analyzer = AIProjectAnalyzer(
            api_key=ai_api_key,
            model=AI_MODEL
        )
        
        analysis_result = analyzer.analyze_project_context(messages_data)
        
        # 3. 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"project_analysis_{timestamp}.json"
        analyzer.save_analysis_result(analysis_result, output_file)
        
        return {
            "success": True,
            "message": "AI项目分析完成",
            "data": analysis_result,
            "output_file": output_file,
            "processing_mode": "OpenRouter Gemini 2.5",
            "ai_model": AI_MODEL
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI项目分析失败: {str(e)}")

@app.post("/ai-analyze-today")
async def ai_analyze_today_project(request: TimeRangeRequest):
    """
    AI分析今天的项目对话
    """
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    ai_request = AIProcessRequest(
        container_id=request.container_id,
        start_time=str(int(today_start.timestamp())),
        end_time=str(int(now.timestamp())),
        download_files=request.download_files,
        use_ai=True
    )
    
    return await ai_analyze_project(ai_request)

@app.post("/daily-todolist")
async def generate_daily_todolist(request: TimeRangeRequest):
    """
    生成今日ToDoList - 简化版本：仅分析昨天10:30到今天10:30的消息
    """
    try:
        print(f"📅 开始生成今日ToDoList: {request.container_id}")
        
        # 计算时间范围：昨天10:30到今天10:30
        now = datetime.now()
        today_1030 = datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=10, minutes=30)
        yesterday_1030 = today_1030 - timedelta(days=1)
        
        print(f"⏰ 时间范围: {yesterday_1030.strftime('%Y-%m-%d %H:%M:%S')} 到 {today_1030.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 获取消息
        fetcher = FeishuMessageFetcher(
            app_id=APP_ID,
            app_secret=APP_SECRET,
            download_path=request.download_path
        )
        
        messages_data = fetcher.get_all_messages(
            container_id=request.container_id,
            start_time=str(int(yesterday_1030.timestamp())),
            end_time=str(int(today_1030.timestamp())),
            download_files=False  # 不下载文件，专注文本分析
        )
        
        print(f"📥 获取到 {messages_data.get('total_count', 0)} 条消息")
        
        # 2. 简化AI分析：只处理消息，不包含会议记录
        analyzer = AIProjectAnalyzer(
            api_key=API_KEY,
            model=AI_MODEL
        )
        
        daily_todolist = await generate_simple_daily_todolist(
            analyzer, messages_data
        )
        
        # 3. 保存今日ToDoList到文件
        today_date = now.strftime("%Y%m%d")
        output_file = f"daily_todolist_{today_date}.json"
        analyzer.save_analysis_result(daily_todolist, output_file)
        
        # 4. 保存到数据库
        database_saved = False
        try:
            db_manager = get_database_manager()
            analysis_id = db_manager.save_todolist_analysis(daily_todolist)
            print(f"📊 ToDoList已保存到数据库，分析ID: {analysis_id}")
            database_saved = True
        except Exception as db_error:
            print(f"⚠️ 数据库保存失败: {db_error}")
            # 数据库保存失败不影响API返回结果
        
        print(f"✅ 今日ToDoList生成完成: {output_file}")
        
        return {
            "success": True,
            "message": "今日ToDoList生成完成",
            "data": daily_todolist,
            "output_file": output_file,
            "time_range": {
                "start": yesterday_1030.strftime('%Y-%m-%d %H:%M:%S'),
                "end": today_1030.strftime('%Y-%m-%d %H:%M:%S')
            },
            "total_messages": messages_data.get('total_count', 0),
            "total_meetings": 0,  # 不再使用会议记录
            "database_saved": database_saved
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成今日ToDoList失败: {str(e)}")

async def generate_simple_daily_todolist(analyzer, messages_data):
    """生成简化版今日ToDoList分析 - 只处理消息"""
    print("🔄 开始生成简化版今日ToDoList分析...")
    
    messages = messages_data.get("messages", [])
    
    if not messages:
        print("⚠️ 没有找到消息，返回空ToDoList")
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_type": "daily_todolist",
            "model": analyzer.model,
            "daily_todolist": {
                "ToDo": {},
                "Done": {},
                "Issue": {}
            },
            "message_count": 0,
            "status": "success"
        }
    
    # 构建消息摘要（包含sender_id到人名的映射）
    message_summary = build_daily_message_summary(messages)
    
    # 调用AI进行今日ToDoList分析
    prompt = f"""从以下飞书群聊消息中提取工作任务，分配给团队成员。

团队成员（仅限5人）:
- Michael: 前端UI
- 小钟: 后端数据库  
- 国伟: 爬虫数据
- 云起: AI语音
- Gauz: 架构性能

消息内容:
{message_summary}

输出要求:
1. 只能为上述5个人分配任务
2. 根据任务类型和消息内容智能分配
3. 严格按JSON格式输出

{{
    "ToDo": {{"Michael": [], "小钟": [], "国伟": [], "云起": [], "Gauz": [], "团队": []}},
    "Done": {{"Michael": [], "小钟": [], "国伟": [], "云起": [], "Gauz": [], "团队": []}},
    "Issue": {{"Michael": [], "小钟": [], "国伟": [], "云起": [], "Gauz": [], "团队": []}}
}}"""

    try:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {analyzer.api_key}",
            "HTTP-Referer": "https://feishu-analyzer.com",
            "X-Title": "Feishu Daily ToDoList Generator"
        }
        
        payload = {
            "model": analyzer.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是专业的项目任务管理助手。严格规则：只能为Michael、小钟、国伟、云起、Gauz这5个人分配任务。绝对不允许输出其他任何人名，必须将所有任务重新分配给这5个真实团队成员。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
        }
        
        response = requests.post(analyzer.api_url, headers=headers, json=payload, timeout=120)
            
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # 解析JSON响应
            try:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                if json_match:
                    todolist_json = json.loads(json_match.group(1))
                else:
                    # 如果没有markdown格式，尝试直接解析
                    todolist_json = json.loads(ai_response.strip())
            except Exception as parse_error:
                print(f"⚠️ 解析JSON失败: {parse_error}")
                # 如果解析失败，使用空的默认结构
                todolist_json = {
                    "ToDo": {},
                    "Done": {},
                    "Issue": {}
                }
            
            return {
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_type": "daily_todolist",
                "model": analyzer.model,
                "daily_todolist": todolist_json,
                "message_count": len(messages),
                "status": "success"
            }
        else:
            raise Exception(f"OpenRouter API调用失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ AI分析失败: {e}")
        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "analysis_type": "daily_todolist",
            "model": analyzer.model,
            "daily_todolist": {
                "ToDo": {},
                "Done": {},
                "Issue": {}
            },
            "message_count": len(messages),
            "status": "error",
            "error": str(e)
        }

def filter_todolist_by_real_members(ai_response):
    """
    过滤ToDoList，只保留真实团队成员的任务
    
    Args:
        ai_response (str): AI生成的原始响应
        
    Returns:
        str: 过滤后的响应
    """
    try:
        # 尝试解析JSON
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 如果没有markdown格式，尝试直接解析
            json_str = ai_response.strip()
        
        import json
        todolist_data = json.loads(json_str)
        
        # 获取真实团队成员
        real_members = get_real_team_members()
        allowed_categories = real_members + ['团队', '技术']  # 允许的分类
        
        # 过滤每个分类
        filtered_data = {}
        for category in ['ToDo', 'Done', 'Issue']:
            if category in todolist_data:
                filtered_category = {}
                for person, tasks in todolist_data[category].items():
                    # 标准化人员名称
                    normalized_name = normalize_team_member_name(person)
                    if normalized_name:
                        # 使用标准化的名称
                        if normalized_name in filtered_category:
                            filtered_category[normalized_name].extend(tasks)
                        else:
                            filtered_category[normalized_name] = tasks
                    elif person in ['团队', '技术']:
                        # 保留团队和技术分类
                        if person in filtered_category:
                            filtered_category[person].extend(tasks)
                        else:
                            filtered_category[person] = tasks
                    else:
                        print(f"⚠️ 过滤掉无效人员: {person}")
                
                filtered_data[category] = filtered_category
        
        # 重新生成JSON响应
        filtered_json = json.dumps(filtered_data, ensure_ascii=False, indent=2)
        filtered_response = f"```json\n{filtered_json}\n```"
        
        print(f"✅ ToDoList过滤完成，只保留真实团队成员: {', '.join(real_members)}")
        return filtered_response
        
    except Exception as e:
        print(f"⚠️ ToDoList过滤失败: {e}")
        return ai_response  # 返回原始响应

def build_daily_message_summary(messages):
    """构建每日消息摘要"""
    if not messages:
        return "无消息内容"
    
    summary = f"### 今日工作消息汇总 ({len(messages)}条)\n\n"
    
    # 按时间排序消息
    sorted_messages = sorted(messages, key=lambda x: int(x.get('create_time', 0)))
    
    for i, msg in enumerate(sorted_messages):
        msg_type = msg.get('msg_type', '')
        sender_id = msg.get('sender', {}).get('id', 'unknown')
        
        # 获取真实用户名，并统一映射为真实团队成员
        sender_name = get_user_name_by_feishu_id(sender_id)
        
        # 将发送者统一映射为真实团队成员
        if sender_name in ['钟悦心', '小钟阿朱', '小明']:
            sender_name = '小钟'
        elif sender_name == '王子健':
            sender_name = 'Michael'
        elif sender_name.startswith('用户'):
            sender_name = "团队成员"
        elif sender_name not in ['Michael', '小钟', '国伟', '云起', 'Gauz']:
            sender_name = "团队成员"
        
        try:
            timestamp = datetime.fromtimestamp(int(msg.get('create_time', 0)) / 1000).strftime("%m-%d %H:%M")
        except:
            timestamp = f"消息{i+1}"
        
        if msg_type == 'text':
            text = msg.get('text', '')
            # 处理飞书富文本格式
            if '<p>' in text:
                import re
                clean_text = re.sub(r'<[^>]+>', '', text)
                clean_text = clean_text.replace('&nbsp;', ' ').strip()
                text = clean_text
            
            # 在消息内容中也替换所有人名为真实团队成员
            text = replace_user_ids_in_text(text)
            
            # 进一步替换消息内容中的人名
            name_mapping = {
                '钟悦心': '小钟',
                '小钟阿朱': '小钟', 
                '小明': '小钟',
                '王子健': 'Michael',
                '前端团队': '团队',
                '技术团队': '团队',
                '开发团队': '团队'
            }
            
            for old_name, new_name in name_mapping.items():
                text = text.replace(old_name, new_name)
            
            # 限制单条消息长度，避免过长
            if len(text) > 500:
                text = text[:500] + "..."
            
            summary += f"**[{timestamp}] {sender_name}**: {text}\n\n"
    
    return summary

# @app.post("/webhook/event")
# async def handle_event(request: Request, background_tasks: BackgroundTasks):
#     """
#     接收飞书事件回调 - 支持URL验证，简化事件处理
#     """
#     try:
#         # 获取请求体
#         req_body = await request.json()
#         print(f"收到飞书事件: {json.dumps(req_body, indent=2, ensure_ascii=False)}")
        
#         # 处理URL验证请求
#         if req_body.get("type") == "url_verification":
#             challenge = req_body.get("challenge", "")
#             print(f"🔗 飞书URL验证请求，返回challenge: {challenge}")
#             return {"challenge": challenge}
        
#         # 处理正常的事件回调
#         req_event = req_body.get("event", {})
        
#         # 检查是否是消息事件
#         if req_event.get("type") == "message":
#             message_content = req_event.get("message", {})
#             chat_id = message_content.get("chat_id")
#             message_type = message_content.get("message_type", "")
            
#             print(f"📨 收到群聊消息事件: {chat_id}")
            
#             # 简化处理：只记录事件，不触发自动分析
#             # 用户可以手动调用 /daily-todolist API 生成ToDoList
#             return {
#                 "success": True,
#                 "message": "消息事件已接收",
#                 "container_id": chat_id,
#                 "note": "请手动调用 /daily-todolist API 生成每日ToDoList"
#             }
        
#         # 其他事件类型
#         print(f"📨 收到其他类型事件: {req_event.get('type', 'unknown')}")
#         return {
#             "success": True,
#             "message": "事件已接收",
#             "event_type": req_event.get("type", "unknown")
#         }
        
#     except Exception as e:
#         print(f"❌ 处理webhook事件失败: {str(e)}")
#         return {
#             "success": False,
#             "error": str(e)
#         }

@app.post("/fetch-messages")
async def fetch_messages(request: MessageRequest):
    """
    获取群聊消息（完整参数版本）
    """
    try:
        print(f"📥 开始获取消息: {request.container_id}")
        
        fetcher = FeishuMessageFetcher(
            app_id=APP_ID,
            app_secret=APP_SECRET,
            download_path=request.download_path
        )
        
        messages_data = fetcher.get_all_messages(
            container_id=request.container_id,
            start_time=request.start_time,
            end_time=request.end_time,
            download_files=request.download_files
        )
        
        # 保存消息数据
        output_file = fetcher.save_messages_to_json(messages_data)
        
        # 获取统计信息
        stats = _get_message_type_stats(messages_data.get("messages", []))
        total_files = _count_total_files(messages_data.get("messages", []))
        
        return {
            "success": True,
            "message": "消息获取完成",
            "data": messages_data,
            "output_file": output_file,
            "statistics": {
                "total_messages": messages_data.get("total_count", 0),
                "message_types": stats,
                "total_files_downloaded": total_files,
                "time_range": messages_data.get("time_range", {})
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取消息失败: {str(e)}")

@app.post("/fetch-today")
async def fetch_today_messages(request: TimeRangeRequest):
    """
    获取今天的消息
    """
    now = datetime.now()
    today_start = datetime.combine(now.date(), datetime.min.time())
    
    message_request = MessageRequest(
        container_id=request.container_id,
        start_time=str(int(today_start.timestamp())),
        end_time=str(int(now.timestamp())),
        download_files=request.download_files,
        download_path=request.download_path
    )
    
    return await fetch_messages(message_request)

@app.post("/fetch-yesterday")
async def fetch_yesterday_messages(request: TimeRangeRequest):
    """
    获取昨天的消息
    """
    now = datetime.now()
    yesterday_start = datetime.combine((now - timedelta(days=1)).date(), datetime.min.time())
    yesterday_end = datetime.combine(now.date(), datetime.min.time())
    
    message_request = MessageRequest(
        container_id=request.container_id,
        start_time=str(int(yesterday_start.timestamp())),
        end_time=str(int(yesterday_end.timestamp())),
        download_files=request.download_files,
        download_path=request.download_path
    )
    
    return await fetch_messages(message_request)

@app.post("/fetch-async")
async def fetch_messages_async(request: MessageRequest, background_tasks: BackgroundTasks):
    """
    异步获取消息 - 立即返回任务ID，后台处理
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # 存储任务状态
    task_status[task_id] = {
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "container_id": request.container_id
    }
    
    # 添加后台任务
    background_tasks.add_task(_fetch_messages_background, task_id, request)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "任务已提交，请使用task_id查询进度"
    }

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    查询异步任务状态
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务ID不存在")
    
    return task_status[task_id]

async def _fetch_messages_background(task_id: str, request: MessageRequest):
    """
    后台消息获取任务
    """
    try:
        # 更新状态为进行中
        task_status[task_id]["status"] = "running"
        task_status[task_id]["started_at"] = datetime.now().isoformat()
        
        # 执行获取任务
        fetcher = FeishuMessageFetcher(
            app_id=APP_ID,
            app_secret=APP_SECRET,
            download_path=request.download_path
        )
        
        messages_data = fetcher.get_all_messages(
            container_id=request.container_id,
            start_time=request.start_time,
            end_time=request.end_time,
            download_files=request.download_files
        )
        
        # 保存消息数据
        output_file = fetcher.save_messages_to_json(messages_data)
        
        # 获取统计信息
        stats = _get_message_type_stats(messages_data.get("messages", []))
        total_files = _count_total_files(messages_data.get("messages", []))
        
        # 更新任务状态为完成
        task_status[task_id].update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": {
                "output_file": output_file,
                "total_messages": messages_data.get("total_count", 0),
                "message_types": stats,
                "total_files_downloaded": total_files
            }
        })
        
    except Exception as e:
        # 更新任务状态为失败
        task_status[task_id].update({
            "status": "failed",
            "failed_at": datetime.now().isoformat(),
            "error": str(e)
        })

def _get_message_type_stats(messages):
    """统计消息类型分布"""
    stats = {}
    for msg in messages:
        msg_type = msg.get("msg_type", "unknown")
        stats[msg_type] = stats.get(msg_type, 0) + 1
    return stats

def _count_total_files(messages):
    """统计下载的文件总数"""
    total = 0
    for msg in messages:
        total += len(msg.get("files", []))
    return total

# =============================================================================
# 数据库查询API
# =============================================================================

@app.get("/db/latest-todolist")
async def get_latest_todolist_from_db(container_id: str = None):
    """
    从数据库获取最新的ToDoList
    """
    try:
        db_manager = get_database_manager()
        todolist_data = db_manager.get_latest_todolist(container_id)
        
        if not todolist_data:
            return {
                "success": False,
                "message": "未找到ToDoList数据",
                "data": None
            }
        
        return {
            "success": True,
            "message": "获取最新ToDoList成功",
            "data": todolist_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取ToDoList失败: {str(e)}")

@app.get("/db/member-workload")
async def get_member_workload_stats(days: int = 7):
    """
    获取成员工作负载统计（最近N天）
    """
    try:
        db_manager = get_database_manager()
        workload_stats = db_manager.get_member_workload_stats(days)
        
        return {
            "success": True,
            "message": f"获取最近{days}天工作负载统计成功",
            "data": workload_stats,
            "summary": {
                "total_members": len(set(item['assignee'] for item in workload_stats)),
                "date_range": f"最近{days}天",
                "total_records": len(workload_stats)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取工作负载统计失败: {str(e)}")

@app.get("/db/daily-summary")
async def get_daily_summary_from_db(target_date: str = None):
    """
    获取指定日期的ToDoList汇总
    格式: YYYY-MM-DD，默认为今天
    """
    try:
        from datetime import date
        
        # 解析日期
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
        else:
            target_date_obj = date.today()
        
        db_manager = get_database_manager()
        summary_data = db_manager.get_daily_summary(target_date_obj)
        
        return {
            "success": True,
            "message": f"获取{target_date_obj}的ToDoList汇总成功",
            "data": summary_data,
            "target_date": target_date_obj.isoformat(),
            "total_categories": len(set(item['category'] for item in summary_data if item['category'])),
            "total_assignees": len(set(item['assignee'] for item in summary_data if item['assignee']))
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用YYYY-MM-DD格式")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取每日汇总失败: {str(e)}")

@app.get("/db/health")
async def check_database_health():
    """
    检查数据库连接健康状态
    """
    try:
        db_manager = get_database_manager()
        
        # 简单查询测试连接
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM todolist_analysis")
                result = cursor.fetchone()
                total_analysis = result[0] if result else 0
                
                cursor.execute("SELECT COUNT(*) as total FROM todolist_items")
                result = cursor.fetchone()
                total_items = result[0] if result else 0
        
        return {
            "status": "healthy",
            "database": db_manager.config['database'],
            "host": db_manager.config['host'],
            "statistics": {
                "total_analysis_records": total_analysis,
                "total_todo_items": total_items
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =============================================================================
# 会议记录处理功能 - 新增
# =============================================================================

class MeetingProcessor:
    """会议记录处理器"""
    
    def __init__(self):
        """初始化会议记录处理器"""
        # DeepSeek API配置
        self.deepseek_url = 'https://api.deepseek.com/v1'
        self.deepseek_key = 'sk-d2513b4c4626409599a73ba64b2e9033'
        
        # MySQL配置 - 会议记录数据库
        self.mysql_config = {
            'host': 'gz-cdb-e0aa423v.sql.tencentcdb.com',
            'port': 20236,
            'user': 'root',
            'password': 'Aa@114514',
            'database': 'meeting_summaries_db'
        }
        
        # 初始化飞书机器人发送器
        try:
            from feishu_bot_sender import FeishuBotSender
            self.feishu_bot = FeishuBotSender(
                app_id=APP_ID,
                app_secret=APP_SECRET,
                container_id=DEFAULT_CONTAINER_ID
            )
        except Exception as e:
            print(f"⚠️ 飞书机器人初始化失败: {e}")
            self.feishu_bot = None
    
    def get_mysql_connection(self):
        """获取MySQL数据库连接"""
        try:
            connection = mysql.connector.connect(**self.mysql_config)
            return connection
        except Error as e:
            raise Exception(f"MySQL连接失败: {e}")
    
    def process_meeting_transcript(self, transcript_content: str) -> dict:
        """处理会议记录，使用DeepSeek API分析"""
        
        prompt = f"""
你是一个专业的会议摘要分析专家。请仔细分析以下会议记录，生成一个详细、结构化的会议摘要。

请以JSON格式返回以下结构，注意摘要要详细、分段落呈现，重点突出待办事项、已完成事项和重要问题：

{{
    "summary": "详细的会议总结，要求：1)第一段是会议整体概述，包含主要议题、参与情况、会议目标和总体进展；2)第二段详述重点讨论内容；3)第三段说明会议成果和后续安排。每段应当详细、具体，不少于100字。",
    "participants": ["参与者姓名列表"],
    "keywords": ["关键词列表，提取5-8个最重要的关键词"],
    "todos": [{{"task": "待办任务描述", "assignee": "负责人", "deadline": "截止时间/预计完成时间", "priority": "high/medium/low", "details": "任务详细说明和要求"}}],
    "dones": [{{"achievement": "已完成事项描述", "contributor": "贡献者", "impact": "影响和意义", "details": "完成情况的详细说明"}}],
    "major_issues": [{{"issue": "重要问题描述", "impact": "问题影响", "urgency": "紧急程度", "proposed_solutions": ["建议解决方案"], "discussion_points": ["相关讨论要点"]}}],
    "key_decisions": [{{"decision": "决策描述", "context": "决策背景", "impact": "预期影响", "owner": "负责人", "rationale": "决策理由"}}],
    "action_items": [{{"task": "行动项", "assignee": "指派人", "priority": "high/medium/low", "status": "new", "context": "任务背景"}}],
    "next_steps": [{{"step": "下一步行动", "timeline": "时间安排", "dependencies": ["依赖条件"], "owner": "负责人"}}],
    "technical_discussions": [{{"topic": "技术主题", "discussion": "讨论内容", "decisions": ["技术决策"], "concerns": ["技术关注点"], "follow_ups": ["后续技术工作"]}}],
    "ai_related_topics": [{{"topic": "AI相关主题", "discussion": "讨论内容", "tools_mentioned": ["提及的AI工具"], "outcomes": ["讨论结果"], "implications": ["对项目的影响"]}}],
    "meeting_highlights": {{
        "most_important_decision": "最重要的决策",
        "biggest_challenge": "最大的挑战",
        "key_breakthrough": "重要突破或进展",
        "urgent_attention_needed": "需要紧急关注的事项"
    }},
    "meeting_type": "根据内容判断：project_review/planning/brainstorming/decision_making/status_update/technical_discussion",
    "priority_level": "1-5的优先级评分，5为最高",
    "tags": ["会议标签，如：紧急、重要、例行、技术、商务等"]
}}

分析要求：
1. 摘要必须详细具体，分3个自然段，每段不少于100字
2. TODOs（待办事项）要明确任务、责任人、时间要求
3. DONEs（已完成事项）要说明成果和价值
4. 重要问题要评估影响和紧急程度
5. 用中文表达，语言正式但易懂
6. 关注项目进展、技术难点、资源需求、风险控制等关键要素

会议记录：
{transcript_content}
"""

        try:
            headers = {
                'Authorization': f'Bearer {self.deepseek_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': '你是一位资深的项目管理专家和会议分析师，擅长从会议记录中提取关键信息，生成高质量的会议摘要。你的分析要详细、准确、有洞察力，能够突出重点并识别潜在问题。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 6000
            }
            
            response = requests.post(
                f'{self.deepseek_url}/chat/completions',
                headers=headers,
                json=data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    parsed_result = json.loads(json_content)
                    return parsed_result
            
            raise Exception(f"DeepSeek API调用失败: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"DeepSeek处理失败: {e}")
    
    def save_meeting_summary(self, summary_data: dict, original_transcript: str = "") -> int:
        """保存会议摘要到数据库"""
        try:
            connection = self.get_mysql_connection()
            
            # 准备摘要文本
            summary_text = summary_data.get('summary', '')
            
            # 添加结构化信息到摘要文本
            if summary_data.get('todos'):
                summary_text += "\n\n🔥 待办事项:\n"
                for i, todo in enumerate(summary_data['todos'], 1):
                    summary_text += f"{i}. {todo.get('task', '')} (负责人: {todo.get('assignee', '未指定')}, 截止: {todo.get('deadline', '待定')})\n"
            
            if summary_data.get('dones'):
                summary_text += "\n\n✅ 已完成事项:\n"
                for i, done in enumerate(summary_data['dones'], 1):
                    summary_text += f"{i}. {done.get('achievement', '')} (贡献者: {done.get('contributor', '团队')})\n"
            
            if summary_data.get('major_issues'):
                summary_text += "\n\n⚠️ 重要问题:\n"
                for i, issue in enumerate(summary_data['major_issues'], 1):
                    summary_text += f"{i}. {issue.get('issue', '')} (紧急程度: {issue.get('urgency', '待定')})\n"
            
            # 插入数据库
            cursor = connection.cursor()
            
            insert_query = """
            INSERT INTO meeting_summaries 
            (meeting_transcript, meeting_summary, meeting_date, participants, meeting_type, ai_provider, processing_status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                original_transcript,
                summary_text,
                datetime.now().isoformat(),
                json.dumps(summary_data.get('participants', [])),
                summary_data.get('meeting_type', 'general'),
                'deepseek',
                'completed'
            )
            
            cursor.execute(insert_query, values)
            connection.commit()
            
            meeting_id = cursor.lastrowid
            
            cursor.close()
            connection.close()
            
            return meeting_id
            
        except Exception as e:
            raise Exception(f"保存会议摘要失败: {e}")
    
    def send_to_feishu_group(self, summary_data: dict) -> bool:
        """发送会议摘要到飞书群"""
        if not self.feishu_bot:
            print("⚠️ 飞书机器人未初始化")
            return False
        
        try:
            return self.feishu_bot.send_summary_to_group(summary_data)
        except Exception as e:
            print(f"❌ 发送到飞书失败: {e}")
            return False

# 初始化会议处理器
meeting_processor = MeetingProcessor()

# 会议记录请求模型
class MeetingTranscriptRequest(BaseModel):
    transcript: str

class MeetingSummaryRequest(BaseModel):
    summary: dict
    transcript: str = ""

@app.post("/meeting/analyze")
async def analyze_meeting_transcript(request: MeetingTranscriptRequest):
    """
    分析会议记录 - 使用DeepSeek AI生成结构化摘要
    """
    try:
        print(f"📝 开始分析会议记录，长度: {len(request.transcript)}字符")
        
        # 使用DeepSeek AI分析会议记录
        summary_data = meeting_processor.process_meeting_transcript(request.transcript)
        
        print(f"✅ 会议记录分析完成")
        
        return {
            "success": True,
            "message": "会议记录分析完成",
            "data": summary_data,
            "processing_info": {
                "ai_provider": "DeepSeek",
                "transcript_length": len(request.transcript),
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ 会议记录分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"会议记录分析失败: {str(e)}")

@app.post("/meeting/save")
async def save_meeting_summary(request: MeetingSummaryRequest):
    """
    保存会议摘要到数据库
    """
    try:
        print("💾 开始保存会议摘要到数据库...")
        
        # 保存到数据库
        meeting_id = meeting_processor.save_meeting_summary(
            request.summary, 
            request.transcript
        )
        
        print(f"✅ 会议摘要已保存，ID: {meeting_id}")
        
        return {
            "success": True,
            "message": "会议摘要保存成功",
            "meeting_id": meeting_id,
            "database": "meeting_summaries_db"
        }
        
    except Exception as e:
        print(f"❌ 保存会议摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存会议摘要失败: {str(e)}")

@app.post("/meeting/send-feishu")
async def send_meeting_to_feishu(request: dict):
    """
    发送会议摘要到飞书群
    """
    try:
        print("📤 开始发送会议摘要到飞书群...")
        
        summary_data = request.get('summary', {})
        
        # 发送到飞书群
        success = meeting_processor.send_to_feishu_group(summary_data)
        
        if success:
            print("✅ 会议摘要已发送到飞书群")
            return {
                "success": True,
                "message": "会议摘要已发送到飞书群",
                "container_id": DEFAULT_CONTAINER_ID
            }
        else:
            raise Exception("发送到飞书群失败")
            
    except Exception as e:
        print(f"❌ 发送到飞书群失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送到飞书群失败: {str(e)}")

@app.post("/meeting/process-complete")
async def process_meeting_complete(file: UploadFile = File(...)):
    """
    完整的会议记录处理流程：上传文件 → AI分析 → 保存数据库 → 发送飞书群
    """
    try:
        print(f"🔄 开始完整会议记录处理流程：{file.filename}")
        
        # 1. 读取上传的文件
        content = await file.read()
        transcript_text = content.decode('utf-8')
        
        print(f"📖 文件读取完成，内容长度: {len(transcript_text)}字符")
        
        # 2. AI分析会议记录
        print("🤖 开始AI分析...")
        summary_data = meeting_processor.process_meeting_transcript(transcript_text)
        
        # 3. 保存到数据库
        print("💾 保存到数据库...")
        meeting_id = meeting_processor.save_meeting_summary(summary_data, transcript_text)
        
        # 4. 发送到飞书群
        print("📤 发送到飞书群...")
        feishu_success = meeting_processor.send_to_feishu_group(summary_data)
        
        print(f"✅ 完整流程处理完成！")
        
        return {
            "success": True,
            "message": "会议记录处理完成",
            "processing_steps": {
                "1_file_upload": "✅ 完成",
                "2_ai_analysis": "✅ 完成", 
                "3_database_save": f"✅ 完成 (ID: {meeting_id})",
                "4_feishu_send": "✅ 完成" if feishu_success else "❌ 失败"
            },
            "data": {
                "meeting_id": meeting_id,
                "summary": summary_data,
                "transcript_length": len(transcript_text),
                "feishu_sent": feishu_success
            },
            "next_steps": [
                "会议摘要已发送到飞书群",
                "可以调用 /daily-todolist 生成包含会议内容的ToDoList",
                "团队成员可以在飞书群中看到会议摘要"
            ]
        }
        
    except Exception as e:
        print(f"❌ 完整流程处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"会议记录处理失败: {str(e)}")

# =============================================================================
# 会议记录处理功能结束
# =============================================================================

if __name__ == "__main__":
    # 启动API服务器
    print("🚀 启动飞书消息获取&AI分析API服务...")
    print(f"📊 API文档地址: http://localhost:8000/docs")
    print(f"🔧 健康检查: http://localhost:8000/health")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000
    ) 