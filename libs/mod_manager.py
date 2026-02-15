"""
MOD管理器
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from enum import Enum


class HookType(Enum):
    """
    钩子类型
    """
    PRE_SAVE = 0  # 保存前
