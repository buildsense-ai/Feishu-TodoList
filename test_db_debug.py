#!/usr/bin/env python3
"""
直接测试数据库查询
"""

import sys
sys.path.append('backend')

from database_manager import get_database_manager
import pymysql.cursors

def test_db_query():
    print("🔍 开始测试数据库查询...")
    
    db_manager = get_database_manager()
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                # 查询今天所有记录
                print("\n1. 查询今天所有分析记录:")
                sql = """
                SELECT id, analysis_date, analysis_timestamp, container_id, total_messages, ai_model, status
                FROM todolist_analysis 
                WHERE analysis_date = CURDATE()
                ORDER BY analysis_timestamp DESC
                """
                cursor.execute(sql)
                analysis_records = cursor.fetchall()
                
                for record in analysis_records:
                    print(f"   ID: {record['id']}, 时间: {record['analysis_timestamp']}, 消息数: {record['total_messages']}")
                
                if analysis_records:
                    latest_id = analysis_records[0]['id']
                    print(f"\n2. 查询最新记录 (ID: {latest_id}) 的任务项:")
                    
                    sql = """
                    SELECT category, assignee, task_content, task_order
                    FROM todolist_items 
                    WHERE analysis_id = %s
                    ORDER BY category, assignee, task_order
                    """
                    cursor.execute(sql, (latest_id,))
                    task_items = cursor.fetchall()
                    
                    print(f"   找到 {len(task_items)} 个任务项:")
                    for item in task_items:
                        print(f"     {item['category']} - {item['assignee']}: {item['task_content']}")
                
                print(f"\n3. 总结:")
                print(f"   今天共有 {len(analysis_records)} 条分析记录")
                if analysis_records:
                    print(f"   最新记录有 {len(task_items)} 个任务项")
                
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")

if __name__ == "__main__":
    test_db_query() 