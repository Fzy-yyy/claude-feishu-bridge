"""
Claude-Feishu Bridge 主程序
连接 Claude Code 和飞书，实现双向交互
"""
import asyncio
import signal
import sys
from pathlib import Path

import yaml
from loguru import logger

from core import SecurityManager, ClaudeAgent, FeishuClient, MessageRouter
from utils import setup_logger


class Application:
    """应用程序主类"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化应用程序

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = None
        self.security_manager = None
        self.claude_agent = None
        self.feishu_client = None
        self.message_router = None
        self._shutdown = False
        self._feishu_task = None  # 飞书客户端任务

    def load_config(self):
        """加载配置文件"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            logger.error(f"配置文件不存在: {self.config_path}")
            logger.info("请复制 config.yaml.example 并修改配置")
            sys.exit(1)

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        logger.info(f"✓ 配置文件加载成功: {self.config_path}")

    def initialize_components(self):
        """初始化各个组件"""
        try:
            # 初始化日志系统
            setup_logger(self.config.get('logging', {}))

            # 初始化安全管理器
            security_config = self.config.get('security', {})
            # 合并 Claude 配置中的工作目录白名单
            claude_config = self.config.get('claude', {})
            security_config['allowed_work_dirs'] = claude_config.get('allowed_work_dirs', [])

            self.security_manager = SecurityManager(security_config)

            # 初始化 Claude Agent
            work_dir = claude_config.get('work_dir', '.')
            self.claude_agent = ClaudeAgent(
                work_dir=work_dir,
                config=claude_config,
                security_manager=self.security_manager
            )

            # 初始化飞书客户端
            feishu_config = self.config.get('feishu', {})
            app_id = feishu_config.get('app_id')
            app_secret = feishu_config.get('app_secret')

            if not app_id or not app_secret:
                logger.error("飞书配置缺失，请在 config.yaml 中配置 app_id 和 app_secret")
                sys.exit(1)

            self.feishu_client = FeishuClient(app_id, app_secret)

            # 初始化消息路由器
            self.message_router = MessageRouter(
                feishu_client=self.feishu_client,
                claude_agent=self.claude_agent,
                security_manager=self.security_manager
            )

            logger.info("✓ 所有组件初始化完成")

        except Exception as e:
            logger.error(f"✗ 组件初始化失败: {e}", exc_info=True)
            sys.exit(1)

    async def start(self):
        """启动应用程序"""
        try:
            logger.info("=" * 60)
            logger.info("Claude-Feishu Bridge 启动中...")
            logger.info("=" * 60)

            # 启动 Claude Agent
            logger.info("正在启动 Claude Code 会话...")
            success = await self.claude_agent.start_session()
            if not success:
                logger.error("Claude Code 启动失败")
                logger.info("提示: 请确保已安装 Claude Code CLI (https://docs.anthropic.com/claude/docs/claude-code)")
                return

            # 启动飞书客户端（会阻塞）
            logger.info("正在启动飞书客户端...")

            # 创建飞书客户端任务
            self._feishu_task = asyncio.create_task(
                self.feishu_client.start(
                    message_handler=self.message_router.handle_feishu_message
                )
            )

            # 等待任务完成或被取消
            await self._feishu_task

        except asyncio.CancelledError:
            logger.info("任务被取消，正在关闭...")
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"运行时错误: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """关闭应用程序"""
        if self._shutdown:
            return

        self._shutdown = True
        logger.info("正在关闭应用程序...")

        # 取消飞书客户端任务
        if self._feishu_task and not self._feishu_task.done():
            self._feishu_task.cancel()
            try:
                await self._feishu_task
            except asyncio.CancelledError:
                pass

        # 停止 Claude Agent
        if self.claude_agent:
            await self.claude_agent.stop()

        # 停止飞书客户端
        if self.feishu_client:
            await self.feishu_client.stop()

        logger.info("✓ 应用程序已关闭")

    def setup_signal_handlers(self):
        """设置信号处理器"""
        loop = asyncio.get_event_loop()

        def signal_handler(sig, frame):
            logger.info(f"收到信号 {sig}，准备退出...")
            # 取消飞书任务以触发关闭流程
            if self._feishu_task and not self._feishu_task.done():
                self._feishu_task.cancel()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def main():
    """主函数"""
    # 打印欢迎信息
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           Claude-Feishu Bridge                            ║
║           连接 Claude Code 和飞书                          ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)

    # 创建应用程序实例
    app = Application()

    # 加载配置
    app.load_config()

    # 初始化组件
    app.initialize_components()

    # 启动应用程序
    try:
        # 在 Windows 上需要使用 ProactorEventLoop
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # 设置信号处理（必须在 asyncio.run 之前）
        app.setup_signal_handlers()

        asyncio.run(app.start())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("程序退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
