"""
简单事件系统，提供观察者模式的事件驱动功能
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from typing import Callable


# 指令管理器,用于注册指令和函数，当指令触发时，调用绑定的函数
class CommandManager:
    """
    指令管理器，用于注册指令绑定到某函数，当指令触发时，调用绑定的函数，简化事件处理。
    """

    def __init__(self):
        self._cmds = {}
        self._cmd_desc = {}

    def reg(self, cmd: str, func: Callable, desc: str = "无具体描述"):
        """
        注册指令
        """
        self._cmds[cmd] = func
        self._cmd_desc[cmd] = desc

    def is_exist_func(self, cmd: str) -> bool:
        """
        判断指令是否存在
        """
        return cmd in self._cmds

    def run(self, cmd: str, *args, **kwargs):
        """
        运行指令
        """
        if self.is_exist_func(cmd):
            try:
                res = self._cmds[cmd](*args, **kwargs)
            except (FileNotFoundError, PermissionError) as e:
                print(f"文件错误: {e}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                print(f"指令 {cmd} 执行时出错：{e}")
        else:
            print("指令不存在")
            return None
        return res

    def unreg(self, cmd: str):
        """
        注销指令
        """
        if self.is_exist_func(cmd):
            del self._cmds[cmd]
        else:
            print("指令不存在")

    @property
    def cmds(self) -> tuple:
        """
        返回所有指令
        """
        return tuple(self._cmds.keys())

    def list_cmds(self):
        """
        列出所有指令
        """
        for cmd in self._cmds:
            print(f"{cmd}: {self._cmd_desc[cmd]}")


cmd_manager = CommandManager()
