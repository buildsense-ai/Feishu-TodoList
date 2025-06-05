import json
import os
import io
from datetime import datetime
from typing import Optional, Dict, List, Any
import lark_oapi as lark
from lark_oapi.api.im.v1 import *


class FeishuMessageFetcher:
    def __init__(self, app_id: str, app_secret: str, download_path: str = "./downloads"):
        """
        初始化飞书消息获取器
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            download_path: 文件下载路径
        """
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        self.download_path = download_path
        if not os.path.exists(download_path):
            os.makedirs(download_path)

    def get_all_messages(self, 
                        container_id: str,
                        start_time: Optional[str] = None,
                        end_time: Optional[str] = None,
                        download_files: bool = True) -> Dict[str, Any]:
        """
        获取群聊中的所有消息
        
        Args:
            container_id: 群聊ID
            start_time: 开始时间戳（秒），不指定则为今天00:00
            end_time: 结束时间戳（秒），不指定则为当前时间
            download_files: 是否下载文件和图片
            
        Returns:
            包含所有消息的字典
        """
        # 设置默认时间范围（今天）
        if not start_time or not end_time:
            now = datetime.now()
            today_start = datetime.combine(now.date(), datetime.min.time())
            start_time = start_time or str(int(today_start.timestamp()))
            end_time = end_time or str(int(now.timestamp()))

        all_messages = []
        page_token = None
        
        print(f"开始获取群聊消息，时间范围: {start_time} - {end_time}")
        
        while True:
            # 构造请求
            request_builder = ListMessageRequest.builder() \
                .container_id_type("chat") \
                .container_id(container_id) \
                .start_time(start_time) \
                .end_time(end_time) \
                .sort_type("ByCreateTimeAsc") \
                .page_size(50)
                
            if page_token:
                request_builder = request_builder.page_token(page_token)
                
            request = request_builder.build()

            # 发起请求
            response = self.client.im.v1.message.list(request)

            if not response.success():
                print(f"获取消息失败: code={response.code}, msg={response.msg}")
                break

            if not response.data or not response.data.items:
                print("没有更多消息")
                break

            # 处理当前页消息
            page_messages = self._process_messages(response.data.items, download_files)
            all_messages.extend(page_messages)
            
            print(f"已处理 {len(page_messages)} 条消息")

            # 检查是否有更多页
            if not response.data.has_more:
                break
                
            page_token = response.data.page_token

        print(f"总共获取到 {len(all_messages)} 条消息")
        
        return {
            "total_count": len(all_messages),
            "messages": all_messages,
            "time_range": {
                "start_time": start_time,
                "end_time": end_time
            }
        }

    def _process_messages(self, messages: List, download_files: bool) -> List[Dict[str, Any]]:
        """处理消息列表"""
        processed_messages = []
        
        for message in messages:
            message_data = {
                "message_id": message.message_id,
                "msg_type": message.msg_type,
                "create_time": message.create_time,
                "update_time": message.update_time,
                "sender": {
                    "id": message.sender.id if message.sender else None,
                    "sender_type": message.sender.sender_type if message.sender else None,
                    "name": self._get_sender_name(message.sender.id if message.sender else None)
                },
                "content": None,
                "files": [],
                "mentions": [],
                "reply_info": None
            }

            # 解析消息内容
            if message.body and message.body.content:
                try:
                    content = json.loads(message.body.content)
                    message_data["content"] = content
                    
                    # 根据消息类型处理
                    if message.msg_type == "text":
                        message_data["text"] = content.get("text", "")
                        
                    elif message.msg_type == "image":
                        image_key = content.get("image_key")
                        if image_key and download_files:
                            file_info = self._download_resource(
                                message.message_id, 
                                image_key, 
                                "image",
                                f"{image_key}.jpg"
                            )
                            if file_info:
                                message_data["files"].append(file_info)
                                
                    elif message.msg_type == "file":
                        file_key = content.get("file_key")
                        file_name = content.get("file_name", "unknown_file")
                        if file_key and download_files:
                            file_info = self._download_resource(
                                message.message_id,
                                file_key,
                                "file", 
                                file_name
                            )
                            if file_info:
                                message_data["files"].append(file_info)
                    
                    elif message.msg_type == "audio":
                        file_key = content.get("file_key")
                        if file_key and download_files:
                            file_info = self._download_resource(
                                message.message_id,
                                file_key,
                                "audio",
                                f"{file_key}.amr"
                            )
                            if file_info:
                                message_data["files"].append(file_info)
                    
                    elif message.msg_type == "media":
                        file_key = content.get("file_key")
                        file_name = content.get("file_name", f"{file_key}.mp4")
                        if file_key and download_files:
                            file_info = self._download_resource(
                                message.message_id,
                                file_key,
                                "media",
                                file_name
                            )
                            if file_info:
                                message_data["files"].append(file_info)
                    
                    elif message.msg_type == "rich_text":
                        # 富文本消息可能包含多种元素
                        elements = content.get("elements", [])
                        message_data["rich_text_elements"] = elements
                        
                        # 检查是否有图片或文件
                        for element in elements:
                            if element.get("tag") == "img":
                                image_key = element.get("image_key")
                                if image_key and download_files:
                                    file_info = self._download_resource(
                                        message.message_id,
                                        image_key,
                                        "image",
                                        f"{image_key}.jpg"
                                    )
                                    if file_info:
                                        message_data["files"].append(file_info)
                        
                except json.JSONDecodeError as e:
                    print(f"消息内容解析失败: {e}")
                    message_data["content"] = message.body.content
                    message_data["parse_error"] = str(e)
            
            # 处理回复信息
            if hasattr(message, 'parent_id') and message.parent_id:
                message_data["reply_info"] = {
                    "parent_id": message.parent_id
                }
            
            # 处理提及信息
            if hasattr(message, 'mentions') and message.mentions:
                message_data["mentions"] = [
                    {
                        "key": mention.key if hasattr(mention, 'key') else None,
                        "id": mention.id if hasattr(mention, 'id') else None,
                        "name": mention.name if hasattr(mention, 'name') else None
                    }
                    for mention in message.mentions
                ]

            processed_messages.append(message_data)
            
        return processed_messages

    def _get_sender_name(self, sender_id: str) -> str:
        """
        根据sender_id获取真实的用户名
        
        Args:
            sender_id: 飞书用户ID
            
        Returns:
            真实的用户名
        """
        if not sender_id:
            return "未知用户"
        
        # 导入用户映射模块
        try:
            from feishu_user_id_mapper import get_user_name_by_feishu_id
            return get_user_name_by_feishu_id(sender_id)
        except ImportError:
            # 如果导入失败，返回简化的ID
            return f"用户{sender_id[-4:]}" if len(sender_id) > 4 else "未知用户"

    def _download_resource(self, 
                         message_id: str, 
                         file_key: str, 
                         resource_type: str,
                         file_name: str) -> Optional[Dict[str, Any]]:
        """
        下载消息中的资源文件
        
        Args:
            message_id: 消息ID
            file_key: 文件key
            resource_type: 资源类型 (image, file, audio, media)
            file_name: 文件名
            
        Returns:
            文件信息字典，如果下载失败返回None
        """
        try:
            request = GetMessageResourceRequest.builder() \
                .message_id(message_id) \
                .file_key(file_key) \
                .type(resource_type) \
                .build()

            response = self.client.im.v1.message_resource.get(request)

            if not response.success():
                print(f"下载资源失败: {response.code}, {response.msg}")
                return None

            if not response.file:
                print("响应中没有文件数据")
                return None

            # 确保文件名安全
            safe_file_name = self._make_safe_filename(file_name)
            file_path = os.path.join(self.download_path, safe_file_name)
            
            # 如果文件已存在，添加时间戳
            if os.path.exists(file_path):
                name, ext = os.path.splitext(safe_file_name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_file_name = f"{name}_{timestamp}{ext}"
                file_path = os.path.join(self.download_path, safe_file_name)

            # 写入文件
            with open(file_path, "wb") as f:
                f.write(response.file.read())

            file_size = os.path.getsize(file_path)
            
            print(f"文件下载成功: {safe_file_name} ({file_size} bytes)")
            
            return {
                "file_key": file_key,
                "file_name": safe_file_name,
                "file_path": file_path,
                "file_size": file_size,
                "resource_type": resource_type,
                "download_time": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"下载资源时出错: {e}")
            return None

    def _make_safe_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全的字符
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # 限制文件名长度
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
            
        return filename

    def save_messages_to_json(self, messages_data: Dict[str, Any], output_file: str = None) -> str:
        """
        将消息数据保存为JSON文件
        
        Args:
            messages_data: 消息数据
            output_file: 输出文件路径，不指定则使用默认名称
            
        Returns:
            保存的文件路径
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"messages_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(messages_data, f, ensure_ascii=False, indent=4)
            
        print(f"消息数据已保存到: {output_file}")
        return output_file


def main():
    """示例用法"""
    # 替换为你的应用信息
    APP_ID = "YOUR_APP_ID"
    APP_SECRET = "YOUR_APP_SECRET"
    CONTAINER_ID = "YOUR_GROUP_ID"  # 群聊ID
    
    # 创建消息获取器
    fetcher = FeishuMessageFetcher(APP_ID, APP_SECRET)
    
    # 获取所有消息（包括下载文件）
    print("开始获取群聊消息...")
    messages_data = fetcher.get_all_messages(
        container_id=CONTAINER_ID,
        download_files=True  # 设置为False可以跳过文件下载
    )
    
    # 保存为JSON文件
    output_file = fetcher.save_messages_to_json(messages_data)
    
    # 打印统计信息
    print(f"\n=== 获取完成 ===")
    print(f"总消息数: {messages_data['total_count']}")
    
    # 统计各类型消息
    msg_types = {}
    total_files = 0
    for msg in messages_data['messages']:
        msg_type = msg['msg_type']
        msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
        total_files += len(msg.get('files', []))
    
    print(f"消息类型统计: {msg_types}")
    print(f"下载文件数: {total_files}")
    print(f"数据已保存到: {output_file}")


if __name__ == "__main__":
    main() 