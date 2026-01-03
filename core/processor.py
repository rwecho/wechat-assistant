"""
消息处理器
负责处理微信群消息，判断是否需要发送到 n8n
"""

import requests
from typing import Dict, Optional
from datetime import datetime
from core.wechat import WeChat
from core.storage import StorageManager
from config.settings import settings
from utils.logger import get_logger
from utils.helpers import generate_message_hash, truncate_text

logger = get_logger(__name__)


class MessageProcessor:
    """消息处理器"""

    def __init__(self):
        """初始化消息处理器"""
        self.wechat = WeChat(base_url=settings.wechat_api_base, timeout=10)
        self.storage_manager = StorageManager()
        self.n8n_webhook_url = settings.n8n_webhook_url

        logger.info("消息处理器初始化完成")

    def is_mentioned(self, text: str) -> bool:
        """
        检查消息是否提及机器人

        Args:
            text: 消息文本

        Returns:
            是否提及
        """
        return settings.mention_trigger in text

    def extract_username(self, text: str) -> str:
        """
        从消息中提取用户名

        Args:
            text: 消息文本

        Returns:
            用户名
        """
        try:
            if "：" in text:
                return text.split("：")[0].strip()
            elif ":" in text:
                return text.split(":")[0].strip()
        except:
            pass

        return "未知用户"

    def extract_message(self, text: str) -> str:
        """
        从消息中提取实际内容

        Args:
            text: 消息文本

        Returns:
            消息内容
        """
        try:
            # 移除提及标记
            message = text.replace(settings.mention_trigger, "")
            message = message.replace("：@阿祖\u2005", "")  # 特殊空格
            message = message.replace(": @阿祖", "")
            message = message.strip()
            return message
        except:
            return text

    def should_process(self, group_storage, log: Dict) -> bool:
        """
        判断是否应该处理此消息

        Args:
            group_storage: 群组存储实例
            log: 消息日志

        Returns:
            是否处理
        """
        text = log.get("title", "")

        # 检查是否提及机器人
        if not self.is_mentioned(text):
            return False

        # 检查是否已处理
        msg_hash = generate_message_hash(text, log.get("createTime", ""))

        if group_storage.is_message_processed(msg_hash):
            logger.debug(f"消息已处理，跳过: {truncate_text(text, 50)}")
            return False

        # 标记为已处理
        group_storage.mark_message_processed(msg_hash)

        return True

    def prepare_payload(
        self,
        group_config: Dict,
        log: Dict,
        username: str,
        message: str,
        group_storage=None,
    ) -> Dict:
        """
        准备发送给 n8n 的数据

        Args:
            group_config: 群组配置
            log: 消息日志
            username: 用户名
            message: 消息内容
            group_storage: 群组存储实例（可选，避免重复创建）

        Returns:
            n8n payload
        """
        group_id = group_config["id"]
        group_name = group_config.get("name", group_id)

        # 使用传入的 group_storage 或创建新的
        if group_storage is None:
            group_storage = self.storage_manager.get_store(group_id, group_name)

        # 获取对话历史（最近5条）
        recent_logs = self.wechat.get_chatlog_by_id(group_id, 10)
        chat_history = []

        for log_item in recent_logs:
            if log_item.get("title"):
                chat_history.append(
                    {
                        "user": self.extract_username(log_item["title"]),
                        "message": log_item["title"],
                        "time": log_item.get("createTime", ""),
                        "is_mention": self.is_mentioned(log_item["title"]),
                    }
                )

        # 只保留最近的对话
        chat_history = chat_history[:5]

        # 构造 payload
        payload = {
            "group_id": group_id,
            "group_name": group_name,
            "user": username,
            "message": message,
            "system_prompt": group_config.get("system_prompt", ""),
            "chat_history": chat_history,
            "timestamp": datetime.now().isoformat(),
            "message_type": "chat",
        }

        # 保存消息记录
        group_storage.save_message(
            {
                "user": username,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "direction": "incoming",
            }
        )

        return payload

    def send_to_n8n(self, payload: Dict) -> Optional[str]:
        """
        发送消息到 n8n webhook 并等待 AI 回复

        Args:
            payload: 消息数据

        Returns:
            AI 的回复内容，失败返回 None
        """
        try:
            logger.info(
                f"发送到 n8n: {payload['group_name']} - {payload['user']}: {truncate_text(payload['message'], 50)}"
            )

            response = requests.post(
                self.n8n_webhook_url,
                json=payload,
                timeout=60,  # 增加超时到 60 秒，等待 AI 处理
            )

            if response.status_code == 200:
                try:
                    # 尝试解析 n8n 返回的 JSON 响应
                    result = response.json()

                    # 尝试多种可能的响应字段名
                    ai_response = (
                        result.get("response")
                        or result.get("message")
                        or result.get("text")
                        or result.get("reply")
                        or result.get("output")
                        or result.get("answer")
                        or result.get("result")
                    )

                    if ai_response:
                        logger.info(
                            f"✅ 收到 n8n 回复: {truncate_text(ai_response, 100)}"
                        )
                        return ai_response
                    else:
                        logger.warning("⚠️  n8n 响应中没有找到回复内容")
                        logger.debug(f"n8n 响应: {result}")
                        return None

                except ValueError:
                    # 如果不是 JSON 响应，直接使用文本
                    text_response = response.text.strip()
                    if text_response:
                        logger.info(
                            f"✅ 收到 n8n 文本回复: {truncate_text(text_response, 100)}"
                        )
                        return text_response
                    else:
                        logger.warning("⚠️  n8n 返回了空响应")
                        return None
            else:
                logger.error(
                    f"❌ n8n 返回错误: {response.status_code} - {response.text}"
                )
                return None

        except requests.Timeout:
            logger.error("⏰ n8n 请求超时 (60秒)")
            return None

        except requests.ConnectionError:
            logger.error(f"🔌 无法连接到 n8n: {self.n8n_webhook_url}")
            return None

        except Exception as e:
            logger.error(f"❌ 发送到 n8n 失败: {e}", exc_info=True)
            return None

    def process_group(self, group_config: Dict) -> int:
        """
        处理单个群组的消息

        Args:
            group_config: 群组配置

        Returns:
            处理的消息数量
        """
        group_id = group_config["id"]
        group_name = group_config.get("name", group_id)

        # 检查是否启用
        if not group_config.get("enabled", True):
            return 0

        # 获取群组存储
        group_storage = self.storage_manager.get_store(group_id, group_name)

        try:
            # 获取最新消息
            logs = self.wechat.get_chatlog_by_id(group_id, 5)

            if not logs:
                logger.debug(f"群组 {group_name} 无新消息")
                return 0

            processed_count = 0

            # 倒序处理（最新的在前）
            for log in reversed(logs):
                if self.should_process(group_storage, log):
                    logger.info(
                        f"群组 {group_name} 收到消息: {truncate_text(log.get('title', ''), 100)}"
                    )

                    # 提取信息
                    username = self.extract_username(log["title"])
                    message = self.extract_message(log["title"])

                    # 准备数据（传入 group_storage 避免重复创建）
                    payload = self.prepare_payload(
                        group_config, log, username, message, group_storage
                    )

                    # 发送到 n8n 并等待 AI 回复
                    ai_response = self.send_to_n8n(payload)

                    if ai_response:
                        # 收到 AI 回复，发送到微信
                        success = self.wechat.send_message_by_id(group_id, ai_response)

                        if success:
                            logger.info(
                                f"✅ 回复已发送到 {group_name}: {truncate_text(ai_response, 50)}..."
                            )
                            processed_count += 1

                            # 保存回复记录
                            group_storage.save_message(
                                {
                                    "user": "AI",
                                    "message": ai_response,
                                    "timestamp": datetime.now().isoformat(),
                                    "direction": "outgoing",
                                }
                            )
                        else:
                            logger.error(f"❌ 回复发送失败到 {group_name}")
                    else:
                        # 没有收到 AI 回复
                        logger.warning(f"⚠️  未收到 n8n 回复，消息未处理")
                        # 取消已处理标记，允许重试
                        msg_hash = generate_message_hash(
                            log["title"], log.get("createTime", "")
                        )
                        # 从已处理列表中移除，允许下次重试
                        if msg_hash in group_storage.processed_messages:
                            del group_storage.processed_messages[msg_hash]
                            # 保存到磁盘
                            group_storage._save_processed_messages()

            return processed_count

        except Exception as e:
            logger.error(f"处理群组 {group_name} 时出错: {e}", exc_info=True)
            return 0

    def process_all_groups(self) -> Dict[str, int]:
        """
        处理所有启用的群组

        Returns:
            每个群组的处理数量
        """
        results = {}
        enabled_groups = settings.get_enabled_groups()

        logger.info(f"开始处理 {len(enabled_groups)} 个群组")

        for group_config in enabled_groups:
            group_id = group_config["id"]
            count = self.process_group(group_config)
            results[group_id] = count

        total_processed = sum(results.values())
        logger.info(f"本次轮询处理了 {total_processed} 条消息")

        return results

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            系统是否正常
        """
        # 检查微信连接
        if not self.wechat.health_check():
            logger.error("微信插件连接失败")
            return False

        # 检查 n8n 连接
        try:
            response = requests.get(self.n8n_webhook_url, timeout=5)
            # n8n webhook 可能返回 404（正常，因为只接受 POST）
            # 只要能连接就行
        except:
            logger.warning("n8n 连接检查失败")

        return True
