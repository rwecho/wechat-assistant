"""
微信机器人主程序
监听微信群消息并发送到 n8n 处理
"""
import time
import signal
import sys
from threading import Thread
from config.settings import settings
from core.processor import MessageProcessor
from utils.logger import get_logger

logger = get_logger(__name__)


class WeChatBot:
    """微信机器人主类"""

    def __init__(self):
        """初始化机器人"""
        self.processor = MessageProcessor()
        self.running = False
        self.stats = {
            'total_processed': 0,
            'total_cycles': 0,
            'start_time': None
        }

        logger.info("=" * 60)
        logger.info("微信机器人初始化")
        logger.info(f"监听群组数量: {len(settings.get_enabled_groups())}")
        logger.info(f"轮询间隔: {settings.poll_interval} 秒")
        logger.info(f"n8n Webhook: {settings.n8n_webhook_url}")
        logger.info("=" * 60)

    def run(self):
        """运行主循环"""
        self.running = True
        self.stats['start_time'] = time.time()

        logger.info("机器人开始运行...")

        try:
            while self.running:
                self.stats['total_cycles'] += 1

                try:
                    # 处理所有群组
                    results = self.processor.process_all_groups()

                    # 统计
                    processed_count = sum(results.values())
                    self.stats['total_processed'] += processed_count

                    if processed_count > 0:
                        logger.info(f"本轮处理了 {processed_count} 条消息")

                    # 显示统计信息（每 30 轮）
                    if self.stats['total_cycles'] % 30 == 0:
                        self._print_stats()

                except KeyboardInterrupt:
                    logger.info("收到键盘中断信号")
                    break

                except Exception as e:
                    logger.error(f"处理循环出错: {e}", exc_info=True)

                # 等待下一轮
                time.sleep(settings.poll_interval)

        except KeyboardInterrupt:
            logger.info("收到退出信号")

        finally:
            self.shutdown()

    def _print_stats(self):
        """打印统计信息"""
        uptime = time.time() - self.stats['start_time']
        uptime_hours = uptime / 3600

        logger.info("=" * 60)
        logger.info("运行统计:")
        logger.info(f"  运行时间: {uptime_hours:.2f} 小时")
        logger.info(f"  轮询次数: {self.stats['total_cycles']}")
        logger.info(f"  处理消息: {self.stats['total_processed']} 条")
        logger.info(f"  平均速率: {self.stats['total_processed'] / uptime_hours * 3600:.1f} 条/小时")
        logger.info("=" * 60)

    def shutdown(self):
        """关闭机器人"""
        logger.info("正在关闭机器人...")
        self.running = False

        # 清理旧数据
        self.processor.storage_manager.cleanup_all(days=7)

        # 最终统计
        self._print_stats()

        logger.info("机器人已关闭")


def signal_handler(sig, frame):
    """信号处理函数"""
    logger.info(f"收到信号 {sig}，准备退出...")
    if bot:
        bot.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bot = None

    try:
        # 创建并启动机器人
        bot = WeChatBot()
        # 运行主循环
        bot.run()

    except Exception as e:
        logger.error(f"机器人启动失败: {e}", exc_info=True)
        sys.exit(1)
