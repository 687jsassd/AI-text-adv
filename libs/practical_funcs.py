"""
便携函数库，集合了本项目可能用到的一些函数
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from typing import Any, Dict
import re
import uuid
import hashlib
import os


# 颜色常量
COLOR_RED = "[bold red]"  # \033[91m
COLOR_GREEN = "[bold green]"  # \033[92m
COLOR_YELLOW = "[bold yellow]"  # \033[93m
COLOR_BLUE = "[bold blue]"  # \033[94m
COLOR_MAGENTA = "[bold magenta]"  # \033[95m
COLOR_CYAN = "[bold cyan]"  # \033[96m
COLOR_RESET = "[white]"  # \033[0m

TO_ANSI_COLORS = {
    '[bold red]': "\033[91m",
    '[bold green]': "\033[92m",
    '[bold yellow]': "\033[93m",
    '[bold blue]': "\033[94m",
    '[bold magenta]': "\033[95m",
    '[bold cyan]': "\033[96m",
    '[white]': "\033[0m",
}


# 清空控制台屏幕
def clear_screen():
    """
    清空控制台屏幕
    """
    os.system('cls' if os.name == 'nt' else 'clear')


# 对文本进行颜色美化
def text_colorize(text: str):
    """
    对文本进行颜色美化
    """
    rcs = [COLOR_RESET]  # remain_color_stack
    rnccs = []  # remain_need_close_chars_stack
    finally_text = [COLOR_RESET]  # 预放RESET以统一颜色
    current_printing_color = COLOR_RESET
    color_convert_dict = {
        "<": COLOR_MAGENTA,
        "[": COLOR_CYAN,
        "『": COLOR_YELLOW,
        "《": COLOR_RED,
        "「": COLOR_GREEN,
        "【": COLOR_BLUE,
    }
    close_chars = {
        ">": "<",
        "]": "[",
        "』": "『",
        "》": "《",
        "」": "「",
        "】": "【",
    }
    # 从开始向字符串末尾逐字符扫描替换
    for i in text:
        if i in color_convert_dict:
            current_printing_color = color_convert_dict[i]
            rnccs.append(i)
            rcs.append(current_printing_color)
            finally_text.append(current_printing_color+i)
        elif i in close_chars:
            if rnccs and rnccs[-1] == close_chars[i]:
                rnccs.pop()
            else:
                print("\n[文本美化]注意：不符合预期的文本嵌套结构,文本将不会被美化")
                return text
            if rcs:
                rcs.pop()
                current_printing_color = rcs[-1] if rcs else COLOR_RESET
                finally_text.append(i+current_printing_color)
            else:
                finally_text.append(i+COLOR_RESET)
        else:
            finally_text.append(i)
    finally_text.append(COLOR_RESET)  # 强制重置颜色
    return ''.join(finally_text)


# 生成8位字符的唯一游戏标识符
def generate_game_id():
    """生成8位字符的唯一游戏标识符"""
    # 使用UUID和哈希生成8位唯一标识
    unique_id = str(uuid.uuid4())
    hash_object = hashlib.md5(unique_id.encode())
    return hash_object.hexdigest()[:8]


# 根据文件名找文件
def find_file_by_name(direc, filename):
    """根据文件名查找保存文件"""
    for item_id in os.listdir(direc):
        targ_dir = os.path.join(direc, item_id)
        if os.path.isdir(targ_dir):
            filepath = os.path.join(targ_dir, filename)
            if os.path.exists(filepath):
                return filepath
    return None


# 替换文本中的颜色代码为ANSI的
def replace_color_code(text: str):
    """
    替换文本中的颜色代码为ANSI的
    """
    for color, to_ansi in TO_ANSI_COLORS.items():
        text = text.replace(color, to_ansi)
    return text

# 规则替换


def rule_replace(text: str, rule_dict: Dict[str, Any], values_dict: Dict[str, Any] = None) -> str:
    """
    规则替换：对text文本，按照rule_dict中的规则进行替换

    参数:
        text: 原始文本
        rule_dict: 替换规则字典，格式如 {"name": "张三", "age": "{age}"}
        values_dict: 变量值字典，当rule_dict中的值以{var}格式时使用

    返回:
        替换后的文本

    示例:
        text = "你好，{name}，你今年{age}岁。"
        rule_dict = {"name": "张三", "age": "{age}"}
        values_dict = {"age": 18}
        result = replace_rule(text, rule_dict, values_dict)
        # 输出: 你好，张三，你今年18岁。

    会抛出错误的情况:
        - 变量值在values_dict中不存在(如有替换为{name}的规则,但values_dict中没有name)
        - 变量值不能转为字符串
    """
    if values_dict is None:
        values_dict = {}

    processed_rules = {}

    for key, value in rule_dict.items():
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            var_name = value[1:-1]
            if var_name in values_dict:
                processed_rules[key] = str(values_dict[var_name])
            else:
                raise ValueError(f"[规则替换]错误：变量'{var_name}'在values_dict中不存在")
        else:
            processed_rules[key] = str(value)

    def replace_match(match):
        key = match.group(1)
        return processed_rules.get(key, match.group(0))
    pattern = r'\{([^{}]+)\}'
    return re.sub(pattern, replace_match, text)


# 多行输入
def get_multiline_input(prompt: str = '::', end_marker: str = "---") -> str:
    """
    获取用户的多行输入（回车不提交，直到输入结束符/空行）

    参数:
        prompt: 输入提示语(注意,不会自动换行)
        end_marker: 结束输入的标记（默认---，用户单独输入该标记即结束）

    返回:
        拼接后的多行文本（行与行之间用\n分隔）
    """
    print(f"（输入空行或单独输入'{end_marker}'后回车结束输入）\n{prompt}", end='')
    lines = []
    while True:
        line = input()
        if not line or line.strip() == end_marker:
            break
        lines.append(line)
    return "\n".join(lines)
