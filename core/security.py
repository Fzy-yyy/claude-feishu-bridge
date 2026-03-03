"""
安全控制模块
负责工作目录验证、命令过滤、路径检查等
"""
import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger


class SecurityError(Exception):
    """安全检查失败异常"""
    pass


class SecurityManager:
    """安全管理器"""

    def __init__(self, config: dict):
        """
        初始化安全管理器

        Args:
            config: 安全配置字典
        """
        self.config = config
        self.allowed_work_dirs = [
            Path(d).resolve() for d in config.get('allowed_work_dirs', [])
        ]
        self.forbidden_commands = config.get('forbidden_commands', [])
        self.forbidden_paths = config.get('forbidden_paths', [])
        self.enable_workdir_check = config.get('enable_workdir_check', True)
        self.audit_log = config.get('audit_log', True)

        logger.info(f"安全管理器初始化 - 白名单目录: {len(self.allowed_work_dirs)} 个")

    def validate_work_dir(self, work_dir: str) -> bool:
        """
        验证工作目录是否在白名单中

        Args:
            work_dir: 工作目录路径

        Returns:
            bool: 验证是否通过

        Raises:
            SecurityError: 工作目录不在白名单中
        """
        if not self.enable_workdir_check:
            logger.warning("工作目录检查已禁用")
            return True

        work_path = Path(work_dir).resolve()

        # 检查目录是否存在
        if not work_path.exists():
            logger.error(f"工作目录不存在: {work_dir}")
            raise SecurityError(f"工作目录不存在: {work_dir}")

        # 检查是否在白名单中
        for allowed_dir in self.allowed_work_dirs:
            try:
                work_path.relative_to(allowed_dir)
                logger.info(f"✓ 工作目录验证通过: {work_dir}")
                return True
            except ValueError:
                continue

        logger.error(f"✗ 工作目录不在白名单中: {work_dir}")
        raise SecurityError(
            f"工作目录 {work_dir} 不在允许的目录列表中\n"
            f"允许的目录: {[str(d) for d in self.allowed_work_dirs]}"
        )

    def check_command(self, command: str) -> bool:
        """
        检查命令是否包含危险操作

        Args:
            command: 要执行的命令

        Returns:
            bool: 检查是否通过

        Raises:
            SecurityError: 命令包含危险操作
        """
        command_lower = command.lower()

        for forbidden in self.forbidden_commands:
            if forbidden.lower() in command_lower:
                logger.warning(f"✗ 检测到危险命令: {command[:100]}")
                raise SecurityError(
                    f"命令包含禁止的操作: {forbidden}\n"
                    f"完整命令: {command[:200]}"
                )

        logger.debug(f"✓ 命令安全检查通过: {command[:100]}")
        return True

    def check_file_path(self, file_path: str) -> bool:
        """
        检查文件路径是否安全

        Args:
            file_path: 文件路径

        Returns:
            bool: 检查是否通过

        Raises:
            SecurityError: 路径不安全
        """
        try:
            path_str = str(Path(file_path).resolve())
        except Exception as e:
            logger.error(f"路径解析失败: {file_path} - {e}")
            raise SecurityError(f"无效的文件路径: {file_path}")

        for pattern in self.forbidden_paths:
            if self._match_pattern(path_str, pattern):
                logger.warning(f"✗ 检测到敏感文件访问: {file_path}")
                raise SecurityError(
                    f"禁止访问路径: {file_path}\n"
                    f"匹配规则: {pattern}"
                )

        logger.debug(f"✓ 文件路径安全检查通过: {file_path}")
        return True

    def _match_pattern(self, path: str, pattern: str) -> bool:
        """
        模式匹配（支持通配符）

        Args:
            path: 文件路径
            pattern: 匹配模式（支持 * 和 ?）

        Returns:
            bool: 是否匹配
        """
        # 将通配符转换为正则表达式
        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
        return bool(re.search(regex_pattern, path, re.IGNORECASE))

    def audit_log_operation(self, operation: str, details: Dict[str, Any]):
        """
        记录操作审计日志

        Args:
            operation: 操作类型
            details: 操作详情
        """
        if not self.audit_log:
            return

        logger.info(f"[AUDIT] {operation}", extra=details)

    def validate_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        验证工具调用的安全性

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            bool: 验证是否通过
        """
        try:
            if tool_name == "Bash":
                command = tool_input.get("command", "")
                self.check_command(command)
                self.audit_log_operation("Bash命令", {
                    "command": command[:200],
                    "tool": tool_name
                })

            elif tool_name in ["Read", "Edit", "Write"]:
                file_path = tool_input.get("file_path", "")
                self.check_file_path(file_path)
                self.audit_log_operation(f"{tool_name}文件", {
                    "path": file_path,
                    "tool": tool_name
                })

            elif tool_name == "Glob":
                pattern = tool_input.get("pattern", "")
                self.audit_log_operation("文件搜索", {
                    "pattern": pattern,
                    "tool": tool_name
                })

            elif tool_name == "Grep":
                pattern = tool_input.get("pattern", "")
                self.audit_log_operation("内容搜索", {
                    "pattern": pattern,
                    "tool": tool_name
                })

            else:
                # 其他工具默认允许
                self.audit_log_operation("工具调用", {
                    "tool": tool_name,
                    "input": str(tool_input)[:200]
                })

            return True

        except SecurityError as e:
            logger.error(f"安全检查失败: {e}")
            return False
        except Exception as e:
            logger.error(f"安全检查异常: {e}")
            return False
