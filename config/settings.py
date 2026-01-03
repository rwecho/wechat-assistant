"""
配置管理模块
加载环境变量和配置文件
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Any

# 加载环境变量
load_dotenv()


class Settings:
    """全局配置类"""

    # n8n 配置
    n8n_webhook_url: str = os.getenv("N8N_WEBHOOK_URL", "https://n8n.aishuohua.art/webhook/wechat-bot")
    n8n_api_key: str = os.getenv("N8N_API_KEY", "")

    # API 服务配置
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    # 微信配置
    wechat_api_base: str = os.getenv("WECHAT_API_BASE", "http://127.0.0.1:52700/wechat-plugin/")

    # 机器人配置
    bot_name: str = os.getenv("BOT_NAME", "阿祖")
    mention_trigger: str = os.getenv("MENTION_TRIGGER", "@阿祖")
    poll_interval: int = int(os.getenv("POLL_INTERVAL", "2"))

    # 日志配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_dir: str = os.getenv("LOG_DIR", "logs")

    # 数据存储配置
    data_dir: str = os.getenv("DATA_DIR", "data")
    context_max_history: int = int(os.getenv("CONTEXT_MAX_HISTORY", "20"))
    context_ttl: int = int(os.getenv("CONTEXT_TTL", "86400"))  # 24小时

    # 项目根目录
    base_dir: Path = Path(__file__).parent.parent

    def __init__(self):
        """初始化配置，创建必要的目录"""
        self._create_directories()
        self._load_groups()

    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            self.log_dir,
            self.data_dir,
            self.data_dir + "/contexts",  # 对话上下文存储
            self.data_dir + "/processed",  # 已处理消息记录
            self.data_dir + "/states",     # 群组状态
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def _load_groups(self) -> None:
        """加载群组配置"""
        groups_file = self.base_dir / "config" / "groups.yaml"

        if not groups_file.exists():
            raise FileNotFoundError(f"群组配置文件不存在: {groups_file}")

        with open(groups_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
            self.groups: List[Dict[str, Any]] = config_data.get("groups", [])

        # 验证群组配置
        self._validate_groups()

    def _validate_groups(self) -> None:
        """验证群组配置"""
        if not self.groups:
            raise ValueError("群组配置为空，请检查 config/groups.yaml")

        group_ids = set()
        for group in self.groups:
            group_id = group.get("id")
            if not group_id:
                raise ValueError("群组配置缺少 id 字段")

            if group_id in group_ids:
                raise ValueError(f"重复的群组 ID: {group_id}")

            group_ids.add(group_id)

            # 设置默认值
            if "enabled" not in group:
                group["enabled"] = True
            if "system_prompt" not in group:
                group["system_prompt"] = "你是阿祖，一个智能助手。"
            if "schedule" not in group:
                group["schedule"] = {}

    def get_group_config(self, group_id: str) -> Dict[str, Any]:
        """获取指定群组的配置"""
        for group in self.groups:
            if group["id"] == group_id:
                return group
        return None

    def get_enabled_groups(self) -> List[Dict[str, Any]]:
        """获取所有启用的群组"""
        return [group for group in self.groups if group.get("enabled", False)]

    def get_group_data_dir(self, group_id: str) -> str:
        """
        获取群组专属的数据目录
        实现数据隔离
        """
        # 将群组 ID 中的 @ 替换为 _，避免文件名问题
        safe_group_id = group_id.replace("@", "_")
        group_dir = os.path.join(self.data_dir, "groups", safe_group_id)
        os.makedirs(group_dir, exist_ok=True)

        # 创建子目录
        subdirs = ["context", "messages", "state"]
        for subdir in subdirs:
            os.makedirs(os.path.join(group_dir, subdir), exist_ok=True)

        return group_dir


# 全局配置实例
settings = Settings()
