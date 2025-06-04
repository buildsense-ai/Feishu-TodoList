# 飞书消息AI分析系统 - 后端API接口文档 (完整版)

## 🚀 系统概述

**版本**: v2.8.0 - 完整闭环版  
**服务地址**: `http://localhost:8000`  
**API文档**: `http://localhost:8000/docs` (FastAPI自动生成)  

### 🔥 完整工作流程
1. **会议记录处理**: 上传会议记录 → DeepSeek AI分析 → 保存数据库 → 发送到飞书群
2. **消息获取分析**: 获取飞书群消息(包含会议摘要) → 用户ID映射 → Gemini AI分析
3. **ToDoList生成**: 生成结构化任务清单 → 保存数据库 → 提供查询接口

### 核心功能
- 🔥 **会议记录AI分析**: DeepSeek AI处理会议记录，生成结构化摘要
- 📤 **自动发送飞书群**: 会议摘要自动发送到指定飞书群聊
- 📥 **智能消息获取**: 分析昨天10:30到今天10:30的飞书消息
- 👥 **智能人员识别**: 自动映射用户ID为真实姓名，只为5个团队成员分配任务
- 🤖 **双AI智能分析**: DeepSeek处理会议 + Gemini处理消息，按ToDo/Done/Issue分类
- 💾 **双数据库存储**: MySQL存储会议记录和ToDoList，支持历史查询

---

## 📝 数据模型

### 团队成员 (固定5人)
- **Michael**: 前端UI
- **小钟**: 后端数据库  
- **国伟**: 爬虫数据
- **云起**: AI语音
- **Gauz**: 架构性能

### 会议摘要格式
```json
{
  "summary": "详细的三段式会议总结",
  "participants": ["参与者列表"],
  "keywords": ["关键词列表"],
  "todos": [{"task": "任务", "assignee": "负责人", "deadline": "截止时间", "priority": "high/medium/low"}],
  "dones": [{"achievement": "完成事项", "contributor": "贡献者", "impact": "影响"}],
  "major_issues": [{"issue": "问题", "urgency": "紧急程度", "impact": "影响"}],
  "meeting_highlights": {
    "most_important_decision": "最重要决策",
    "biggest_challenge": "最大挑战"
  }
}
```

### ToDoList格式
```json
{
  "ToDo": {
    "Michael": ["任务1", "任务2"],
    "小钟": ["任务3"],
    "团队": ["共同任务"]
  },
  "Done": {
    "Michael": ["已完成任务1"],
    "国伟": ["已完成任务2"]
  },
  "Issue": {
    "云起": ["问题1"],
    "Gauz": ["问题2"]
  }
}
```

---

## 🔧 会议记录处理接口 (第一步)

### 1. 完整会议记录处理流程 ⭐️ **主要接口**

**POST** `/meeting/process-complete`

一键完成：上传会议记录文件 → AI分析 → 保存数据库 → 发送飞书群

**请求**: 文件上传 (multipart/form-data)
- `file`: 会议记录文本文件 (.txt)

**响应示例**:
```json
{
  "success": true,
  "message": "会议记录处理完成",
  "processing_steps": {
    "1_file_upload": "✅ 完成",
    "2_ai_analysis": "✅ 完成",
    "3_database_save": "✅ 完成 (ID: 123)",
    "4_feishu_send": "✅ 完成"
  },
  "data": {
    "meeting_id": 123,
    "summary": {会议摘要数据},
    "transcript_length": 5240,
    "feishu_sent": true
  },
  "next_steps": [
    "会议摘要已发送到飞书群",
    "可以调用 /daily-todolist 生成包含会议内容的ToDoList",
    "团队成员可以在飞书群中看到会议摘要"
  ]
}
```

### 2. 分析会议记录

**POST** `/meeting/analyze`

单独使用DeepSeek AI分析会议记录，不保存不发送。

**请求参数**:
```json
{
  "transcript": "会议记录文本内容..."
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "会议记录分析完成",
  "data": {
    "summary": "详细的会议总结...",
    "participants": ["Michael", "小钟", "国伟"],
    "todos": [
      {
        "task": "优化前端界面",
        "assignee": "Michael",
        "deadline": "本周五",
        "priority": "high"
      }
    ]
  },
  "processing_info": {
    "ai_provider": "DeepSeek",
    "transcript_length": 1234,
    "analysis_timestamp": "2025-06-04T14:30:00"
  }
}
```

### 3. 保存会议摘要到数据库

**POST** `/meeting/save`

将分析好的会议摘要保存到MySQL数据库。

**请求参数**:
```json
{
  "summary": {会议摘要对象},
  "transcript": "原始会议记录文本"
}
```

### 4. 发送会议摘要到飞书群

**POST** `/meeting/send-feishu`

将会议摘要发送到飞书群聊。

**请求参数**:
```json
{
  "summary": {会议摘要对象}
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "会议摘要已发送到飞书群",
  "container_id": "oc_58605a887f1e11e359ceec1782c2d12d"
}
```

---

## 🔧 ToDoList生成接口 (第二步)

### 5. 生成每日ToDoList ⭐️ **主要接口**

**POST** `/daily-todolist`

分析飞书群消息(包含会议摘要)生成ToDoList，自动获取昨天10:30到今天10:30的所有消息。

