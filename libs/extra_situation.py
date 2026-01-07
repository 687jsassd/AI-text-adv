"""
游戏引擎拓展(必须)
形势系统
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from libs.practical_funcs import COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_RESET


class Situation:
    """
    形势
    """

    def __init__(self):
        self.situation = 0
        self.situation_text = {
            (-99999, -10): "形势对你极其不利",
            (-10, -7): "形势对你非常不利",
            (-7, -4): "形势对你明显不利",
            (-4, -1): "形势对你略显不利",
            (-1, 1): "均势",
            (1, 4): "形势对你略有利",
            (4, 7): "形势对你明显有利",
            (7, 10): "形势对你非常有利",
            (10, 99999): "形势对你极其有利",
        }

    def get_situation_text(self, add_numbers=False, colorize=False):
        """获取当前形势的文本描述"""
        if self.situation > 10:
            self.situation = 10
        if self.situation < -10:
            self.situation = -10
        for tp, texts in self.situation_text.items():
            if tp[0] <= self.situation < tp[1]:
                ret_text = f"{texts}"
                if add_numbers:
                    ret_text = f"当前的形势值:{self.situation} ({texts})"
                if colorize:
                    if self.situation < -4:
                        ret_text = COLOR_RED + ret_text + COLOR_RESET
                    elif self.situation < -1:
                        ret_text = COLOR_YELLOW + ret_text + COLOR_RESET
                    elif self.situation < 1:
                        pass
                    elif self.situation < 4:
                        ret_text = COLOR_GREEN + ret_text + COLOR_RESET
                    else:
                        ret_text = COLOR_BLUE + ret_text + COLOR_RESET
                return ret_text

    def to_dict(self):
        """转换为字典"""
        # 把元组键转为字符串（如 (-99999, -10) → "-99999,-10"）
        situation_text_str_keys = {}
        for tuple_key, text in self.situation_text.items():
            # 元组转逗号分隔的字符串
            str_key = f"{tuple_key[0]},{tuple_key[1]}"
            situation_text_str_keys[str_key] = text

        return {
            "situation": self.situation,
            "situation_text": situation_text_str_keys,  # 用字符串键的字典
        }

    def from_dict(self, data: dict):
        """从字典更新状态"""
        self.situation = data.get("situation", self.situation)

        # 处理situation_text：字符串键还原为元组
        text_data = data.get("situation_text", {})
        restored_text = {}
        for str_key, text in text_data.items():
            # 字符串转元组（如 "-99999,-10" → (-99999, -10)）
            try:
                num1, num2 = map(int, str_key.split(","))
                restored_text[(num1, num2)] = text
            except (ValueError, IndexError):
                # 兼容旧数据，解析失败则用默认值
                restored_text = self.situation_text  # 回退到默认配置
                break
        self.situation_text = restored_text
