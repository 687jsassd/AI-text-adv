"""
游戏引擎拓展(必须)
属性系统
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from libs.practical_funcs import (COLOR_RED, COLOR_GREEN, COLOR_BLUE,
                                  COLOR_CYAN, COLOR_MAGENTA, COLOR_YELLOW, COLOR_RESET)


class Attributes:
    """
    属性类，用于存储游戏对象的属性值
    """

    def __init__(self):
        self.attributes = {
            "STR": 20.0,
            "DEX": 20.0,
            "INT": 20.0,
            "WIS": 20.0,
            "CHA": 20.0,
            "LUK": 20.0,
        }

    def in_attrs(self, attr_name: str) -> bool:
        """检查属性是否存在"""
        return attr_name in self.attributes

    def get_attr(self, attr_name: str) -> float:
        """获取指定属性值"""
        return self.attributes.get(attr_name, 0.0)

    def set_attr(self, attr_name: str, value: float):
        """设置指定属性值"""
        if attr_name in self.attributes:
            self.attributes[attr_name] = value

    def get_attribute_text(self, colorize=False):
        """获取当前属性列表的文本描述"""
        if not self.attributes:
            return "玩家当前没有属性"
        if colorize:
            ret = f"""
            当前属性
            {COLOR_RED}力量 STR:{self.attributes["STR"]}{COLOR_RESET}
            {COLOR_GREEN}敏捷 DEX:{self.attributes["DEX"]}{COLOR_RESET}
            {COLOR_BLUE}智力 INT:{self.attributes["INT"]}{COLOR_RESET}
            {COLOR_CYAN}感知 WIS:{self.attributes["WIS"]}{COLOR_RESET}
            {COLOR_MAGENTA}魅力 CHA:{self.attributes["CHA"]}{COLOR_RESET}
            {COLOR_YELLOW}幸运 LUK:{self.attributes["LUK"]}{COLOR_RESET}
            """
            return ret
        return "玩家属性：\n" + "\n".join([f"{attr}: {value}" for attr, value in self.attributes.items()])

    def to_dict(self):
        """转换为字典"""
        return {
            "attributes": self.attributes
        }

    def from_dict(self, data: dict):
        """从字典更新状态"""
        self.attributes = data.get("attributes", self.attributes)
