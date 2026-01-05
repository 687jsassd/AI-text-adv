"""
日志拓展
"""
# Copyright (c) 2025 [687jsassd]
# MIT Licens
from functools import wraps
import logging
import logging.handlers
import os
import sys


def init_global_logger():
    """
    初始化全局日志系统：
    - 日志文件路径：logs/global_error.log
    - 轮转策略：按文件大小轮转（50MB/个，保留5个备份）
    - 日志格式：包含时间、模块、函数、行号、异常堆栈等关键信息
    """
    # 1. 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. 定义日志格式（尽可能详细，方便调试）
    log_format = logging.Formatter(
        '[%(asctime)s] [%(process)d:%(thread)d] [%(levelname)s] '
        '[%(module)s:%(funcName)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. 全局日志器（root logger）
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)  # 开发环境用DEBUG，生产环境改ERROR

    # 4. 控制台输出（开发环境用，生产环境可注释）
    # console_handler = logging.StreamHandler(sys.stdout)
    # console_handler.setLevel(logging.INFO)
    # console_handler.setFormatter(log_format)
    # root_logger.addHandler(console_handler)

    # 5. 文件输出（核心：按大小轮转，避免日志文件过大）
    log_file = os.path.join(log_dir, "global_error.log")
    # 轮转配置：每个文件最大50MB，保留5个备份，编码UTF-8
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # 6. 异常捕获：记录未捕获的全局异常
    def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # 忽略Ctrl+C中断
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        # 记录未捕获的异常到日志
        root_logger.critical(
            "Uncaught global exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_uncaught_exception

    return root_logger


def log_exceptions(logger=None):
    """
    装饰器：捕获函数内的所有异常，记录到日志，并保留原有返回逻辑
    :param logger: 日志器（默认使用全局日志器）
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                # 记录异常（包含完整堆栈信息）
                logger.error(
                    "Exception in function %s",
                    func.__name__,
                    exc_info=True  # 关键：记录完整的异常堆栈
                )
                raise  # 保留原有异常抛出
        return wrapper
    return decorator
