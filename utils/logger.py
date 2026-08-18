"""
日志工具模块

统一日志配置，按级别记录到文件和控制台。
打包后日志文件位于可执行文件同级目录下的 logs/ 文件夹。
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime


def _get_log_dir() -> Path:
    """获取日志目录"""
    if getattr(sys, "frozen", False):
        _exe_dir = Path(sys.executable).resolve().parent
        return _exe_dir / "logs"
    else:
        # 开发环境: 项目根目录下的 logs/
        return Path(__file__).resolve().parent.parent / "logs"


_LOG_DIR = _get_log_dir()
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str = "ExamBroadcaster",
                 level: int = logging.DEBUG,
                 max_bytes: int = 5 * 1024 * 1024,
                 backup_count: int = 3) -> logging.Logger:
    """
    配置并返回日志记录器

    Args:
        name: 日志器名称
        level: 日志级别
        max_bytes: 单个日志文件最大字节数（默认 5MB）
        backup_count: 保留的备份文件数

    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 避免重复添加

    logger.setLevel(level)

    # 日志文件（按日期命名）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = _LOG_DIR / f"{name}_{today}.log"

    # 文件处理器（按大小轮转）
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    except Exception as e:
        # 日志文件不可写时静默降级
        print(f"[Logger] 无法创建日志文件: {e}", flush=True)

    # 控制台处理器（仅 WARNING 及以上，或 DEBUG 模式）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "ExamBroadcaster") -> logging.Logger:
    """获取已配置的日志记录器"""
    return logging.getLogger(name)


def get_log_dir() -> Path:
    """获取日志目录路径"""
    return _LOG_DIR