**请求参数**:
```json
{
  "container_id": "oc_58605a887f1e11e359ceec1782c2d12d",
  "download_files": false
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "今日ToDoList生成完成",
  "data": {
    "analysis_timestamp": "2025-06-04T13:42:57.723735",
    "analysis_type": "daily_todolist", 
    "model": "google/gemini-2.5-pro-preview",
    "daily_todolist": {
      "ToDo": {
        "Michael": ["前端界面优化", "用户体验测试"],
        "小钟": ["数据库性能优化", "API开发"],
        "团队": []
      },
      "Done": {
        "Michael": ["完成飞书机器人开发"],
        "国伟": ["解决验证码问题"]
      },
      "Issue": {
        "云起": ["JSON格式输出问题"],
        "Gauz": ["上下文理解问题"]
      }
    },
    "message_count": 42,
    "status": "success"
  },
  "output_file": "daily_todolist_20250604.json",
  "time_range": {
    "start": "2025-06-03 10:30:00",
    "end": "2025-06-04 10:30:00"
  },
  "total_messages": 42,
  "database_saved": true
}
```

---

## 🔍 系统监控接口

### 6. 健康检查

**GET** `/health`

检查系统状态，确认AI服务和数据库连接正常。

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-04T13:46:00.947481", 
  "ai_available": true,
  "ai_provider": "OpenRouter Gemini 2.5 + DeepSeek",
  "ai_model": "google/gemini-2.5-pro-preview",
  "version": "2.8.0",
  "features": {
    "meeting_processing": true,
    "feishu_bot_sending": true,
    "chat_messages": true,
    "ai_analysis": true,
    "daily_todolist": true,
    "database_storage": true,
    "workload_analytics": true
  }
}
```

### 7. 数据库健康检查

**GET** `/db/health`

检查ToDoList数据库连接状态。

---

## 📊 数据查询接口

### 8. 获取最新ToDoList

**GET** `/db/latest-todolist?container_id={群聊ID}`

从数据库获取最新生成的ToDoList。

### 9. 获取成员工作负载统计

**GET** `/db/member-workload?days={天数}`

统计最近N天各成员的工作负载分布。

### 10. 获取指定日期ToDoList汇总

**GET** `/db/daily-summary?target_date={日期}`

获取指定日期的ToDoList详细汇总。

---

## 📥 消息获取接口 (辅助功能)

### 11. 获取今天消息

**POST** `/fetch-today`

### 12. 获取昨天消息

**POST** `/fetch-yesterday`

### 13. 自定义时间范围获取消息

**POST** `/fetch-messages`

---

## 🤖 AI分析接口 (高级功能)

### 14. AI项目分析

**POST** `/ai-analyze`

### 15. AI分析今天讨论

**POST** `/ai-analyze-today`

---

## 🏃‍♂️ 异步任务接口

### 16. 异步获取消息

**POST** `/fetch-async`

### 17. 查询任务状态

**GET** `/task-status/{task_id}`

---

## 🔥 完整工作流程示例

### 典型使用场景

**步骤1: 处理会议记录**
```bash
# 上传会议记录文件，自动完成分析和发送
curl -X POST "http://localhost:8000/meeting/process-complete" \
  -F "file=@meeting_record.txt"
```

**步骤2: 生成ToDoList** 
```bash
# 等待几分钟让会议摘要在飞书群中生效，然后生成ToDoList
curl -X POST "http://localhost:8000/daily-todolist" \
  -H "Content-Type: application/json" \
  -d '{"container_id": "oc_58605a887f1e11e359ceec1782c2d12d", "download_files": false}'
```

**步骤3: 查看结果**
```bash
# 获取最新的ToDoList
curl "http://localhost:8000/db/latest-todolist"
```

### 前端集成建议

**主要页面结构:**

1. **Meeting Upload** - 上传会议记录，调用 `/meeting/process-complete`
2. **Dashboard** - 显示最新ToDoList，调用 `/db/latest-todolist` 
3. **Team Workload** - 团队工作负载图表，调用 `/db/member-workload`
4. **Daily Summary** - 按日期查看历史任务，调用 `/db/daily-summary`
5. **System Monitor** - 系统状态监控，调用 `/health`

**推荐工作流:**
1. 每次会议后，上传会议记录到 `/meeting/process-complete`
2. 每天上午调用 `/daily-todolist` 生成当日任务清单
3. 前端定时刷新 `/db/latest-todolist` 显示最新任务
4. 提供历史查询功能查看往期任务和统计

---

## 🎯 技术架构

### AI服务
- **DeepSeek API**: 专业会议记录分析，生成结构化摘要
- **Gemini 2.5**: 智能消息分析，生成ToDoList任务清单

### 数据库
- **meeting_summaries_db**: 存储会议记录和摘要
- **feishu_todolist**: 存储ToDoList分析结果

### 通信
- **飞书API**: 消息获取和自动发送
- **FastAPI**: 统一REST API接口

### 完整闭环
**会议记录 → DeepSeek分析 → 飞书群发送 → 消息获取 → Gemini分析 → ToDoList生成 → 数据库存储**

---

## 🎯 快速开始

1. **启动服务**: `python feishu_api_server.py`
2. **处理会议记录**: `POST /meeting/process-complete` (上传文件)
3. **生成ToDoList**: `POST /daily-todolist`
4. **查看结果**: `GET /db/latest-todolist`
5. **API文档**: 访问 `http://localhost:8000/docs`

**技术栈**: FastAPI + DeepSeek + Gemini 2.5 + 飞书API + MySQL

---

*📞 完整闭环系统，覆盖从会议记录到任务管理的全流程* 