"""
微信 API 封装（修复版）
解决了原代码中的所有问题：
1. 添加了完整的异常处理
2. 添加了请求超时
3. 修复了响应检查逻辑
4. 修复了参数传递问题
5. 添加了类型注解
6. 添加了日志记录
"""

import requests
import time
from typing import List, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class WeChat:
    """微信插件 API 客户端"""

    def __init__(self, base_url: str = None, timeout: int = 10):
        """
        初始化微信客户端

        Args:
            base_url: API 基础 URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        logger.info(f"微信客户端初始化完成: {self.base_url}")

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        data: Dict = None,
        retry: int = 3,
    ) -> Optional[requests.Response]:
        """
        统一的请求方法，带重试和超时

        Args:
            method: HTTP 方法 (GET, POST)
            endpoint: API 端点
            params: URL 参数
            data: 请求体数据
            retry: 重试次数

        Returns:
            Response 对象，失败返回 None
        """
        url = self.base_url + endpoint

        for attempt in range(retry):
            try:
                logger.debug(f"请求: {method} {url}")

                if method.upper() == "GET":
                    response = self.session.get(
                        url, params=params, timeout=self.timeout
                    )
                elif method.upper() == "POST":
                    # 修复：使用正确的 Content-Type
                    headers = {"Content-Type": "application/x-www-form-urlencoded"}

                    # # 将列表参数转换为字符串
                    # processed_data = {}
                    # if data:
                    #     for key, value in data.items():
                    #         if isinstance(value, list):
                    #             # JSON 序列化列表参数
                    #             processed_data[key] = str(value)
                    #         else:
                    #             processed_data[key] = value

                    response = self.session.post(
                        url, headers=headers, data=data, timeout=self.timeout
                    )
                else:
                    logger.error(f"不支持的 HTTP 方法: {method}")
                    return None

                # 修复：检查状态码
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"请求失败，状态码: {response.status_code}")
                    return None

            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{retry})")
                if attempt < retry - 1:
                    time.sleep(1)
                else:
                    logger.error(f"请求最终超时: {url}")
                    return None

            except requests.ConnectionError:
                logger.error(f"连接失败: {url}")
                logger.error("请确保微信插件服务正在运行")
                return None

            except Exception as e:
                logger.error(f"请求异常: {e}")
                return None

        return None

    def get_users(self) -> List[Dict]:
        """
        获取所有联系人

        Returns:
            用户列表
        """
        try:
            response = self._request("GET", "user?keyword=")
            if response:
                users = response.json()
                logger.debug(f"获取到 {len(users)} 个联系人")
                return users
            return []
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []

    def search_user_by_name(self, name: str) -> List[str]:
        """
        通过名称搜索用户 ID

        Args:
            name: 用户名称

        Returns:
            匹配的用户 ID 列表
        """
        users = self.get_users()
        matched_ids = [user["userId"] for user in users if user.get("title") == name]

        logger.debug(f"搜索用户 '{name}': 找到 {len(matched_ids)} 个匹配")
        return matched_ids

    def get_chatlog_by_id(self, user_id: str, count: int = 10) -> List[Dict]:
        """
        获取指定用户的聊天记录

        Args:
            user_id: 用户 ID
            count: 获取数量

        Returns:
            聊天记录列表
        """
        try:
            # 修复：正确传递参数
            response = self._request(
                "GET",
                "chatlog",
                params={"userId": [user_id], "count": count},  # 保留为列表格式
            )

            if response:
                chatlog = response.json()
                logger.debug(f"获取到 {len(chatlog)} 条聊天记录 (user_id: {user_id})")
                return chatlog
            else:
                logger.warning(f"获取聊天记录失败: {user_id}")
                return []

        except Exception as e:
            logger.error(f"获取聊天记录异常: {e}")
            return []

    def send_message_by_id(self, user_id: str, content: str, srv_id: int = 1) -> bool:
        """
        发送消息到指定用户/群组

        Args:
            user_id: 用户 ID 或群组 ID
            content: 消息内容
            srv_id: 服务 ID

        Returns:
            是否发送成功
        """
        try:
            response = self._request(
                "POST",
                "send-message",
                data={"userId": [user_id], "content": content, "srvId": srv_id},
            )

            # 修复：检查响应对象是否存在
            if response is not None:
                logger.info(f"消息发送成功: {user_id} -> {content[:50]}...")
                return True
            else:
                logger.error(f"消息发送失败: {user_id}")
                return False

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    def send_message_by_name(self, name: str, content: str, srv_id: int = 1) -> bool:
        """
        通过用户名发送消息（先搜索 ID 再发送）

        Args:
            name: 用户名或群组名
            content: 消息内容
            srv_id: 服务 ID

        Returns:
            是否发送成功
        """
        # 搜索用户 ID
        user_ids = self.search_user_by_name(name)

        if len(user_ids) == 0:
            logger.error(f"未找到用户: {name}")
            return False

        if len(user_ids) > 1:
            logger.warning(f"找到多个同名用户 '{name}'，使用第一个: {user_ids[0]}")

        # 使用第一个匹配的 ID 发送消息
        user_id = user_ids[0]
        return self.send_message_by_id(user_id, content, srv_id)

    def health_check(self) -> bool:
        """
        健康检查

        Returns:
            服务是否正常
        """
        try:
            response = self._request("GET", "user?keyword=")
            return response is not None
        except:
            return False
