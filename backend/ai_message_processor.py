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
    def __init__(self, api_key: str = None, model: str = "deepseek-chat", api_url: str = "https://api.deepseek.com/v1/chat/completions"):
        """
        初始化AI项目分析器
        
        Args:
            api_key: DeepSeek API密钥
            model: 使用的模型名称（DeepSeek格式）
            api_url: DeepSeek API地址
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
    
    def analyze_project_context(self, messages_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        对飞书群聊消息进行深度项目分析
        
        Args:
            messages_data: 包含消息列表的字典
            
        Returns:
            包含按人员分组的任务信息的字典
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
                raise ValueError("需要提供DeepSeek API密钥才能进行分析")
                
            analysis_result = self._analyze_with_openrouter_deepseek(context_data)
            
            # 检查AI是否直接返回了分组数据
            if isinstance(analysis_result, dict) and 'ToDo' in analysis_result:
                print("📋 使用AI直接返回的分组格式...")
                # 直接使用AI返回的分组数据
                final_result = {
                    "success": True,
                    "daily_todolist": analysis_result,  # 使用AI直接返回的格式
                    "analysis_info": {
                        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                        "analysis_timestamp": datetime.now().isoformat(),
                        "container_id": messages_data.get("container_id", "unknown"),
                        "total_messages": len(messages),
                        "ai_model": self.model
                    },
                    "message_count": len(messages),
                    "status": "success"
                }
            else:
                # 回退到原有的TaskItem处理方式
                print("📋 使用TaskItem格式处理...")
                final_result = self._organize_by_person(analysis_result, messages_data)
            
            print(f"✅ 项目分析完成")
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
    
    def _analyze_with_openrouter_deepseek(self, context_data: Dict[str, Any]) -> List[TaskItem]:
        """使用DeepSeek API进行深度项目分析"""
        print("🤖 使用DeepSeek API进行项目分析...")
        
        # 构建AI分析prompt
        prompt = self._build_comprehensive_analysis_prompt_with_documents(context_data)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": """你是一个资深的项目管理专家和开发团队顾问。你的任务是分析开发团队的群聊记录，从中提取出真正的项目任务、已完成的工作和遇到的问题。

你需要：
1. 仔细阅读每一条消息，准确理解上下文
2. 识别出明确提到的待办任务(ToDo)、已完成工作(Done)和遇到的问题(Issue)
3. 正确归属每个任务到具体的人员
4. 严格基于对话原文，不要推理或添加任何内容
5. 按照指定的JSON格式准确输出

重要：只提取对话中明确提到的内容，保持原文描述，不要概括或重写。"""
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,  # 降低温度以提高准确性
            "max_tokens": 2000
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            print("✅ DeepSeek API分析完成")
            
            # 解析AI响应，但同时保存原始分组数据
            tasks = self._parse_ai_analysis(ai_response, context_data)
            
            # 如果成功解析到分组数据，直接返回它
            if hasattr(self, '_parsed_grouped_data') and self._parsed_grouped_data:
                print("📋 使用AI直接返回的分组数据")
                return self._parsed_grouped_data  # 直接返回分组数据而不是TaskItem列表
            else:
                print("⚠️ 未能获取到分组数据，使用TaskItem格式")
                return tasks
        else:
            print(f"❌ DeepSeek API调用失败: {response.status_code} - {response.text}")
            raise Exception(f"API调用失败: {response.status_code}")
    
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
        
        # 构建团队成员列表用于JSON格式
        member_names = [p_info['name'] for p_info in participants.values()]
        
        prompt = f"""请深度分析以下开发团队的项目群聊对话，提取出真正的任务信息并按人员组织：

## 基本信息
- 时间范围: {start_time} 至 {end_time}
- 消息总数: {context_data["total_messages"]}条
- 参与人数: {len(participants)}人

{participants_text}

{conversation_text}

## 分析任务

请从对话中准确识别以下三类信息：

### 1. ToDo (待办任务)
- 明确提到需要完成的工作、开发任务、功能需求
- 被分配给特定人员的任务
- 计划要做的事情
- 关键词：需要、要做、负责、开发、实现、完成、设计等

