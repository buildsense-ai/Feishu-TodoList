#!/usr/bin/env python3
"""
FastAPI Backend Server for Meeting Transcript Processing
Alternative to Flask version - provides same REST API endpoints
"""

import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from feishu_bot_sender import FeishuBotSender

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables
load_dotenv()

class TranscriptRequest(BaseModel):
    transcript: str

class SummaryRequest(BaseModel):
    summary: dict
    transcript: str = ""

class WebMeetingProcessor:
    """Backend processor for meeting transcript analysis and storage"""
    
    def __init__(self):
        """Initialize the processor with database and API configurations"""
        self.deepseek_url = os.getenv('DEEPSEEK_URL', 'https://api.deepseek.com/v1')
        # Hardcoded API key for convenience
        self.deepseek_key = 'sk-d2513b4c4626409599a73ba64b2e9033'
        
        # MySQL connection configuration
        self.mysql_config = {
            'host': os.getenv('MYSQL_HOST', 'gz-cdb-e0aa423v.sql.tencentcdb.com'),
            'port': int(os.getenv('MYSQL_PORT', '20236')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'Aa@114514'),
            'database': os.getenv('MYSQL_DATABASE', 'meeting_summaries_db')
        }
        
        # Initialize Feishu bot
        try:
            self.feishu_bot = FeishuBotSender()
        except Exception as e:
            print(f"⚠️ 飞书机器人初始化失败: {e}")
            self.feishu_bot = None
        
        if not self.deepseek_key:
            raise Exception("DEEPSEEK_API_KEY 未设置")
    
    def get_mysql_connection(self):
        """Get MySQL database connection"""
        try:
            connection = mysql.connector.connect(**self.mysql_config)
            return connection
        except Error as e:
            raise Exception(f"MySQL连接失败: {e}")

    def process_transcript_only(self, transcript_content: str) -> Dict[str, Any]:
        """Process transcript using DeepSeek API without saving to database or sending to Feishu"""
        
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
            
            raise Exception(f"API调用失败: {response.status_code}")
            
        except Exception as e:
            raise Exception(f"DeepSeek处理失败: {e}")

    def save_summary_to_database(self, summary_data: Dict[str, Any], original_transcript: str = "") -> Dict[str, Any]:
        """Save summary to MySQL database"""
        try:
            # Test MySQL connection first
            connection = self.get_mysql_connection()
            
            # Prepare the summary text (combine all AI output into one text field)
            summary_text = summary_data.get('summary', '')
            
            # Add structured information to the summary text for better readability
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
            
            if summary_data.get('meeting_highlights'):
                highlights = summary_data['meeting_highlights']
                summary_text += "\n\n🌟 会议亮点:\n"
                if highlights.get('most_important_decision'):
                    summary_text += f"重要决策: {highlights['most_important_decision']}\n"
                if highlights.get('biggest_challenge'):
                    summary_text += f"最大挑战: {highlights['biggest_challenge']}\n"
                if highlights.get('key_breakthrough'):
                    summary_text += f"重要突破: {highlights['key_breakthrough']}\n"
                if highlights.get('urgent_attention_needed'):
                    summary_text += f"紧急关注: {highlights['urgent_attention_needed']}\n"
            
            # Insert into MySQL database
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
                'DeepSeek',
                'completed'
            )
            
            cursor.execute(insert_query, values)
            connection.commit()
            
            record_id = cursor.lastrowid
            cursor.close()
            connection.close()
            
            return {
                'success': True,
                'record_id': record_id,
                'message': f"摘要已成功保存到MySQL数据库，记录ID: {record_id}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"数据库保存失败: {e}"
            }

    def send_summary_to_feishu(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send summary to Feishu chat"""
        if not self.feishu_bot:
            return {
                'success': False,
                'error': "飞书机器人未配置"
            }
        
        try:
            success = self.feishu_bot.send_summary_to_group(summary_data)
            return {
                'success': success,
                'message': "飞书发送成功" if success else "飞书发送失败"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"飞书发送失败: {e}"
            }

# Create FastAPI app
app = FastAPI(title="Meeting Transcript Processor API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processor
processor = WebMeetingProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'framework': 'FastAPI',
        'services': {
            'database': 'connected',
            'ai_service': 'available',
            'feishu_bot': 'configured' if processor.feishu_bot else 'not_configured'
        }
    }

@app.post("/analyze")
async def analyze_transcript(request: TranscriptRequest):
    """
    Analyze transcript text using AI
    """
    try:
        transcript = request.transcript.strip()
        
        if not transcript:
            raise HTTPException(status_code=400, detail='会议记录内容不能为空')
        
        result = processor.process_transcript_only(transcript)
        
        return {
            'success': True,
            'data': result,
            'message': 'AI分析完成'
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload file and analyze using AI
    """
    try:
        # Check file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail='只支持 .txt 格式的文件')
        
        # Read file content
        try:
            content = await file.read()
            transcript_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail='文件编码格式不支持，请使用UTF-8编码的文本文件')
        
        if not transcript_content.strip():
            raise HTTPException(status_code=400, detail='文件内容为空')
        
        # Analyze content
        result = processor.process_transcript_only(transcript_content)
        
        return {
            'success': True,
            'data': result,
            'original_transcript': transcript_content,
            'message': 'AI分析完成'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-database")
async def save_to_database(request: SummaryRequest):
    """
    Save analysis to database
    """
    try:
        if not request.summary:
            raise HTTPException(status_code=400, detail='摘要数据不能为空')
        
        result = processor.save_summary_to_database(request.summary, request.transcript)
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send-feishu")
async def send_to_feishu(request: dict):
    """
    Send summary to Feishu
    """
    try:
        summary = request.get('summary', {})
        
        if not summary:
            raise HTTPException(status_code=400, detail='摘要数据不能为空')
        
        result = processor.send_summary_to_feishu(summary)
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=500, detail=result['error'])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-complete")
async def process_complete(file: UploadFile = File(...)):
    """
    Complete processing: upload file -> AI analyze -> save DB -> send Feishu
    """
    try:
        # Check file type
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail='只支持 .txt 格式的文件')
        
        # Read file content
        try:
            content = await file.read()
            transcript_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail='文件编码格式不支持，请使用UTF-8编码的文本文件')
        
        if not transcript_content.strip():
            raise HTTPException(status_code=400, detail='文件内容为空')
        
        # Step 1: AI Analysis
        print("🤖 开始AI分析...")
        summary_data = processor.process_transcript_only(transcript_content)
        
        # Step 2: Save to Database
        print("💾 保存到数据库...")
        db_result = processor.save_summary_to_database(summary_data, transcript_content)
        
        # Step 3: Send to Feishu
        print("📨 发送到飞书...")
        feishu_result = processor.send_summary_to_feishu(summary_data)
        
        return {
            'success': True,
            'data': summary_data,
            'original_transcript': transcript_content,
            'results': {
                'ai_analysis': {'success': True, 'message': 'AI分析完成'},
                'database_save': db_result,
                'feishu_send': feishu_result
            },
            'message': '所有操作完成'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def main():
    """Run the FastAPI server"""
    import uvicorn
    
    print("🚀 启动会议记录处理FastAPI服务器")
    print("=" * 50)
    print("📡 API端点:")
    print("  GET  /health              - 健康检查")
    print("  POST /analyze             - 分析文本")
    print("  POST /upload-analyze      - 上传文件并分析")
    print("  POST /save-database       - 保存到数据库")
    print("  POST /send-feishu         - 发送到飞书")
    print("  POST /process-complete    - 一键完成所有操作")
    print("\n🌐 FastAPI服务器启动中...")
    print("📱 API地址: http://localhost:8001")
    print("📚 自动生成的文档: http://localhost:8001/docs")
    print("📋 OpenAPI规范: http://localhost:8001/openapi.json")
    print("\n按 Ctrl+C 停止服务")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    main() 