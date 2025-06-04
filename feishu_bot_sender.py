#!/usr/bin/env python3
"""
Feishu Bot Sender - Send meeting summaries to Feishu chat groups
"""

import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

class FeishuBotSender:
    def __init__(self, 
                 app_id: str = "cli_a778ea0d0278100e",
                 app_secret: str = "9h4EoFmjeTPgR344VWKu8fDmnxW76Cru",
                 container_id: str = "oc_58605a887f1e11e359ceec1782c2d12d"):
        """
        Initialize Feishu Bot Sender
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            container_id: 群聊ID
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.container_id = container_id
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token = None
        self._token_expires_at = None

    def _get_tenant_access_token(self) -> Optional[str]:
        """获取租户访问令牌"""
        try:
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }
            
            response = requests.post(url, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                self._access_token = result["tenant_access_token"]
                # Token valid for 2 hours, we'll refresh every 1.5 hours
                import time
                self._token_expires_at = time.time() + 5400  # 1.5 hours
                return self._access_token
            else:
                print(f"❌ 获取访问令牌失败: {result}")
                return None
                
        except Exception as e:
            print(f"❌ 获取访问令牌异常: {e}")
            return None

    def _get_valid_token(self) -> Optional[str]:
        """获取有效的访问令牌（自动刷新）"""
        import time
        if not self._access_token or (self._token_expires_at and time.time() > self._token_expires_at):
            return self._get_tenant_access_token()
        return self._access_token

    def format_meeting_summary_as_text(self, summary_data: Dict[str, Any]) -> str:
        """Format the meeting summary as simple text message"""
        
        # Create header
        meeting_type = summary_data.get('meeting_type', 'general')
        priority_level = int(summary_data.get('priority_level', 3)) if str(summary_data.get('priority_level', 3)).isdigit() else 3
        priority_emoji = "🔥" if priority_level >= 4 else "⭐" if priority_level >= 3 else "📝"
        
        # Extract key stats
        todos_count = len(summary_data.get('todos', []))
        dones_count = len(summary_data.get('dones', []))
        issues_count = len(summary_data.get('major_issues', []))
        participants_count = len(summary_data.get('participants', []))
        
        # Build the message text
        message_lines = []
        
        # Header
        message_lines.append(f"{priority_emoji} 会议摘要 ({meeting_type})")
        message_lines.append("=" * 30)
        
        # Stats
        message_lines.append(f"📊 关键统计:")
        message_lines.append(f"👥 参与者: {participants_count}人 | 🔥 待办: {todos_count}项 | ✅ 完成: {dones_count}项 | ⚠️ 问题: {issues_count}项")
        message_lines.append("")
        
        # Main summary
        summary_text = summary_data.get('summary', '暂无会议摘要')
        message_lines.append("📋 详细摘要:")
        message_lines.append(summary_text)
        message_lines.append("")
        
        # TODOs
        if summary_data.get('todos'):
            message_lines.append("🔥 待办事项 (重点关注):")
            for i, todo in enumerate(summary_data['todos'][:5], 1):
                priority_indicator = "🔴" if todo.get('priority') == 'high' else "🟡" if todo.get('priority') == 'medium' else "🟢"
                assignee = todo.get('assignee', '未指定')
                deadline = todo.get('deadline', '待定')
                message_lines.append(f"{priority_indicator} {i}. {todo.get('task', '')}")
                message_lines.append(f"   负责人: {assignee} | 截止: {deadline}")
            message_lines.append("")
        
        # DONEs
        if summary_data.get('dones'):
            message_lines.append("✅ 已完成事项:")
            for i, done in enumerate(summary_data['dones'][:3], 1):
                contributor = done.get('contributor', '团队')
                impact = done.get('impact', '正面')
                message_lines.append(f"✅ {i}. {done.get('achievement', '')}")
                message_lines.append(f"   贡献者: {contributor} | 影响: {impact}")
            message_lines.append("")
        
        # Major Issues
        if summary_data.get('major_issues'):
            message_lines.append("⚠️ 重要问题 (需要关注):")
            for i, issue in enumerate(summary_data['major_issues'][:3], 1):
                urgency_indicator = "🚨" if issue.get('urgency') in ['high', '高'] else "⚠️" if issue.get('urgency') in ['medium', '中'] else "ℹ️"
                impact = issue.get('impact', '待评估')
                message_lines.append(f"{urgency_indicator} {i}. {issue.get('issue', '')}")
                message_lines.append(f"   影响: {impact}")
            message_lines.append("")
        
        # Meeting Highlights
        if summary_data.get('meeting_highlights'):
            highlights = summary_data['meeting_highlights']
            message_lines.append("🌟 会议亮点:")
            if highlights.get('most_important_decision'):
                message_lines.append(f"📋 重要决策: {highlights['most_important_decision']}")
            if highlights.get('biggest_challenge'):
                message_lines.append(f"🎯 最大挑战: {highlights['biggest_challenge']}")
            if highlights.get('key_breakthrough'):
                message_lines.append(f"🚀 重要突破: {highlights['key_breakthrough']}")
            if highlights.get('urgent_attention_needed'):
                message_lines.append(f"🔥 紧急关注: {highlights['urgent_attention_needed']}")
            message_lines.append("")
        
        # Participants and Keywords
        participants_text = ', '.join(summary_data.get('participants', ['暂无']))
        keywords_text = ', '.join(summary_data.get('keywords', ['暂无']))
        
        message_lines.append("👥 参与者:")
        message_lines.append(participants_text)
        message_lines.append("")
        message_lines.append("🔑 关键词:")
        message_lines.append(keywords_text)
        message_lines.append("")
        
        # Technical discussions and AI topics
        if summary_data.get('technical_discussions'):
            message_lines.append("💻 技术讨论:")
            for tech in summary_data['technical_discussions'][:2]:
                message_lines.append(f"• {tech.get('topic', '')}: {tech.get('discussion', '')[:100]}...")
            message_lines.append("")
        
        if summary_data.get('ai_related_topics'):
            message_lines.append("🤖 AI相关话题:")
            for ai_topic in summary_data['ai_related_topics'][:2]:
                message_lines.append(f"• {ai_topic.get('topic', '')}: {ai_topic.get('discussion', '')[:100]}...")
            message_lines.append("")
        
        # Footer
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_lines.append("=" * 30)
        message_lines.append(f"📅 生成时间: {current_time}")
        message_lines.append("🤖 由DeepSeek AI分析生成")
        
        return "\n".join(message_lines)

    def send_summary_to_group(self, summary_data: Dict[str, Any]) -> bool:
        """发送会议摘要到飞书群聊 (简单文本消息)"""
        
        token = self._get_valid_token()
        if not token:
            print("❌ 无法获取访问令牌")
            return False
        
        try:
            url = f"{self.base_url}/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # URL参数
            params = {
                "receive_id_type": "chat_id"
            }
            
            # Format as simple text message
            message_text = self.format_meeting_summary_as_text(summary_data)
            
            payload = {
                "receive_id": self.container_id,
                "msg_type": "text",
                "content": json.dumps({
                    "text": message_text
                }, ensure_ascii=False)
            }
            
            print("🚀 正在发送摘要到飞书群聊...")
            response = requests.post(url, headers=headers, params=params, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                print("✅ 摘要已成功发送到飞书群聊！")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False

    def test_connection(self) -> bool:
        """测试飞书连接"""
        print("🔍 测试飞书机器人连接...")
        
        token = self._get_valid_token()
        if token:
            print("✅ 飞书机器人连接成功！")
            return True
        else:
            print("❌ 飞书机器人连接失败")
            return False

    def send_simple_test_message(self) -> bool:
        """发送简单测试消息"""
        token = self._get_valid_token()
        if not token:
            print("❌ 无法获取访问令牌")
            return False
        
        try:
            url = f"{self.base_url}/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # URL参数
            params = {
                "receive_id_type": "chat_id"
            }
            
            payload = {
                "receive_id": self.container_id,
                "msg_type": "text",
                "content": json.dumps({
                    "text": "🤖 飞书机器人测试消息\n这是一条测试消息，用于验证机器人是否正常工作。"
                }, ensure_ascii=False)
            }
            
            print("🚀 正在发送测试消息到飞书群聊...")
            response = requests.post(url, headers=headers, params=params, json=payload)
            result = response.json()
            
            if result.get("code") == 0:
                print("✅ 测试消息发送成功！")
                return True
            else:
                print(f"❌ 发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送异常: {e}")
            return False

def main():
    """测试飞书机器人功能"""
    print("🤖 飞书机器人测试")
    print("=" * 40)
    
    bot = FeishuBotSender()
    
    # 测试连接
    if bot.test_connection():
        # 先测试简单消息
        print("\n🔄 测试简单文本消息...")
        if bot.send_simple_test_message():
            print("✅ 简单消息测试成功!")
            
            # 再测试复杂摘要消息
            print("\n🔄 测试会议摘要消息...")
            test_summary = {
                "summary": "这是一个测试会议摘要",
                "participants": ["测试用户1", "测试用户2"], 
                "keywords": ["测试", "机器人", "飞书"],
                "key_decisions": [
                    {"decision": "测试决策1", "owner": "测试负责人"}
                ],
                "action_items": [
                    {"task": "测试任务", "assignee": "测试人员", "priority": "high"}
                ],
                "ai_related_topics": [
                    {"topic": "飞书机器人集成", "tools_mentioned": ["DeepSeek", "Python"]}
                ]
            }
            
            success = bot.send_summary_to_group(test_summary)
            if success:
                print("🎉 完整测试成功！请检查飞书群聊")
            else:
                print("⚠️  复杂消息失败，但简单消息可用")
        else:
            print("❌ 简单消息测试失败")

if __name__ == "__main__":
    main() 