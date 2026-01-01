"""
便携函数库，集合了本项目可能用到的一些函数
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

import uuid
import hashlib
import os


# 颜色常量
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"


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
    finally_text = []  # 用于避免频繁创建字符串
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
                print(f"\n[文本美化]注意：不符合预期的文本嵌套结构{text}\n 文本将不会被美化 \n按任意键继续")
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
