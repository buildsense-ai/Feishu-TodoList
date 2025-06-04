import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests  # 用于调用OpenRouter API
import base64
import os
from dataclasses import dataclass
from feishu_user_id_mapper import get_user_name_by_feishu_id, replace_user_ids_in_text


@dataclass
class TaskItem:
    """单个任务项"""
    id: str
    title: str
    description: str
    assignee: str  # 负责人
    priority: str  # HIGH, MEDIUM, LOW
    status: str  # TODO, DONE, ISSUE
    tags: List[str]
    deadline: Optional[str] = None
    related_messages: List[str] = None  # 相关的消息ID
    confidence: float = 0.0


@dataclass
class PersonTasks:
    """个人任务汇总"""
    person_id: str
    person_name: str
    todos: List[TaskItem]
    dones: List[TaskItem] 
    issues: List[TaskItem]


class AIProjectAnalyzer:
    def __init__(self, api_key: str = None, model: str = "google/gemini-2.5-pro-preview", api_url: str = "https://openrouter.ai/api/v1/chat/completions"):
        """
        初始化AI项目分析器
        
        Args:
            api_key: OpenRouter API密钥
            model: 使用的模型名称（OpenRouter格式）
            api_url: OpenRouter API地址
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
    
    def analyze_project_context(self, messages_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析整个项目上下文，提取任务并按人员分组
        
        Args:
            messages_data: 从飞书获取的消息数据
            
        Returns:
            按人员分组的任务分析结果
        """
        print("🔍 开始项目上下文分析...")
        
        try:
            messages = messages_data.get("messages", [])
            if not messages:
                return self._create_empty_result()
            
            # 预处理消息，构建完整上下文
            print("📊 构建项目上下文...")
            context_data = self._build_project_context_with_documents(messages)
            
            # 使用AI进行深度分析
            print("🤖 开始AI任务分析...")
            if not self.api_key:
                raise ValueError("需要提供OpenRouter API密钥才能进行分析")
                
            analysis_result = self._analyze_with_openrouter_gemini(context_data)
            
            # 后处理和统计
            print("📋 组织分析结果...")
            final_result = self._organize_by_person(analysis_result, messages_data)
            
            print(f"✅ 项目分析完成，识别出 {len(analysis_result)} 个任务项")
            return final_result
            
        except Exception as e:
            print(f"❌ 项目分析过程中出错: {e}")
            print(f"❌ 错误类型: {type(e)}")
            import traceback
            print(f"❌ 错误详情: {traceback.format_exc()}")
            raise e
    
    def _build_project_context_with_documents(self, messages: List[Dict]) -> Dict[str, Any]:
        """构建项目上下文，暂时跳过文档处理以提高速度"""
        print("📊 构建项目上下文（仅文本消息）...")
        
        # 提取人员信息
        participants = {}
        
        # 按时间排序的消息
        sorted_messages = sorted(messages, key=lambda x: x.get("create_time", 0))
        
        # 构建对话上下文
        conversation_flow = []
        
        for msg in sorted_messages:
            msg_type = msg.get("msg_type", "")
            sender_info = msg.get("sender", {})
            sender_id = sender_info.get("id", "unknown")
            
            # 收集参与者信息
            if sender_id not in participants:
                participants[sender_id] = {
                    "id": sender_id,
                    "name": self._extract_person_name(sender_info),
                    "message_count": 0
                }
            participants[sender_id]["message_count"] += 1
            
            # 只处理文本消息，跳过文件消息以提高速度
            if msg_type == "text":
                text = msg.get("text", "").strip()
                if text and len(text) >= 2:
                    # 在文本内容中也替换用户ID为真实姓名
                    text = replace_user_ids_in_text(text)
                    conversation_item = {
                        "message_id": msg.get("message_id"),
                        "timestamp": msg.get("create_time"),
                        "sender": participants[sender_id],
                        "content": text,
                        "type": "text",
                        "mentions": msg.get("mentions", []),
                        "original_msg": msg
                    }
                    conversation_flow.append(conversation_item)
            
            # 对于文件消息，只记录文件名，不读取内容
            elif msg_type == "file":
                files = msg.get("files", [])
                for file_info in files:
                    file_name = file_info.get('file_name', '未知文档')
                    conversation_item = {
                        "message_id": msg.get("message_id"),
                        "timestamp": msg.get("create_time"),
                        "sender": participants[sender_id],
                        "content": f"[文档] {file_name}",
                        "type": "file_reference",
                        "file_info": file_info,
                        "original_msg": msg
                    }
                    conversation_flow.append(conversation_item)
        
        return {
            "participants": participants,
            "conversation_flow": conversation_flow,
            "document_contents": [],  # 暂时为空，不处理文档内容
            "total_messages": len(conversation_flow),
            "total_documents": 0,  # 暂时设为0
            "timespan": {
                "start": conversation_flow[0]["timestamp"] if conversation_flow else None,
                "end": conversation_flow[-1]["timestamp"] if conversation_flow else None
            }
        }
    
    def _extract_document_content(self, file_info: Dict) -> str:
        """提取文档内容"""
        try:
            file_path = file_info.get("file_path", "")
            file_name = file_info.get("file_name", "")
            
            if not file_path or not os.path.exists(file_path):
                return f"文档文件不存在或路径无效: {file_name}"
            
            # 根据文件扩展名处理不同类型的文档
            file_ext = os.path.splitext(file_name.lower())[1]
            
            if file_ext in ['.txt', '.md', '.log']:
                # 纯文本文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content[:5000]  # 限制长度，避免过长
            
            elif file_ext in ['.pdf']:
                # PDF文件（需要安装pdfplumber或类似库）
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = ""
                        for page in pdf.pages[:10]:  # 限制页数
                            text += page.extract_text() or ""
                    return text[:5000]
                except ImportError:
                    return f"PDF文档需要安装pdfplumber库才能读取: {file_name}"
                except Exception as e:
                    return f"无法读取PDF文档: {file_name}, 错误: {str(e)}"
            
            elif file_ext in ['.docx']:
                # Word文档（需要安装python-docx）
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = ""
                    for paragraph in doc.paragraphs:
                        text += paragraph.text + "\n"
                    return text[:5000]
                except ImportError:
                    return f"Word文档需要安装python-docx库才能读取: {file_name}"
                except Exception as e:
                    return f"无法读取Word文档: {file_name}, 错误: {str(e)}"
            
            else:
                return f"暂不支持的文档格式: {file_name} ({file_ext})"
                
        except Exception as e:
            return f"读取文档时发生错误: {str(e)}"
    
    def _analyze_with_openrouter_gemini(self, context_data: Dict[str, Any]) -> List[TaskItem]:
        """使用OpenRouter Gemini 2.5进行深度项目分析"""
        print("🤖 使用OpenRouter Gemini 2.5进行项目分析...")
        
        # 构建AI分析prompt
        prompt = self._build_comprehensive_analysis_prompt_with_documents(context_data)
        
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://feishu-analyzer.com",
            "X-Title": "Feishu Message Analyzer"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": """你是一个资深的项目管理专家和开发团队顾问。你的任务是分析开发团队的群聊记录，从中提取出真正的项目任务、已完成的工作和遇到的问题。

