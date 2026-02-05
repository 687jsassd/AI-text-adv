"""
字符串替换管理器
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 字符串替换管理器
from typing import Dict, Any, Callable
from libs.practical_funcs import rule_replace


class TextReplaceManager:
    # 内部包装类(存储变量等需要实时获取值的)
    class _DynamicValue:
        def __init__(self, getter: Callable[[], Any]):
            self.getter = getter

        def __str__(self):
            return str(self.getter())

    def __init__(self, rule_dict: Dict[str, Any] = None, values_dict: Dict[str, Any] = None):
        self.rule_dict = rule_dict or {}
        self.values_dict = {}
        if values_dict:
            self.update_values_dict(values_dict)

    def replace(self, text: str) -> str:
        """
        对text文本，按照self.rule_dict中的规则进行替换（自动获取最新值）
        """
        return rule_replace(text, self.rule_dict, self.values_dict)

    def update_rule_dict(self, rule_dict: Dict[str, Any]):
        """更新替换规则字典"""
        self.rule_dict.update(rule_dict)

    def update_values_dict(self, values_dict: Dict[str, Any]):
        """
        更新变量值字典：
        - 若值是可调用对象（如lambda），自动包装为动态值；
        - 若值是普通值，直接存储（兼容原有逻辑）

        特别提示:
        若要注册动态变量，请使用lambda表达式，如：
        values_dict = {"player_name": lambda: self.player.name}
        使用values_dict = {"player_name":self.player.name}将会是值传递！

        注册少量动态变量时，建议使用register_dynamic_var方法
        """
        for key, value in values_dict.items():
            if callable(value):
                self.values_dict[key] = self._DynamicValue(value)
            else:
                self.values_dict[key] = value

    def register_dynamic_var(self, var_name: str, getter: Callable[[], Any]):
        self.values_dict[var_name] = self._DynamicValue(getter)
