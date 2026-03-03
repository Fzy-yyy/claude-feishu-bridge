"""
Claude Code 交互模块
通过子进程管理 Claude CLI，实现双向 JSON 流通信
"""
import asyncio
import json
import subprocess
from typing import Optional, AsyncIterator, Dict, Any, List
from pathlib import Path
from loguru import logger
from enum import Enum


class EventType(Enum):
    """事件类型"""
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    PERMISSION_REQUEST = "permission_request"
    ERROR = "error"
    SESSION_START = "session_start"
    TURN_COMPLETE = "turn_complete"


class ClaudeEvent:
    """Claude 事件"""

    def __init__(self, event_type: EventType, content: str = "", **kwargs):
        self.type = event_type
        self.content = content
        self.data = kwargs

    def __repr__(self):
        return f"ClaudeEvent(type={self.type.value}, content={self.content[:50]}...)"


class ClaudeAgent:
    """Claude Code Agent"""

    def __init__(self, work_dir: str, config: dict, security_manager):
        """
        初始化 Claude Agent

        Args:
            work_dir: 工作目录
            config: Claude 配置
            security_manager: 安全管理器
        """
        self.work_dir = work_dir
        self.config = config
        self.security = security_manager
        self.process: Optional[subprocess.Popen] = None
        self.session_id: Optional[str] = None
        self._running = False
        self._read_task: Optional[asyncio.Task] = None

        # 验证工作目录
        self.security.validate_work_dir(work_dir)

        logger.info(f"Claude Agent 初始化 - 工作目录: {work_dir}")

    async def start_session(self, session_id: Optional[str] = None) -> bool:
        """
        启动 Claude Code 会话

        Args:
            session_id: 会话 ID（用于恢复会话）

        Returns:
            bool: 是否启动成功
        """
        try:
            # 查找 claude 命令路径
            import shutil
            claude_path = shutil.which("claude")
            if not claude_path:
                logger.error("✗ Claude CLI 未找到，请确保已安装 Claude Code")
                logger.info("提示: 尝试运行 'claude --version' 检查安装")
                return False

            logger.debug(f"找到 Claude CLI: {claude_path}")

            # 构建命令参数
            args = [
                claude_path,
                "--output-format", "stream-json",
                "--verbose",
                "--input-format", "stream-json",
                "--permission-prompt-tool", "stdio",
            ]

            # 权限模式
            mode = self.config.get('permission_mode', 'default')
            if mode != 'default':
                args.extend(["--permission-mode", mode])

            # 恢复会话
            if session_id:
                args.extend(["--resume", session_id])
                self.session_id = session_id
                logger.info(f"恢复会话: {session_id}")

            # 模型
            model = self.config.get('model')
            if model:
                args.extend(["--model", model])

            # 预授权工具
            allowed_tools = self.config.get('allowed_tools', [])
            if allowed_tools:
                args.extend(["--allowedTools", ",".join(allowed_tools)])

            logger.info(f"启动 Claude Code: {' '.join(args)}")

            # 准备环境变量（移除 CLAUDECODE 以避免嵌套检测）
            import os
            env = os.environ.copy()
            if 'CLAUDECODE' in env:
                del env['CLAUDECODE']
                logger.debug("已移除 CLAUDECODE 环境变量以避免嵌套检测")

            # Windows 上设置 git-bash 路径
            if not env.get('CLAUDE_CODE_GIT_BASH_PATH'):
                # 尝试查找 bash.exe
                import shutil
                bash_exe = shutil.which('bash.exe')
                if bash_exe:
                    env['CLAUDE_CODE_GIT_BASH_PATH'] = bash_exe
                    logger.debug(f"找到 bash.exe: {bash_exe}")
                else:
                    # 尝试常见的 git-bash 路径
                    possible_bash_paths = [
                        r"C:\Program Files\Git\bin\bash.exe",
                        r"C:\Program Files\Git\usr\bin\bash.exe",
                        r"C:\Program Files (x86)\Git\bin\bash.exe",
                        r"C:\Program Files (x86)\Git\usr\bin\bash.exe",
                        r"D:\Program\Git\usr\bin\bash.exe",
                        r"D:\Program\Git\bin\bash.exe",
                        r"C:\msys64\usr\bin\bash.exe",
                        r"C:\Git\bin\bash.exe",
                    ]
                    for bash_path in possible_bash_paths:
                        if Path(bash_path).exists():
                            env['CLAUDE_CODE_GIT_BASH_PATH'] = bash_path
                            logger.debug(f"设置 git-bash 路径: {bash_path}")
                            break

            # 启动子进程
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.work_dir,
                text=True,
                bufsize=1,  # 行缓冲
                env=env,  # 使用清理后的环境变量
                encoding='utf-8',  # 强制使用 UTF-8 编码
                errors='replace',  # 遇到无法解码的字符时替换而不是报错
            )

            # 等待一小段时间检查进程是否立即退出
            await asyncio.sleep(0.5)

            if self.process.poll() is not None:
                # 进程已退出，读取错误信息
                stderr_output = self.process.stderr.read()
                logger.error(f"✗ Claude 进程启动后立即退出")
                logger.error(f"退出码: {self.process.returncode}")
                if stderr_output:
                    logger.error(f"错误信息: {stderr_output}")
                return False

            self._running = True
            logger.info("✓ Claude Code 进程已启动")

            # 启动 stderr 监控任务
            asyncio.create_task(self._monitor_stderr())

            return True

        except FileNotFoundError as e:
            logger.error(f"✗ Claude CLI 未找到: {e}")
            logger.info("请确保已安装 Claude Code 并添加到 PATH")
            return False
        except Exception as e:
            logger.error(f"✗ 启动 Claude Code 失败: {e}")
            return False

    async def send_message(self, content: str, images: List[Dict] = None) -> bool:
        """
        发送用户消息

        Args:
            content: 消息内容
            images: 图片列表（可选）

        Returns:
            bool: 是否发送成功
        """
        if not self.process or not self._running:
            logger.error("Claude Code 进程未运行")
            return False

        try:
            # 构建消息
            message = {
                "type": "user",
                "message": {
                    "role": "user",  # 必须包含 role 字段
                    "content": content
                }
            }

            # 添加图片（如果有）
            if images:
                message["message"]["images"] = images

            # 发送到 stdin
            json_str = json.dumps(message, ensure_ascii=False) + "\n"
            self.process.stdin.write(json_str)
            self.process.stdin.flush()

            logger.debug(f"→ 已发送消息: {content[:100]}...")
            return True

        except BrokenPipeError:
            logger.error("进程管道已断开")
            self._running = False
            return False
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    async def respond_permission(self, request_id: str, allow: bool,
                                 tool_input: Dict[str, Any] = None) -> bool:
        """
        响应权限请求

        Args:
            request_id: 请求 ID
            allow: 是否允许
            tool_input: 工具输入（允许时需要）

        Returns:
            bool: 是否响应成功
        """
        if not self.process or not self._running:
            return False

        try:
            # 构建权限决策
            perm_response = {}
            if allow:
                # 允许时必须包含 updatedInput，即使是空字典
                perm_response = {
                    "behavior": "allow",
                    "updatedInput": tool_input if tool_input is not None else {}
                }
            else:
                perm_response = {
                    "behavior": "deny",
                    "message": "用户拒绝了此操作"
                }

            # 构建完整的 control_response（参考 cc-connect 项目的格式）
            response = {
                "type": "control_response",
                "response": {
                    "subtype": "success",
                    "request_id": request_id,
                    "response": perm_response
                }
            }

            json_str = json.dumps(response, ensure_ascii=False) + "\n"
            logger.debug(f"发送权限响应: {json_str[:500]}")
            self.process.stdin.write(json_str)
            self.process.stdin.flush()

            logger.info(f"→ 已响应权限请求: {request_id} -> {'✓ 允许' if allow else '✗ 拒绝'}")
            return True

        except Exception as e:
            logger.error(f"响应权限失败: {e}")
            return False

    async def read_events(self) -> AsyncIterator[ClaudeEvent]:
        """
        读取 Claude 输出事件流

        Yields:
            ClaudeEvent: Claude 事件
        """
        if not self.process:
            logger.warning("read_events: 进程不存在")
            return

        logger.debug("read_events: 开始读取事件流")
        try:
            while self._running:
                # 使用 asyncio 读取行（避免阻塞）
                logger.debug("read_events: 等待读取下一行...")
                try:
                    # 添加超时机制，避免无限等待
                    line = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, self.process.stdout.readline
                        ),
                        timeout=30.0  # 30秒超时
                    )
                    logger.debug(f"read_events: 读取到行，长度: {len(line) if line else 0}")
                except asyncio.TimeoutError:
                    logger.warning("read_events: 读取超时（30秒），检查进程状态...")
                    if self.process.poll() is not None:
                        logger.error(f"Claude 进程已退出，退出码: {self.process.returncode}")
                        self._running = False
                        break
                    else:
                        logger.warning("Claude 进程仍在运行，但没有输出。可能在等待某些操作完成。")
                        # 继续等待
                        continue

                if not line:
                    # 检查进程是否退出
                    if self.process.poll() is not None:
                        logger.error(f"Claude 进程已退出，退出码: {self.process.returncode}")
                        # 读取 stderr
                        stderr_output = self.process.stderr.read()
                        if stderr_output:
                            logger.error(f"错误输出: {stderr_output}")
                        self._running = False
                    else:
                        logger.warning("Claude 进程输出流暂时无数据")
                    break

                line = line.strip()
                if not line:
                    # 跳过空行但不退出
                    logger.debug("跳过空行")
                    continue

                logger.debug(f"收到 Claude 输出: {line[:200]}...")

                try:
                    data = json.loads(line)
                    event = self._parse_event(data)
                    if event:
                        logger.debug(f"解析事件: {event.type.value}")
                        yield event

                except json.JSONDecodeError:
                    logger.debug(f"非 JSON 行: {line[:100]}")
                    continue

        except Exception as e:
            logger.error(f"读取事件流失败: {e}", exc_info=True)
            yield ClaudeEvent(EventType.ERROR, str(e))
            self._running = False

    async def _monitor_stderr(self):
        """监控 stderr 输出"""
        if not self.process or not self.process.stderr:
            return

        try:
            logger.debug("_monitor_stderr: 开始监控 stderr")
            while self._running and self.process.poll() is None:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stderr.readline
                )
                if line:
                    line = line.strip()
                    if line:
                        logger.warning(f"Claude stderr: {line}")
                await asyncio.sleep(0.1)
            logger.debug("_monitor_stderr: 监控结束")
        except Exception as e:
            logger.error(f"监控 stderr 失败: {e}")

    def _parse_event(self, data: dict) -> Optional[ClaudeEvent]:
        """
        解析事件数据

        Args:
            data: JSON 数据

        Returns:
            ClaudeEvent: 解析后的事件
        """
        event_type = data.get("type")
        logger.debug(f"解析事件类型: {event_type}, 数据: {str(data)[:200]}")

        if event_type == "system":
            # 会话初始化
            session_id = data.get("session_id")
            if session_id:
                self.session_id = session_id
                logger.info(f"会话已创建: {session_id}")
                return ClaudeEvent(EventType.SESSION_START, session_id=session_id)

        elif event_type == "assistant":
            # 助手消息
            message = data.get("message", {})
            content_arr = message.get("content", [])
            logger.debug(f"助手消息内容数组长度: {len(content_arr)}")

            for item in content_arr:
                item_type = item.get("type")
                logger.debug(f"内容项类型: {item_type}")

                if item_type == "text":
                    text = item.get("text", "")
                    if text:
                        logger.debug(f"文本内容: {text[:100]}")
                        return ClaudeEvent(EventType.TEXT, text)

                elif item_type == "thinking":
                    thinking = item.get("thinking", "")
                    if thinking:
                        return ClaudeEvent(EventType.THINKING, thinking)

                elif item_type == "tool_use":
                    tool_name = item.get("name")
                    tool_input = item.get("input", {})
                    return ClaudeEvent(
                        EventType.TOOL_USE,
                        tool_name=tool_name,
                        tool_input=tool_input
                    )

        elif event_type == "control_request":
            # 权限请求（subtype 在 request 对象内）
            request = data.get("request", {})
            subtype = request.get("subtype")
            if subtype == "can_use_tool":
                tool_input = request.get("input", {})
                return ClaudeEvent(
                    EventType.PERMISSION_REQUEST,
                    request_id=data.get("request_id"),
                    tool_name=request.get("tool_name"),
                    tool_input=tool_input,
                    input_preview=str(tool_input)[:200]
                )

        elif event_type == "result":
            # 回合完成
            result_content = data.get("result", "")
            logger.info(f"回合完成: {result_content}")
            return ClaudeEvent(EventType.TURN_COMPLETE, result_content)

        logger.debug(f"未识别的事件类型或空事件: {event_type}")
        return None

    async def stop(self):
        """停止会话"""
        self._running = False

        if self.process:
            try:
                logger.info("正在停止 Claude Code 进程...")

                # 关闭 stdin
                if self.process.stdin:
                    self.process.stdin.close()

                # 等待进程结束
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("进程未响应，强制终止")
                    self.process.kill()
                    self.process.wait()

                logger.info("✓ Claude Code 会话已停止")

            except Exception as e:
                logger.error(f"停止进程失败: {e}")
                if self.process:
                    self.process.kill()
            finally:
                self.process = None

    def is_alive(self) -> bool:
        """检查进程是否存活"""
        return self.process is not None and self.process.poll() is None