你需要：
1. 深度理解整个对话的上下文和项目背景
2. 识别出具体的开发任务、功能需求、bug修复等
3. 跟踪任务的状态变化（谁负责、是否完成、遇到什么问题）
4. 识别任务的优先级和截止时间
5. 按照团队成员组织任务分配
6. 提取技术标签和关键信息

重要：不要简单地对每条消息分类，而是要理解整个项目的任务流程和团队协作模式。"""
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1500
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            print("✅ OpenRouter Gemini 2.5分析完成")
            return self._parse_ai_analysis(ai_response, context_data)
        else:
            error_msg = f"OpenRouter API调用失败，状态码: {response.status_code}, 错误信息: {response.text}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def _build_comprehensive_analysis_prompt_with_documents(self, context_data: Dict[str, Any]) -> str:
        """构建分析prompt，专注于文本消息分析"""
        participants = context_data["participants"]
        conversation = context_data["conversation_flow"]
        
        # 构建参与者列表
        participants_text = "项目团队成员：\n"
        for p_id, p_info in participants.items():
            participants_text += f"- {p_info['name']} (ID: {p_id}, 消息数: {p_info['message_count']})\n"
        
        # 构建完整对话内容
        conversation_text = "\n## 完整群聊对话记录：\n"
        for i, msg in enumerate(conversation):
            sender_name = msg["sender"]["name"]
            content = msg["content"]
            msg_type = msg.get("type", "text")
            
            # 安全地处理时间戳转换
            try:
                timestamp = datetime.fromtimestamp(int(msg["timestamp"])).strftime("%m-%d %H:%M")
            except (ValueError, OSError, OverflowError):
                # 如果时间戳有问题，使用索引作为标识
                timestamp = f"消息{i+1}"
            
            if msg_type == "file_reference":
                conversation_text += f"[{timestamp}] {sender_name} 分享了文档: {content}\n"
            else:
                conversation_text += f"[{timestamp}] {sender_name}: {content}\n"
            
            # 如果有@提到的人，也显示出来
            if msg.get("mentions"):
                mentions = [m.get("name", m.get("id", "")) for m in msg["mentions"]]
                conversation_text += f"    (提到: {', '.join(mentions)})\n"
        
        # 时间范围 - 安全处理
        timespan = context_data["timespan"]
        try:
            start_time = datetime.fromtimestamp(int(timespan["start"])).strftime("%Y-%m-%d %H:%M:%S")
            end_time = datetime.fromtimestamp(int(timespan["end"])).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError):
            start_time = "开始时间"
            end_time = "结束时间"
        
        prompt = f"""请深度分析以下开发团队的项目群聊对话，提取出真正的任务信息并按人员组织：