### 2. Done (已完成)
- 明确提到已经完成的工作、解决的问题
- 已经交付的功能、修复的bug
- 取得的进展和成果
- 关键词：完成了、已经、搞定、解决了、上线了、修复了等

### 3. Issue (遇到的问题)
- 遇到的技术问题、困难、阻塞
- 需要解决的bug、故障
- 开发过程中的挑战
- 关键词：问题、bug、出错、异常、困难、阻塞等

## 重要原则

1. **严格基于原文**：只提取对话中明确提到的内容，不要推理或添加
2. **准确归属**：确保任务分配给正确的人员
3. **分类准确**：区分清楚待办、已完成和问题
4. **内容具体**：保留任务的具体描述，不要过度概括

## 输出格式

请严格按照以下JSON格式输出，确保所有团队成员都包含在内：

```json
{{
  "ToDo": {{
    {', '.join([f'"{name}": []' for name in member_names])}
  }},
  "Done": {{
    {', '.join([f'"{name}": []' for name in member_names])}
  }},
  "Issue": {{
    {', '.join([f'"{name}": []' for name in member_names])}
  }}
}}
```

每个人员的任务数组应该包含具体的任务描述字符串。如果对话中没有明确的任务，对应数组保持为空。

## 示例输出格式

```json
{{
  "ToDo": {{
    "张三": ["完成用户登录功能", "修复数据库连接问题"],
    "李四": ["设计前端界面", "准备项目文档"],
    "王五": []
  }},
  "Done": {{
    "张三": ["完成了API接口开发"],
    "李四": ["上线了用户注册功能"],
    "王五": []
  }},
  "Issue": {{
    "张三": ["数据库连接超时问题"],
    "李四": [],
    "王五": ["前端打包出现错误"]
  }}
}}
```

请仔细分析对话内容，准确提取并分类任务信息。
"""
        return prompt
    
    def _parse_ai_analysis(self, ai_response: str, context_data: Dict) -> List[TaskItem]:
        """解析AI分析结果 - 现在AI直接返回分组格式"""
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
            
            # 现在AI直接返回分组格式，我们需要存储这个格式而不是转换为TaskItem列表
            # 直接返回原始分组数据，后续处理会使用这个格式
            self._parsed_grouped_data = ai_data
            
            # 为了兼容现有代码流程，仍然生成TaskItem列表
            tasks = []
            task_id = 1
            
            # 处理ToDo任务
            if 'ToDo' in ai_data:
                for person, task_list in ai_data['ToDo'].items():
                    for task_desc in task_list:
                        task = TaskItem(
                            id=f"todo_{task_id}",
                            title=task_desc,
                            description=task_desc,
                            assignee=person,
                            priority="MEDIUM",
                            status="TODO",
                            tags=[],
                            deadline=None,
                            related_messages=[],
                            confidence=0.8
                        )
                        tasks.append(task)
                        task_id += 1
            
            # 处理Done任务
            if 'Done' in ai_data:
                for person, task_list in ai_data['Done'].items():
                    for task_desc in task_list:
                        task = TaskItem(
                            id=f"done_{task_id}",
                            title=task_desc,
                            description=task_desc,
                            assignee=person,
                            priority="MEDIUM",
                            status="DONE",
                            tags=[],
                            deadline=None,
                            related_messages=[],
                            confidence=0.8
                        )
                        tasks.append(task)
                        task_id += 1
            
            # 处理Issue问题
            if 'Issue' in ai_data:
                for person, task_list in ai_data['Issue'].items():
                    for task_desc in task_list:
                        task = TaskItem(
                            id=f"issue_{task_id}",
                            title=task_desc,
                            description=task_desc,
                            assignee=person,
                            priority="HIGH",
                            status="ISSUE",
                            tags=[],
                            deadline=None,
                            related_messages=[],
                            confidence=0.8
                        )
                        tasks.append(task)
                        task_id += 1
            
            return tasks
            
        except Exception as e:
            print(f"⚠️ 解析AI分析结果失败: {e}")
            print(f"⚠️ AI响应内容: {ai_response[:500]}...")
            # 如果解析失败，返回空列表
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