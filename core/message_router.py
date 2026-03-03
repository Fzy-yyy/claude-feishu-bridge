"""
消息路由器
协调飞书消息和 Claude Agent 之间的交互
"""
import asyncio
from typing import Dict, Optional
from loguru import logger
from .claude_agent import ClaudeAgent, EventType, ClaudeEvent
from .feishu_client import FeishuClient
from .security import SecurityManager


class MessageRouter:
    """消息路由器"""

    def __init__(self, feishu_client: FeishuClient,
                 claude_agent: ClaudeAgent,
                 security_manager: SecurityManager):
        """
        初始化消息路由器

        Args:
            feishu_client: 飞书客户端
            claude_agent: Claude Agent
            security_manager: 安全管理器
        """
        self.feishu = feishu_client
        self.claude = claude_agent
        self.security = security_manager

        # 当前权限请求
        self.pending_permission: Optional[Dict] = None

        # 是否正在处理消息
        self.processing = False

        # 是否启用自动批准所有权限
        self.approve_all = False

        logger.info("消息路由器初始化完成")

    async def handle_feishu_message(self, user_id: str, chat_id: str,
                                    message_id: str, content: str):
        """
        处理来自飞书的消息

        Args:
            user_id: 用户 ID
            chat_id: 聊天 ID
            message_id: 消息 ID
            content: 消息内容
        """
        try:
            content = content.strip()

            # 检查是否是权限响应
            if self.pending_permission:
                await self._handle_permission_response(message_id, content)
                return

            # 检查是否是特殊命令
            if content.startswith("/"):
                await self._handle_command(message_id, content)
                return

            # 检查是否正在处理
            if self.processing:
                await self.feishu.reply_text(
                    message_id,
                    "⏳ 上一条消息正在处理中，请稍候..."
                )
                return

            self.processing = True

            # 检查 Claude 进程是否存活
            if not self.claude.is_alive():
                logger.warning("Claude 进程未运行，正在启动...")
                success = await self.claude.start_session()
                if not success:
                    await self.feishu.reply_text(
                        message_id,
                        "❌ Claude Code 启动失败，请检查是否已安装 Claude CLI"
                    )
                    self.processing = False
                    return

            # 发送给 Claude
            logger.info(f"处理用户消息: {content[:100]}...")
            success = await self.claude.send_message(content)

            if not success:
                await self.feishu.reply_text(message_id, "❌ 发送消息失败，请重试")
                self.processing = False
                return

            # 读取 Claude 响应
            await self._process_claude_events(message_id)

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            await self.feishu.reply_text(message_id, f"❌ 处理失败: {str(e)}")
        finally:
            self.processing = False

    async def _process_claude_events(self, reply_to_message_id: str):
        """
        处理 Claude 事件流

        Args:
            reply_to_message_id: 要回复的消息 ID
        """
        response_parts = []
        last_tool_name = None

        try:
            async for event in self.claude.read_events():
                if event.type == EventType.TEXT:
                    # 收集文本响应
                    response_parts.append(event.content)

                elif event.type == EventType.THINKING:
                    # 思考过程（可选择是否显示）
                    logger.debug(f"Claude 思考: {event.content[:100]}...")
                    # 可以选择发送思考过程给用户
                    # await self.feishu.reply_text(reply_to_message_id, f"💭 {event.content}")

                elif event.type == EventType.TOOL_USE:
                    # 工具调用
                    tool_name = event.data.get("tool_name")
                    tool_input = event.data.get("tool_input", {})
                    last_tool_name = tool_name

                    logger.info(f"工具调用: {tool_name}")

                    # 显示工具调用信息
                    tool_desc = self._get_tool_description(tool_name, tool_input)
                    await self.feishu.reply_text(
                        reply_to_message_id,
                        f"🔧 {tool_desc}"
                    )

                elif event.type == EventType.PERMISSION_REQUEST:
                    # 权限请求
                    await self._handle_permission_request(reply_to_message_id, event)
                    return  # 等待用户响应

                elif event.type == EventType.TURN_COMPLETE:
                    # 回合完成
                    if response_parts:
                        full_response = "\n".join(response_parts)
                        await self.feishu.reply_text(reply_to_message_id, full_response)
                    else:
                        # 如果没有文本响应，说明可能只执行了工具
                        if last_tool_name:
                            await self.feishu.reply_text(
                                reply_to_message_id,
                                f"✅ 已完成 {last_tool_name} 操作"
                            )
                    break

                elif event.type == EventType.ERROR:
                    # 错误
                    await self.feishu.reply_text(
                        reply_to_message_id,
                        f"❌ 错误: {event.content}"
                    )
                    break

        except Exception as e:
            logger.error(f"处理事件流失败: {e}", exc_info=True)
            await self.feishu.reply_text(
                reply_to_message_id,
                f"❌ 处理事件流失败: {str(e)}"
            )

    async def _handle_permission_request(self, message_id: str, event: ClaudeEvent):
        """
        处理权限请求

        Args:
            message_id: 消息 ID
            event: 权限请求事件
        """
        request_id = event.data.get("request_id")
        tool_name = event.data.get("tool_name")
        tool_input = event.data.get("tool_input", {})
        input_preview = event.data.get("input_preview", "")

        logger.info(f"收到权限请求: {tool_name} - {input_preview[:100]}")

        # 如果启用了自动批准
        if self.approve_all:
            logger.info("自动批准模式已启用，直接允许")
            await self.claude.respond_permission(request_id, True, tool_input)
            await self._process_claude_events(message_id)
            return

        # 安全检查
        is_safe = self.security.validate_tool_call(tool_name, tool_input)

        if not is_safe:
            # 自动拒绝不安全的操作
            await self.claude.respond_permission(request_id, False)
            await self.feishu.reply_text(
                message_id,
                f"🚫 **安全检查失败**\n\n已自动拒绝操作: {tool_name}\n\n请检查操作是否符合安全策略"
            )
            self.processing = False
            return

        # 保存待处理的权限请求
        self.pending_permission = {
            "request_id": request_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "message_id": message_id
        }

        # 询问用户
        prompt = f"""🔐 **权限请求**

**工具**: `{tool_name}`
**操作**: {input_preview or '查看详细信息'}

请回复：
• `允许` 或 `allow` - 批准此操作
• `拒绝` 或 `deny` - 拒绝此操作
• `允许所有` 或 `allow all` - 本次会话自动批准所有后续请求"""

        await self.feishu.reply_text(message_id, prompt)

    async def _handle_permission_response(self, message_id: str, content: str):
        """
        处理权限响应

        Args:
            message_id: 消息 ID
            content: 用户回复内容
        """
        if not self.pending_permission:
            return

        content_lower = content.lower().strip()
        request_id = self.pending_permission["request_id"]
        tool_input = self.pending_permission["tool_input"]

        # 清除待处理请求
        self.pending_permission = None

        if content_lower in ["允许所有", "allow all", "allowall"]:
            # 启用自动批准模式
            self.approve_all = True
            await self.claude.respond_permission(request_id, True, tool_input)
            await self.feishu.reply_text(
                message_id,
                "✅ 已允许操作，并启用自动批准模式（本次会话有效）"
            )
            # 继续处理后续事件
            await self._process_claude_events(message_id)

        elif content_lower in ["允许", "allow", "y", "yes", "ok"]:
            # 允许
            await self.claude.respond_permission(request_id, True, tool_input)
            await self.feishu.reply_text(message_id, "✅ 已允许操作，正在执行...")
            # 继续处理后续事件
            logger.info("开始继续处理 Claude 事件流...")
            await self._process_claude_events(message_id)
            logger.info("Claude 事件流处理完成")

        elif content_lower in ["拒绝", "deny", "n", "no"]:
            # 拒绝
            await self.claude.respond_permission(request_id, False)
            await self.feishu.reply_text(message_id, "❌ 已拒绝操作")
            self.processing = False

        else:
            # 无效响应
            await self.feishu.reply_text(
                message_id,
                "⚠️ 无效的响应，请回复 `允许` 或 `拒绝`"
            )
            # 恢复待处理请求
            self.pending_permission = {
                "request_id": request_id,
                "tool_input": tool_input,
                "message_id": message_id
            }

    async def _handle_command(self, message_id: str, command: str):
        """
        处理特殊命令

        Args:
            message_id: 消息 ID
            command: 命令内容
        """
        cmd = command.lower().strip()

        if cmd == "/help":
            help_text = """**可用命令**

• `/help` - 显示帮助信息
• `/status` - 查看系统状态
• `/restart` - 重启 Claude 会话
• `/stop` - 停止 Claude 会话
• `/approve_all on` - 启用自动批准模式
• `/approve_all off` - 禁用自动批准模式"""
            await self.feishu.reply_text(message_id, help_text)

        elif cmd == "/status":
            is_alive = self.claude.is_alive()
            session_id = self.claude.session_id or "未创建"
            status_text = f"""**系统状态**

• Claude 进程: {'✅ 运行中' if is_alive else '❌ 未运行'}
• 会话 ID: `{session_id}`
• 工作目录: `{self.claude.work_dir}`
• 自动批准: {'✅ 已启用' if self.approve_all else '❌ 已禁用'}
• 处理中: {'是' if self.processing else '否'}"""
            await self.feishu.reply_text(message_id, status_text)

        elif cmd == "/restart":
            await self.feishu.reply_text(message_id, "🔄 正在重启 Claude 会话...")
            await self.claude.stop()
            success = await self.claude.start_session()
            if success:
                await self.feishu.reply_text(message_id, "✅ Claude 会话已重启")
            else:
                await self.feishu.reply_text(message_id, "❌ 重启失败")

        elif cmd == "/stop":
            await self.claude.stop()
            await self.feishu.reply_text(message_id, "✅ Claude 会话已停止")

        elif cmd.startswith("/approve_all"):
            parts = cmd.split()
            if len(parts) == 2:
                if parts[1] == "on":
                    self.approve_all = True
                    await self.feishu.reply_text(message_id, "✅ 自动批准模式已启用")
                elif parts[1] == "off":
                    self.approve_all = False
                    await self.feishu.reply_text(message_id, "✅ 自动批准模式已禁用")
                else:
                    await self.feishu.reply_text(message_id, "⚠️ 无效参数，使用 on 或 off")
            else:
                await self.feishu.reply_text(message_id, "⚠️ 用法: /approve_all on|off")

        else:
            await self.feishu.reply_text(message_id, "⚠️ 未知命令，输入 /help 查看帮助")

    def _get_tool_description(self, tool_name: str, tool_input: dict) -> str:
        """
        获取工具描述

        Args:
            tool_name: 工具名称
            tool_input: 工具输入

        Returns:
            str: 工具描述
        """
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            return f"正在读取文件: `{file_path}`"

        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            return f"正在写入文件: `{file_path}`"

        elif tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            return f"正在编辑文件: `{file_path}`"

        elif tool_name == "Bash":
            command = tool_input.get("command", "")
            return f"正在执行命令: `{command[:100]}`"

        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"正在搜索内容: `{pattern}`"

        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"正在搜索文件: `{pattern}`"

        else:
            return f"正在执行: {tool_name}"