## 基本信息
- 时间范围: {start_time} 至 {end_time}
- 消息总数: {context_data["total_messages"]}条
- 参与人数: {len(participants)}人

{participants_text}

{conversation_text}

## 分析要求

请从这些对话中深度挖掘并识别出：

### 1. TODO任务 (待办事项)
- 需要完成的开发任务、功能需求、修复工作等
- 被明确分配给某人的工作
- 计划中的开发内容

### 2. DONE任务 (已完成)
- 已经完成的工作、上线的功能、解决的问题等
- 完成的开发任务和里程碑
- 已交付的成果

### 3. ISSUE问题 (技术问题)
- 遇到的技术问题、bug、系统故障等
- 开发过程中的阻塞和困难
- 需要解决的技术难题

## 输出格式

请以JSON格式返回结果，包含详细的任务信息：

```json
{{
  "analysis_summary": {{
    "total_tasks_identified": 0,
    "messages_analyzed": {context_data["total_messages"]},
    "analysis_timestamp": "{datetime.now().isoformat()}"
  }},
  "tasks": [
    {{
      "id": "task_001",
      "title": "实现用户登录功能",
      "description": "需要开发用户登录页面和后端API接口，包括前端界面设计和后端认证逻辑",
      "assignee": "张三",
      "assignee_id": "ou_zhang",
      "status": "TODO",
      "priority": "HIGH",
      "tags": ["frontend", "backend", "authentication"],
      "deadline": "2025-06-05",
      "source_type": "conversation",
      "related_messages": ["msg_001", "msg_002"],
      "confidence": 0.9
    }}
  ],
  "team_summary": {{
    "total_members": {len(participants)},
    "task_distribution": {{
      "张三": {{"todo": 2, "done": 1, "issue": 0}},
      "李四": {{"todo": 1, "done": 2, "issue": 1}}
    }}
  }}
}}
```

## 分析重点

1. **任务关联性**: 识别同一个任务在不同消息中的提及
2. **人员分工**: 准确识别谁负责什么任务
3. **优先级判断**: 根据"紧急"、"重要"、"asap"等关键词判断
4. **技术分类**: 根据技术关键词进行标签分类
5. **状态跟踪**: 跟踪任务从提出到完成的状态变化

