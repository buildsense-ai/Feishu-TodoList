#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
飞书用户ID映射工具
用于将飞书用户ID映射为真实姓名
"""

# 飞书用户ID到姓名的映射表
FEISHU_USER_ID_MAPPING = {
    'ou_5cfcf740cc1614d2b23776fd564909cc': '国伟',
    'ou_69f46927695e0456e5db3c83bea85008': 'Gauz', 
    'ou_72eca8d326aeb5da486b68558733fbfd': '云起',
    'ou_95f74ad6e567d99b8adedb1bcaf127ee': 'Michael',
    'cli_a778ea0d0278100e': '飞书机器人'  # 机器人账号
}

# 真实团队成员白名单（只有这5个人）
REAL_TEAM_MEMBERS = ['Michael', '小钟', '国伟', '云起', 'Gauz']

def get_user_name_by_feishu_id(feishu_user_id):
    """
    根据飞书用户ID获取用户姓名
    
    Args:
        feishu_user_id (str): 飞书用户ID
        
    Returns:
        str: 用户姓名，如果未找到则返回简化的ID
    """
    if feishu_user_id in FEISHU_USER_ID_MAPPING:
        return FEISHU_USER_ID_MAPPING[feishu_user_id]
    
    # 如果未找到映射，返回简化的ID（取后4位）
    if feishu_user_id and len(feishu_user_id) > 4:
        return f"用户{feishu_user_id[-4:]}"
    
    return "未知用户"

def get_all_team_members():
    """
    获取所有团队成员列表
    
    Returns:
        list: 团队成员姓名列表
    """
    return list(FEISHU_USER_ID_MAPPING.values())

def update_user_mapping(feishu_user_id, user_name):
    """
    更新用户映射关系
    
    Args:
        feishu_user_id (str): 飞书用户ID
        user_name (str): 用户姓名
    """
    FEISHU_USER_ID_MAPPING[feishu_user_id] = user_name

def replace_user_ids_in_text(text):
    """
    在文本中将飞书用户ID替换为用户姓名
    
    Args:
        text (str): 包含飞书用户ID的文本
        
    Returns:
        str: 替换后的文本
    """
    if not text:
        return text
        
    result = text
    for feishu_id, user_name in FEISHU_USER_ID_MAPPING.items():
        result = result.replace(feishu_id, user_name)
    
    return result

def get_participants_from_messages(messages):
    """
    从消息列表中提取参与者
    
    Args:
        messages (list): 消息列表
        
    Returns:
        list: 参与者姓名列表
    """
    participants = set()
    
    for msg in messages:
        sender_id = msg.get('sender', {}).get('id', '')
        if sender_id:
            user_name = get_user_name_by_feishu_id(sender_id)
            if user_name != "未知用户" and user_name != "飞书机器人":
                participants.add(user_name)
    
    return sorted(list(participants))

def get_real_team_members():
    """
    获取真实团队成员白名单
    
    Returns:
        list: 真实团队成员列表（只有5个人）
    """
    return REAL_TEAM_MEMBERS.copy()

def is_real_team_member(name):
    """
    检查是否为真实团队成员
    
    Args:
        name (str): 姓名
        
    Returns:
        bool: 是否为真实团队成员
    """
    if not name:
        return False
    
    # 处理各种可能的名称变体
    name = name.strip()
    
    # 直接匹配
    if name in REAL_TEAM_MEMBERS:
        return True
    
    # 处理常见的名称变体
    name_variants = {
        '钟悦心': '小钟',
        '小钟阿朱': '小钟', 
        '小明': '小钟',  # 可能的别名
        '王子健': None,  # 不是团队成员
    }
    
    if name in name_variants:
        return name_variants[name] is not None
    
    # 处理用户ID格式（如果还没映射）
    if name.startswith('用户'):
        return False
    
    return False

def normalize_team_member_name(name):
    """
    标准化团队成员姓名
    
    Args:
        name (str): 输入姓名
        
    Returns:
        str: 标准化后的姓名，如果不是团队成员则返回None
    """
    if not name:
        return None
    
    name = name.strip()
    
    # 直接匹配
    if name in REAL_TEAM_MEMBERS:
        return name
    
    # 处理名称变体 - 扩展映射表
    name_variants = {
        # 小钟的各种变体
        '钟悦心': '小钟',
        '小钟阿朱': '小钟',
        '小明': '小钟',
        
        # 无效人员（不是团队成员）
        '王子健': None,
        '小王': None,
        
        # 团队分类的变体 - 统一为"团队"
        '前端团队': '团队',
        '技术团队': '团队', 
        '开发团队': '团队',
        '项目团队': '团队',
    }
    
    if name in name_variants:
        return name_variants[name]
    
    # 处理以"用户"开头的ID格式 - 这些应该被过滤掉
    if name.startswith('用户'):
        return None
    
    return None

if __name__ == "__main__":
    # 测试映射功能
    print("🧪 测试飞书用户ID映射:")
    
    test_ids = [
        'ou_5cfcf740cc1614d2b23776fd564909cc',
        'ou_69f46927695e0456e5db3c83bea85008', 
        'ou_72eca8d326aeb5da486b68558733fbfd',
        'ou_95f74ad6e567d99b8adedb1bcaf127ee',
        'unknown_user_id'
    ]
    
    for user_id in test_ids:
        user_name = get_user_name_by_feishu_id(user_id)
        print(f"   {user_id} -> {user_name}")
    
    print(f"\n👥 团队成员: {get_all_team_members()}")
    
    # 测试文本替换
    test_text = "ou_5cfcf740cc1614d2b23776fd564909cc 完成了任务，ou_69f46927695e0456e5db3c83bea85008 正在review代码"
    replaced_text = replace_user_ids_in_text(test_text)
    print(f"\n📝 文本替换测试:")
    print(f"   原文: {test_text}")
    print(f"   替换后: {replaced_text}") 