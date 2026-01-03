"""
日志配置模块
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from config.settings import settings


def setup_logger(name: str = None) -> logging.Logger:
    """
    配置并返回一个 logger 实例

    Args:
        name: logger 名称，默认使用调用模块的名称

    Returns:
        配置好的 logger 实例
    """
    if name is None:
        name = "wechat-bot"

    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    log_filename = f"log-{datetime.now().strftime('%Y%m%d')}.txt"
    log_filepath = Path(settings.log_dir) / log_filename

    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """获取 logger 实例的快捷方法"""
    return setup_logger(name)