请确保提取的是真正的工作任务，而不是简单的聊天内容或讨论。重点关注项目开发相关的具体工作内容。
"""
        return prompt
    
    def _parse_ai_analysis(self, ai_response: str, context_data: Dict) -> List[TaskItem]:
        """解析AI分析结果"""
        try:
            # 提取JSON部分
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                ai_data = json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    ai_data = json.loads(json_match.group())
                else:
                    ai_data = json.loads(ai_response)
            
            tasks = []
            # 处理两种可能的格式
            if 'tasks' in ai_data:
                task_list = ai_data['tasks']
            else:
                task_list = ai_data if isinstance(ai_data, list) else []
            
            for item in task_list:
                task = TaskItem(
                    id=item.get("id", f"ai_task_{len(tasks)+1}"),
                    title=item.get("title", "未知任务"),
                    description=item.get("description", ""),
                    assignee=item.get("assignee", "未指定"),
                    priority=item.get("priority", "LOW"),
                    status=item.get("status", "TODO"),
                    tags=item.get("tags", []),
                    deadline=item.get("deadline"),
                    related_messages=item.get("related_messages", []),
                    confidence=item.get("confidence", 0.7)
                )
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            print(f"⚠️ 解析AI分析结果失败: {e}")
            # 如果解析失败，返回空列表而不是回退到规则引擎
            return []
    
    def _extract_person_name(self, sender_info: Dict) -> str:
        """提取人员姓名"""
        sender_id = sender_info.get("id", "")
        if sender_id:
            # 使用飞书用户ID映射获取真实姓名
            real_name = get_user_name_by_feishu_id(sender_id)
            if not real_name.startswith("用户") and real_name != "未知用户":
                return real_name
        
        # 如果映射失败，回退到原来的逻辑
        return sender_info.get("name", sender_info.get("id", "未知用户"))
    
    def _organize_by_person(self, tasks: List[TaskItem], original_data: Dict) -> Dict[str, Any]:
        """按人员组织任务"""
        # 按人员分组
        person_tasks = {}
        
        for task in tasks:
            assignee = task.assignee
            if assignee not in person_tasks:
                person_tasks[assignee] = {
                    "person_name": assignee,
                    "todos": [],
                    "dones": [],
                    "issues": []
                }
            
            task_dict = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "priority": task.priority,
                "tags": task.tags,
                "deadline": task.deadline,
                "related_messages": task.related_messages,
                "confidence": task.confidence
            }
            
            if task.status == "TODO":
                person_tasks[assignee]["todos"].append(task_dict)
            elif task.status == "DONE":
                person_tasks[assignee]["dones"].append(task_dict)
            elif task.status == "ISSUE":
                person_tasks[assignee]["issues"].append(task_dict)
        
        # 计算统计信息
        total_todos = sum(len(p["todos"]) for p in person_tasks.values())
        total_dones = sum(len(p["dones"]) for p in person_tasks.values())
        total_issues = sum(len(p["issues"]) for p in person_tasks.values())
        
        return {
            "success": True,
            "summary": {
                "analysis_type": "project_context_analysis",
                "original_data": {
                    "total_messages": original_data.get("total_count", 0),
                    "time_range": original_data.get("time_range", {})
                },
                "task_statistics": {
                    "total_tasks": len(tasks),
                    "total_todos": total_todos,
                    "total_dones": total_dones,
                    "total_issues": total_issues,
                    "total_assignees": len(person_tasks),
                    "high_priority_tasks": sum(1 for t in tasks if t.priority == "HIGH")
                },
                "analyzed_at": datetime.now().isoformat()
            },
            "team_tasks": person_tasks,
            "metadata": {
                "analyzer_version": "2.0.0",
                "ai_model": self.model,
                "processing_mode": "AI" if self.api_key else "Enhanced Rules"
            }
        }
    
    def _create_empty_result(self) -> Dict[str, Any]:
        """创建空结果"""
        return {
            "success": False,
            "message": "没有找到可分析的消息内容",
            "team_tasks": {},
            "summary": {
                "task_statistics": {
                    "total_tasks": 0,
                    "total_assignees": 0
                }
            }
        }
    
    def save_analysis_result(self, result: Dict[str, Any], output_file: str = None) -> str:
        """保存分析结果"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"project_analysis_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        
        print(f"📄 项目分析结果已保存到: {output_file}")
        return output_file


# 为了保持向后兼容，保留原有的类名作为别名
AIMessageProcessor = AIProjectAnalyzer 