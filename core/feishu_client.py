"""
飞书客户端模块
使用 WebSocket 长连接接收消息，通过 API 发送消息
"""
import asyncio
import json
from typing import Callable, Optional
from loguru import logger

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import *
except ImportError:
    logger.error("请安装飞书 SDK: pip install lark-oapi")
    raise


class FeishuClient:
    """飞书客户端"""

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化飞书客户端

        Args:
            app_id: 飞书应用 ID
            app_secret: 飞书应用 Secret
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder() \
            .app_id(app_id) \
            .app_secret(app_secret) \
            .build()
        self.ws_client: Optional[lark.ws.Client] = None
        self.message_handler: Optional[Callable] = None

        logger.info(f"飞书客户端初始化 - App ID: {app_id[:10]}...")

    async def start(self, message_handler: Callable):
        """
        启动飞书客户端（WebSocket 长连接）

        Args:
            message_handler: 消息处理回调函数
        """
        self.message_handler = message_handler

        # 创建事件处理器
        event_handler = lark.EventDispatcherHandler.builder("", "") \
            .register_p2_im_message_receive_v1(self._on_message) \
            .build()

        # 创建 WebSocket 客户端
        self.ws_client = lark.ws.Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO
        )

        logger.info("飞书 WebSocket 客户端启动中...")

        # 在单独的线程中启动（因为 SDK 是同步的）
        await asyncio.get_event_loop().run_in_executor(
            None, self.ws_client.start
        )

    def _on_message(self, data: P2ImMessageReceiveV1) -> None:
        """
        处理接收到的消息

        Args:
            data: 飞书消息事件数据
        """
        try:
            event = data.event
            message = event.message
            sender = event.sender

            # 提取消息信息
            msg_type = message.message_type
            chat_id = message.chat_id
            message_id = message.message_id
            user_id = sender.sender_id.open_id
            user_name = sender.sender_id.user_id or "未知用户"

            logger.info(f"← 收到飞书消息 [{msg_type}] from {user_name}")

            # 解析消息内容
            if msg_type == "text":
                content_obj = json.loads(message.content)
                text = content_obj.get("text", "")

                # 调用消息处理器（异步）
                if self.message_handler:
                    asyncio.create_task(self.message_handler(
                        user_id=user_id,
                        chat_id=chat_id,
                        message_id=message_id,
                        content=text
                    ))

            elif msg_type == "image":
                logger.info(f"收到图片消息（暂不支持）: {user_id}")
                asyncio.create_task(self.reply_text(
                    message_id,
                    "暂不支持图片消息，请发送文本"
                ))

            else:
                logger.debug(f"忽略消息类型: {msg_type}")

        except Exception as e:
            logger.error(f"处理飞书消息失败: {e}", exc_info=True)

    async def reply_text(self, message_id: str, content: str) -> bool:
        """
        回复文本消息

        Args:
            message_id: 要回复的消息 ID
            content: 回复内容

        Returns:
            bool: 是否发送成功
        """
        try:
            # 判断是否需要使用卡片（包含 Markdown）
            if self._contains_markdown(content):
                return await self._reply_card(message_id, content)
            else:
                return await self._reply_plain_text(message_id, content)

        except Exception as e:
            logger.error(f"回复消息失败: {e}", exc_info=True)
            return False

    async def _reply_plain_text(self, message_id: str, text: str) -> bool:
        """
        回复纯文本

        Args:
            message_id: 消息 ID
            text: 文本内容

        Returns:
            bool: 是否成功
        """
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(ReplyMessageRequestBody.builder()
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()) \
            .build()

        # 在线程池中执行（SDK 是同步的）
        response = await asyncio.get_event_loop().run_in_executor(
            None, self.client.im.v1.message.reply, request
        )

        if not response.success():
            logger.error(f"回复失败: {response.code} - {response.msg}")
            return False

        logger.debug(f"→ 已回复消息: {text[:50]}...")
        return True

    async def _reply_card(self, message_id: str, content: str) -> bool:
        """
        回复交互式卡片（支持 Markdown）

        Args:
            message_id: 消息 ID
            content: Markdown 内容

        Returns:
            bool: 是否成功
        """
        # 适配 Markdown（飞书卡片不支持 # 标题和 > 引用）
        adapted_content = self._adapt_markdown(content)

        card = {
            "config": {"wide_screen_mode": True},
            "elements": [{
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": adapted_content
                }
            }]
        }

        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(ReplyMessageRequestBody.builder()
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()) \
            .build()

        response = await asyncio.get_event_loop().run_in_executor(
            None, self.client.im.v1.message.reply, request
        )

        if not response.success():
            logger.error(f"回复卡片失败: {response.code} - {response.msg}")
            return False

        logger.debug(f"→ 已回复卡片消息")
        return True

    def _contains_markdown(self, text: str) -> bool:
        """
        检查是否包含 Markdown 语法

        Args:
            text: 文本内容

        Returns:
            bool: 是否包含 Markdown
        """
        indicators = ["```", "**", "~~", "\n- ", "\n* ", "\n1. ", "\n# ", "---"]
        return any(ind in text for ind in indicators)

    def _adapt_markdown(self, text: str) -> str:
        """
        适配飞书 Markdown（转换不支持的语法）

        Args:
            text: 原始 Markdown 文本

        Returns:
            str: 适配后的文本
        """
        lines = text.split("\n")
        in_code_block = False

        for i, line in enumerate(lines):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # 转换标题为粗体
            for level in range(6, 0, -1):
                prefix = "#" * level + " "
                if line.startswith(prefix):
                    lines[i] = "**" + line[len(prefix):] + "**"
                    break

            # 转换引用为缩进
            if line.startswith("> "):
                lines[i] = "  " + line[2:]

        return "\n".join(lines)

    async def send_text(self, chat_id: str, content: str) -> bool:
        """
        主动发送消息到指定聊天

        Args:
            chat_id: 聊天 ID
            content: 消息内容

        Returns:
            bool: 是否成功
        """
        try:
            request = CreateMessageRequest.builder() \
                .receive_id_type("chat_id") \
                .request_body(CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(json.dumps({"text": content}, ensure_ascii=False))
                    .build()) \
                .build()

            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.im.v1.message.create, request
            )

            if not response.success():
                logger.error(f"发送消息失败: {response.code} - {response.msg}")
                return False

            logger.info(f"→ 已发送消息到 {chat_id}")
            return True

        except Exception as e:
            logger.error(f"发送消息异常: {e}")
            return False

    async def stop(self):
        """停止客户端"""
        if self.ws_client:
            try:
                logger.info("正在停止飞书 WebSocket 客户端...")

                # 调用 SDK 的私有断开连接方法
                if hasattr(self.ws_client, '_disconnect'):
                    await self.ws_client._disconnect()
                    logger.info("✓ WebSocket 连接已断开")

                # 清理客户端引用
                self.ws_client = None
                self.message_handler = None

                logger.info("✓ 飞书客户端已停止")

            except Exception as e:
                logger.error(f"停止飞书客户端时出错: {e}", exc_info=True)
                # 即使出错也要清理引用
                self.ws_client = None
                self.message_handler = None
