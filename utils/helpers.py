"""
辅助工具函数
"""
import hashlib
import json
from typing import Any, Dict
from datetime import datetime


def generate_message_hash(content: str, timestamp: str = None) -> str:
    """
    生成消息的唯一哈希值
    用于消息去重
    注意：只使用内容生成哈希，不依赖时间戳（因为 WeChat API 返回的时间戳可能不一致）

    Args:
        content: 消息内容
        timestamp: 消息时间戳（已废弃，保留参数兼容性）

    Returns:
        MD5 哈希字符串
    """
    # 只使用消息内容，不使用时间戳
    # 因为 WeChat API 的 createTime 可能每次都不同
    data = content.strip()
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    安全地从字典中获取值

    Args:
        data: 字典数据
        key: 键名
        default: 默认值

    Returns:
        对应的值或默认值
    """
    return data.get(key, default)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 替换非法字符
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*', '@']
    safe_name = filename

    for char in illegal_chars:
        safe_name = safe_name.replace(char, '_')

    return safe_name


def format_timestamp(timestamp: str = None) -> str:
    """
    格式化时间戳

    Args:
        timestamp: ISO 格式时间戳，如果为 None 则使用当前时间

    Returns:
        格式化的时间字符串
    """
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            dt = datetime.now()
    else:
        dt = datetime.now()

    return dt.strftime('%Y-%m-%d %H:%M:%S')


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
