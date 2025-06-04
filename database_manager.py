"""
飞书ToDoList数据库管理模块
处理ToDoList数据的存储、查询和统计
"""

import pymysql
import json
import re
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

@dataclass
class TodoListItem:
    """ToDoList任务项数据类"""
    category: str  # ToDo, Done, Issue
    assignee: str  # 成员名称
    task_content: str  # 任务内容
    task_order: int = 0  # 排序
    priority: str = '中'  # 优先级
    estimated_hours: Optional[float] = None

@dataclass
class TodoListAnalysis:
    """ToDoList分析记录数据类"""
    analysis_date: date
    container_id: str
    time_range_start: datetime
    time_range_end: datetime
    total_messages: int
    ai_model: str = 'gemini-2.5'
    analysis_type: str = 'daily_todolist'
    raw_output: str = ''
    status: str = 'success'

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, host='localhost', port=3306, user='root', password='', database='feishu_todolist'):
        """初始化数据库连接配置"""
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'autocommit': True
        }
        self._test_connection()
    
    def _test_connection(self):
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    print(f"✅ 数据库连接成功: {self.config['database']}")
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = pymysql.connect(**self.config)
        try:
            yield conn
        finally:
            conn.close()
    
    def save_todolist_analysis(self, analysis_data: Dict) -> int:
        """
        保存ToDoList分析结果到数据库
        
        Args:
            analysis_data: 包含完整分析结果的字典
            
        Returns:
            analysis_id: 插入的分析记录ID
        """
        try:
            print("💾 开始保存ToDoList分析结果到数据库...")
            
            # 解析分析数据
            analysis_record = self._parse_analysis_data(analysis_data)
            todolist_items = self._parse_todolist_items(analysis_data)
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 1. 插入主分析记录
                    analysis_id = self._insert_analysis_record(cursor, analysis_record)
                    print(f"📊 分析记录已保存，ID: {analysis_id}")
                    
                    # 2. 批量插入任务项
                    if todolist_items:
                        item_count = self._insert_todolist_items(cursor, analysis_id, todolist_items)
                        print(f"📋 任务项已保存，数量: {item_count}")
                    
                    # 3. 保存消息统计（可选）
                    self._save_message_statistics(cursor, analysis_id, analysis_data)
                    
                    conn.commit()
                    print(f"✅ ToDoList分析结果保存完成，分析ID: {analysis_id}")
                    return analysis_id
                    
        except Exception as e:
            print(f"❌ 保存ToDoList分析结果失败: {e}")
            raise e
    
    def _parse_analysis_data(self, analysis_data: Dict) -> TodoListAnalysis:
        """解析分析数据为数据库记录格式"""
        
        # 获取时间信息
        analysis_timestamp = analysis_data.get('analysis_timestamp', datetime.now().isoformat())
        if isinstance(analysis_timestamp, str):
            analysis_timestamp = datetime.fromisoformat(analysis_timestamp.replace('Z', '+00:00'))
        
        analysis_date = analysis_timestamp.date()
        
        # 获取消息数据中的时间范围
        raw_messages_data = analysis_data.get('raw_messages_data', {})
        time_range = raw_messages_data.get('time_range', {})
        
        # 解析时间范围
        time_range_start = self._parse_time_range(time_range.get('start'))
        time_range_end = self._parse_time_range(time_range.get('end'))
        
        # 获取其他信息
        input_data = analysis_data.get('input_data', {})
        total_messages = input_data.get('message_count', 0) or raw_messages_data.get('total_count', 0)
        
        return TodoListAnalysis(
            analysis_date=analysis_date,
            container_id=raw_messages_data.get('container_id', 'unknown'),
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            total_messages=total_messages,
            ai_model=analysis_data.get('model', 'gemini-2.5'),
            analysis_type=analysis_data.get('analysis_type', 'daily_todolist'),
            raw_output=str(analysis_data.get('daily_todolist', '')),
            status=analysis_data.get('status', 'success')
        )
    
    def _parse_time_range(self, time_str) -> datetime:
        """解析时间字符串"""
        if not time_str:
            return datetime.now()
        
        try:
            # 尝试不同的时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(str(time_str), fmt)
                except ValueError:
                    continue
            
            # 如果都不匹配，尝试作为时间戳处理
            if str(time_str).isdigit():
                return datetime.fromtimestamp(float(time_str))
            
            return datetime.now()
            
        except Exception:
            return datetime.now()
    
    def _parse_todolist_items(self, analysis_data: Dict) -> List[TodoListItem]:
        """解析ToDoList项目数据"""
        items = []
        
        try:
            # 获取AI分析的ToDoList内容
            todolist_str = analysis_data.get('daily_todolist', '')
            
            # 如果是字符串，尝试解析JSON
            if isinstance(todolist_str, str):
                todolist_data = self._extract_json_from_string(todolist_str)
            else:
                todolist_data = todolist_str
            
            if not isinstance(todolist_data, dict):
                print("⚠️ 无法解析ToDoList数据")
                return items
            
            # 解析三个分类的数据
            for category in ['ToDo', 'Done', 'Issue']:
                if category in todolist_data:
                    category_data = todolist_data[category]
                    if isinstance(category_data, dict):
                        for assignee, tasks in category_data.items():
                            if isinstance(tasks, list):
                                for i, task in enumerate(tasks):
                                    if task and task.strip():  # 过滤空任务
                                        items.append(TodoListItem(
                                            category=category,
                                            assignee=assignee,
                                            task_content=task.strip(),
                                            task_order=i + 1
                                        ))
            
            print(f"📋 解析到 {len(items)} 个任务项")
            return items
            
        except Exception as e:
            print(f"⚠️ 解析ToDoList项目失败: {e}")
            return items
    
    def _extract_json_from_string(self, text: str) -> Dict:
        """从字符串中提取JSON内容"""
        try:
            # 查找JSON代码块
            if '```json' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                json_str = text[start:end]
            else:
                # 查找第一个大括号到最后一个大括号
                start = text.find('{')
                end = text.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = text[start:end]
                else:
                    return {}
            
            return json.loads(json_str)
            
        except Exception as e:
            print(f"⚠️ JSON解析失败: {e}")
            return {}
    
    def _insert_analysis_record(self, cursor, analysis: TodoListAnalysis) -> int:
        """插入分析记录"""
        sql = """
        INSERT INTO todolist_analysis 
        (analysis_date, analysis_timestamp, container_id, time_range_start, time_range_end, 
         total_messages, ai_model, analysis_type, raw_output, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        analysis_timestamp = VALUES(analysis_timestamp),
        time_range_start = VALUES(time_range_start),
        time_range_end = VALUES(time_range_end),
        total_messages = VALUES(total_messages),
        raw_output = VALUES(raw_output),
        updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(sql, (
            analysis.analysis_date,
            datetime.now(),
            analysis.container_id,
            analysis.time_range_start,
            analysis.time_range_end,
            analysis.total_messages,
            analysis.ai_model,
            analysis.analysis_type,
            analysis.raw_output,
            analysis.status
        ))
        
        # 获取插入或更新的记录ID
        cursor.execute("SELECT LAST_INSERT_ID()")
        result = cursor.fetchone()
        return result[0] if result[0] > 0 else self._get_analysis_id(cursor, analysis)
    
    def _get_analysis_id(self, cursor, analysis: TodoListAnalysis) -> int:
        """获取已存在的分析记录ID"""
        sql = "SELECT id FROM todolist_analysis WHERE container_id = %s AND analysis_date = %s"
        cursor.execute(sql, (analysis.container_id, analysis.analysis_date))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def _insert_todolist_items(self, cursor, analysis_id: int, items: List[TodoListItem]) -> int:
        """批量插入任务项"""
        # 先删除该分析ID下的所有任务项（避免重复）
        cursor.execute("DELETE FROM todolist_items WHERE analysis_id = %s", (analysis_id,))
        
        # 批量插入新任务项
        sql = """
        INSERT INTO todolist_items 
        (analysis_id, category, assignee, task_content, task_order, priority)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        values = [
            (analysis_id, item.category, item.assignee, item.task_content, item.task_order, item.priority)
            for item in items
        ]
        
        cursor.executemany(sql, values)
        return len(values)
    
    def _save_message_statistics(self, cursor, analysis_id: int, analysis_data: Dict):
        """保存消息统计信息"""
        try:
            raw_messages_data = analysis_data.get('raw_messages_data', {})
            messages = raw_messages_data.get('messages', [])
            
            if not messages:
                return
            
            # 统计消息类型
            message_stats = {}
            for msg in messages:
                msg_type = msg.get('msg_type', 'unknown')
                message_stats[msg_type] = message_stats.get(msg_type, 0) + 1
            
            # 先删除旧统计
            cursor.execute("DELETE FROM message_statistics WHERE analysis_id = %s", (analysis_id,))
            
            # 插入新统计
            sql = "INSERT INTO message_statistics (analysis_id, message_type, message_count) VALUES (%s, %s, %s)"
            values = [(analysis_id, msg_type, count) for msg_type, count in message_stats.items()]
            cursor.executemany(sql, values)
            
        except Exception as e:
            print(f"⚠️ 保存消息统计失败: {e}")
    
    def get_latest_todolist(self, container_id: str = None) -> Dict:
        """获取最新的ToDoList"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    # 构建查询条件
                    where_clause = ""
                    params = []
                    if container_id:
                        where_clause = "WHERE ta.container_id = %s"
                        params.append(container_id)
                    
                    sql = f"""
                    SELECT ta.*, ti.category, ti.assignee, ti.task_content, ti.task_order
                    FROM todolist_analysis ta
                    LEFT JOIN todolist_items ti ON ta.id = ti.analysis_id
                    {where_clause}
                    ORDER BY ta.analysis_date DESC, ti.category, ti.assignee, ti.task_order
                    LIMIT 100
                    """
                    
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    
                    if not results:
                        return {}
                    
                    # 构建ToDoList结构
                    return self._build_todolist_structure(results)
                    
        except Exception as e:
            print(f"❌ 获取最新ToDoList失败: {e}")
            return {}
    
    def _build_todolist_structure(self, db_results: List[Dict]) -> Dict:
        """构建ToDoList数据结构"""
        if not db_results:
            return {}
        
        # 获取分析信息
        analysis_info = db_results[0]
        
        # 构建ToDoList结构
        todolist = {
            "analysis_info": {
                "analysis_date": analysis_info['analysis_date'].isoformat(),
                "analysis_timestamp": analysis_info['analysis_timestamp'].isoformat(),
                "container_id": analysis_info['container_id'],
                "total_messages": analysis_info['total_messages'],
                "ai_model": analysis_info['ai_model']
            },
            "todolist": {
                "ToDo": {},
                "Done": {},
                "Issue": {}
            }
        }
        
        # 填充任务数据
        for row in db_results:
            if row['category'] and row['assignee']:
                category = row['category']
                assignee = row['assignee']
                task_content = row['task_content']
                
                if assignee not in todolist["todolist"][category]:
                    todolist["todolist"][category][assignee] = []
                
                if task_content:
                    todolist["todolist"][category][assignee].append(task_content)
        
        return todolist
    
    def get_member_workload_stats(self, days: int = 7) -> List[Dict]:
        """获取成员工作负载统计"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    sql = """
                    SELECT * FROM v_member_workload 
                    WHERE analysis_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                    ORDER BY analysis_date DESC, total_tasks DESC
                    """
                    cursor.execute(sql, (days,))
                    return cursor.fetchall()
                    
        except Exception as e:
            print(f"❌ 获取工作负载统计失败: {e}")
            return []
    
    def get_daily_summary(self, target_date: date = None) -> Dict:
        """获取指定日期的ToDoList汇总"""
        if not target_date:
            target_date = date.today()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    sql = """
                    SELECT * FROM v_daily_todolist_summary 
                    WHERE analysis_date = %s
                    ORDER BY category, assignee
                    """
                    cursor.execute(sql, (target_date,))
                    return cursor.fetchall()
                    
        except Exception as e:
            print(f"❌ 获取每日汇总失败: {e}")
            return []

# 数据库配置（可以通过环境变量或配置文件设置）
DATABASE_CONFIG = {
    'host': 'gz-cdb-e0aa423v.sql.tencentcdb.com',
    'port': 20236,
    'user': 'root',
    'password': 'Aa@114514',
    'database': 'feishu_todolist'
}

def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager(**DATABASE_CONFIG) 