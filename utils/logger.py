"""
日志工具模块
使用 loguru 提供统一的日志接口
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(config: dict):
    """
    配置日志系统

    Args:
        config: 日志配置字典
    """
    # 移除默认处理器
    logger.remove()

    # 获取配置
    level = config.get('level', 'INFO')
    log_file = config.get('file', 'logs/app.log')
    rotation = config.get('rotation', '100 MB')
    retention = config.get('retention', '7 days')

    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 控制台输出（带颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )

    # 文件输出
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=level,
        rotation=rotation,
        retention=retention,
        encoding='utf-8'
    )

    logger.info(f"日志系统初始化完成 - 级别: {level}, 文件: {log_file}")

    return logger
