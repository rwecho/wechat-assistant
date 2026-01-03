"""
数据隔离存储模块
确保每个群组的数据完全独立
"""
import json
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from utils.logger import get_logger
from utils.helpers import sanitize_filename, generate_message_hash
from config.settings import settings

logger = get_logger(__name__)


class GroupStorage:
    """
    群组数据存储类
    实现数据隔离，每个群组有独立的存储空间
    """

    def __init__(self, group_id: str, group_name: str = None):
        """
        初始化群组存储

        Args:
            group_id: 群组 ID
            group_name: 群组名称（可选）
        """
        self.group_id = group_id
        self.group_name = group_name or group_id

        # 获取群组专属的数据目录
        self.data_dir = settings.get_group_data_dir(group_id)

        # 子目录路径
        self.context_dir = os.path.join(self.data_dir, "context")
        self.messages_dir = os.path.join(self.data_dir, "messages")
        self.state_dir = os.path.join(self.data_dir, "state")

        # 已处理消息记录文件
        self.processed_file = os.path.join(self.state_dir, "processed_messages.json")
        self.processed_messages = self._load_processed_messages()

        logger.info(f"群组存储初始化: {self.group_name} -> {self.data_dir}")

    def _load_processed_messages(self) -> Dict[str, float]:
        """加载已处理消息记录"""
        if os.path.exists(self.processed_file):
            try:
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 清理超过 24 小时的记录
                    cutoff = datetime.now().timestamp() - 86400
                    return {
                        msg_id: timestamp
                        for msg_id, timestamp in data.items()
                        if timestamp > cutoff
                    }
            except Exception as e:
                logger.error(f"加载已处理消息记录失败: {e}")
                return {}
        return {}

    def _save_processed_messages(self):
        """保存已处理消息记录"""
        try:
            with open(self.processed_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存已处理消息记录失败: {e}")

    def is_message_processed(self, message_hash: str) -> bool:
        """
        检查消息是否已处理

        Args:
            message_hash: 消息哈希值

        Returns:
            是否已处理
        """
        return message_hash in self.processed_messages

    def mark_message_processed(self, message_hash: str):
        """
        标记消息为已处理

        Args:
            message_hash: 消息哈希值
        """
        self.processed_messages[message_hash] = datetime.now().timestamp()
        self._save_processed_messages()

        # 定期清理（保持记录数在合理范围）
        if len(self.processed_messages) > 10000:
            self._cleanup_old_messages()

    def _cleanup_old_messages(self):
        """清理旧的消息记录"""
        cutoff = datetime.now().timestamp() - 86400  # 保留 24 小时
        self.processed_messages = {
            msg_id: timestamp
            for msg_id, timestamp in self.processed_messages.items()
            if timestamp > cutoff
        }
        self._save_processed_messages()
        logger.debug("已清理旧的消息记录")

    def save_context(self, user_id: str, context: List[Dict]):
        """
        保存对话上下文

        Args:
            user_id: 用户 ID
            context: 对话上下文列表
        """
        safe_user_id = sanitize_filename(user_id)
        context_file = os.path.join(self.context_dir, f"{safe_user_id}.json")

        try:
            # 限制历史记录数量
            max_history = settings.context_max_history
            limited_context = context[-max_history:] if len(context) > max_history else context

            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(limited_context, f, ensure_ascii=False, indent=2)

            logger.debug(f"保存上下文: {user_id} ({len(limited_context)} 条)")
        except Exception as e:
            logger.error(f"保存上下文失败: {e}")

    def load_context(self, user_id: str) -> List[Dict]:
        """
        加载对话上下文

        Args:
            user_id: 用户 ID

        Returns:
            对话上下文列表
        """
        safe_user_id = sanitize_filename(user_id)
        context_file = os.path.join(self.context_dir, f"{safe_user_id}.json")

        if not os.path.exists(context_file):
            return []

        try:
            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)

                # 检查是否过期
                file_mtime = os.path.getmtime(context_file)
                if datetime.now().timestamp() - file_mtime > settings.context_ttl:
                    logger.debug(f"上下文已过期: {user_id}")
                    return []

                logger.debug(f"加载上下文: {user_id} ({len(context)} 条)")
                return context
        except Exception as e:
            logger.error(f"加载上下文失败: {e}")
            return []

    def save_message(self, message_data: Dict):
        """
        保存消息记录

        Args:
            message_data: 消息数据
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        message_file = os.path.join(self.messages_dir, f"messages_{timestamp}.json")

        try:
            # 如果文件不存在，创建新文件
            if not os.path.exists(message_file):
                with open(message_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)

            # 读取现有消息
            with open(message_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)

            # 添加新消息
            message_data['saved_at'] = datetime.now().isoformat()
            messages.append(message_data)

            # 保存回文件
            with open(message_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存消息失败: {e}")

    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的消息记录

        Args:
            limit: 数量限制

        Returns:
            消息列表
        """
        messages = []

        try:
            # 获取最近 3 天的消息文件
            for i in range(3):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
                message_file = os.path.join(self.messages_dir, f"messages_{date}.json")

                if os.path.exists(message_file):
                    with open(message_file, 'r', encoding='utf-8') as f:
                        day_messages = json.load(f)
                        messages.extend(day_messages)

                if len(messages) >= limit:
                    break

            # 按时间排序，返回最新的
            messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return messages[:limit]

        except Exception as e:
            logger.error(f"获取最近消息失败: {e}")
            return []

    def clear_old_data(self, days: int = 7):
        """
        清理旧数据

        Args:
            days: 保留天数
        """
        cutoff = datetime.now() - timedelta(days=days)

        # 清理旧的消息文件
        for filename in os.listdir(self.messages_dir):
            if filename.startswith("messages_"):
                filepath = os.path.join(self.messages_dir, filename)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_mtime < cutoff:
                    try:
                        os.remove(filepath)
                        logger.debug(f"删除旧消息文件: {filename}")
                    except Exception as e:
                        logger.error(f"删除文件失败: {e}")

        logger.info(f"已清理 {days} 天前的数据")


class StorageManager:
    """
    存储管理器
    管理所有群组的存储实例
    """

    def __init__(self):
        """初始化存储管理器"""
        self.stores: Dict[str, GroupStorage] = {}
        logger.info("存储管理器初始化完成")

    def get_store(self, group_id: str, group_name: str = None) -> GroupStorage:
        """
        获取群组的存储实例

        Args:
            group_id: 群组 ID
            group_name: 群组名称

        Returns:
            GroupStorage 实例
        """
        if group_id not in self.stores:
            self.stores[group_id] = GroupStorage(group_id, group_name)

        return self.stores[group_id]

    def cleanup_all(self, days: int = 7):
        """
        清理所有群组的旧数据

        Args:
            days: 保留天数
        """
        for store in self.stores.values():
            store.clear_old_data(days)

        logger.info(f"已清理所有群组的旧数据（保留 {days} 天）")
