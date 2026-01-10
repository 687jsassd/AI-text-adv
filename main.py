"""
游戏主程序，用于进行游戏循环流程，进行显示等。
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from typing import Tuple
from datetime import datetime
import json
import os
import gzip
import sys
import logging
from collections import deque
from rich import print
from config import (LOG_DIR,
                    CustomConfig)
from libs.animes_rich import GameTitle, console
from libs.event_manager import cmd_manager
from libs.logger import init_global_logger, log_exceptions
from libs.practical_funcs import (clear_screen,
                                  COLOR_RESET,
                                  COLOR_RED,
                                  COLOR_YELLOW,
                                  generate_game_id,
                                  find_file_by_name,
                                  text_colorize,
                                  )
from libs.token_ana import analyze_token_consume
from game_engine import GameEngine


# 日志初始化
init_global_logger()
logger = logging.getLogger(__name__)


if getattr(sys, 'frozen', False):
    # 打包后：exe所在目录（处理符号链接/中文路径）
    exe_path = os.path.abspath(sys.executable)
    root_path = os.path.dirname(exe_path)
else:
    # 未打包：脚本所在目录（双击py时，__file__是绝对路径，不受CWD影响）
    script_path = os.path.abspath(__file__)
    root_path = os.path.dirname(script_path)
# 强制切换工作目录到程序根目录
os.chdir(root_path)


VERSION = "Reborn-v0.1.8"


# 额外数据，存储回合数等必要的需要持久化的信息
class ExtraData:
    """
    引擎用，额外数据，存储回合数等必要的需要持久化的信息
    """

    def __init__(self):
        self.turns = 0

    def read_from_dict(self, extra_datas: dict):
        """
        从字典读取额外数据
        """
        self.turns = extra_datas.get("turns", 0)

    def to_dict(self) -> dict:
        """
        转换为字典
        """
        return {
            "turns": self.turns,
        }


config = CustomConfig()


# 保存游戏
@log_exceptions(logger)
def save_game(game_engine, extra_datas: ExtraData, save_name="autosave", is_manual_save=False):
    """
    保存游戏状态到文件（使用gzip压缩）
    """
    if extra_datas is None:
        extra_datas = ExtraData()
    try:
        # 创建保存目录
        save_dir = "saves"
        if not os.path.exists(save_dir):
            logger.info("创建保存目录 %s", save_dir)
            os.makedirs(save_dir)

        # 获取或生成游戏ID
        if not game_engine.game_id:
            game_engine.game_id = generate_game_id()
            logger.info("生成游戏ID %s", game_engine.game_id)

        # 创建游戏专属目录
        game_save_dir = os.path.join(save_dir, game_engine.game_id)
        if not os.path.exists(game_save_dir):
            logger.info("创建游戏专属目录 %s", game_save_dir)
            os.makedirs(game_save_dir)

        save_data = {
            "version": VERSION,
            "save_desc": save_name,
            "game_id": game_engine.game_id,
            "timestamp": datetime.now().isoformat(),
            # 基础变量
            "player_name": game_engine.player_name,
            "current_response": game_engine.current_response,
            "current_description": game_engine.current_description,
            "history_descriptions": game_engine.history_descriptions,
            "history_choices": game_engine.history_choices,
            "history_simple_summaries": game_engine.history_simple_summaries,
            "conversation_history": game_engine.conversation_history,
            # 摘要压缩相关
            "summary_conclude_val": game_engine.summary_conclude_val,
            "conclude_summary_cooldown": game_engine.conclude_summary_cooldown,
            # Token统计
            "total_prompt_tokens": game_engine.total_prompt_tokens,
            "last_prompt_tokens": game_engine.l_p_token,
            "total_completion_tokens": game_engine.total_completion_tokens,
            "last_completion_tokens": game_engine.l_c_token,
            "total_tokens": game_engine.total_tokens,
            "token_consumes": game_engine.token_consumes,
            # 自定义配置（保留）
            "custom_config": {
                "max_tokens": game_engine.custom_config.max_tokens,
                "temperature": game_engine.custom_config.temperature,
                "frequency_penalty": game_engine.custom_config.frequency_penalty,
                "presence_penalty": game_engine.custom_config.presence_penalty,
                "player_name": game_engine.custom_config.player_name,
                "player_story": game_engine.custom_config.player_story,
                "porn_value": game_engine.custom_config.porn_value,
                "violence_value": game_engine.custom_config.violence_value,
                "blood_value": game_engine.custom_config.blood_value,
                "horror_value": game_engine.custom_config.horror_value,
                "custom_prompts": game_engine.custom_config.custom_prompts,
                "api_provider_choice": game_engine.custom_config.api_provider_choice,
            },

            # 其他拓展变量
            "message_queue": list(game_engine.message_queue),
            "total_turns": len(game_engine.history_descriptions),
            "extra_datas": extra_datas.to_dict(),
        }

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if is_manual_save:
            filename = f"manual_{save_name}_{timestamp}.json.gz"
        else:
            filename = f"{save_name}_{timestamp}.json.gz"
        filepath = os.path.join(game_save_dir, filename)
        logger.info("保存游戏数据到 %s", filepath)

        # 保存到压缩文件（使用gzip.open，模式为wt：文本写入）
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        logger.info("游戏数据保存完成")

        # 更新最新保存文件
        latest_file = os.path.join(
            game_save_dir, f"{save_name}_latest.json.gz")
        with gzip.open(latest_file, 'wt', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        logger.info("最新保存文件 %s 更新完成", latest_file)

        # 如果不是手动保存，进行自动存档管理
        if not is_manual_save:
            logger.info("自动保存-开始管理自动保存")
            manage_auto_saves(game_save_dir, save_name)

        return True, f"游戏已保存到 {game_engine.game_id}/{filename}"

    except Exception as e:  # type:ignore
        logger.error("保存失败: %s", str(e))
        return False, f"保存失败: {str(e)}"


@log_exceptions(logger)
def manage_auto_saves(game_save_dir, save_name="autosave"):
    """管理自动保存，只保留最近的5个存档（兼容gzip压缩存档和旧版未压缩存档）"""
    # 获取所有自动保存文件（同时匹配 .json 和 .json.gz 后缀）
    auto_save_files = []
    for f in os.listdir(game_save_dir):
        # 过滤条件：
        # 1. 以save_name开头 2. 不是手动存档 3. 不是latest文件 4. 后缀是.json或.json.gz
        if (f.startswith(save_name) and
            not f.startswith('manual_') and
            not f.endswith('_latest.json') and
            not f.endswith('_latest.json.gz') and
                f.endswith(('.json', '.json.gz'))):
            auto_save_files.append(f)
    logger.info("找到了%s个自动保存文件", len(auto_save_files))

    if len(auto_save_files) > 5:
        # 按时间戳排序（文件名包含时间戳，排序后最早的在前）
        # 排序逻辑：提取文件名中的时间戳部分进行比较，确保排序准确
        def get_file_timestamp(filename):
            # 提取时间戳（格式：YYYYMMDD_HHMMSS）
            # 文件名格式：save_name_YYYYMMDD_HHMMSS.json(.gz)
            parts = filename.replace(
                '.json', '').replace('.gz', '').split('_')
            # 找到时间戳部分（长度为15：YYYYMMDD_HHMMSS）
            for part in parts:
                if len(part) == 15 and part[:8].isdigit() and part[9:].isdigit():
                    return part
            return filename  # 兜底：用原文件名排序

        auto_save_files.sort(key=get_file_timestamp)
        files_to_delete = auto_save_files[:-5]  # 保留最后5个

        for filename in files_to_delete:
            filepath = os.path.join(game_save_dir, filename)
            os.remove(filepath)
            logger.info("自动删除旧存档: %s", filepath)


# 读取存档
@log_exceptions(logger)
def load_game(game_engine, extra_datas: ExtraData, save_name="autosave", filename=None, game_id=None):
    """
    从文件加载游戏状态（适配gzip压缩存档，也兼容json存档）
    """
    try:
        save_dir = "saves"
        if not os.path.exists(save_dir):
            logger.info("没有找到保存文件目录")
            return False, "没有找到保存文件目录"

        # 确定要加载的文件
        if filename and game_id:
            # 兼容手动指定的文件名（自动补全.gz后缀）
            if not filename.endswith(('.json', '.json.gz')):
                filepath = os.path.join(
                    save_dir, game_id, f"{filename}.json.gz")
            else:
                filepath = os.path.join(save_dir, game_id, filename)
        elif filename:
            filepath = find_file_by_name(save_dir, filename)
            if not filepath:
                # 尝试查找压缩版本
                filepath = find_file_by_name(save_dir, f"{filename}.gz")
                if not filepath:
                    return False, f"没有找到保存文件 {filename}（含压缩版本）"
        else:
            if game_id:
                game_save_dir = os.path.join(save_dir, game_id)
                if not os.path.exists(game_save_dir):
                    return False, f"没有找到游戏 {game_id} 的保存目录"
                # 优先查找压缩版最新存档
                filepath = os.path.join(
                    game_save_dir, f"{save_name}_latest.json.gz")
                # 如果没有压缩版，尝试旧版未压缩
                if not os.path.exists(filepath):
                    filepath = os.path.join(
                        game_save_dir, f"{save_name}_latest.json")
            else:
                filepath = find_latest_save(save_dir, save_name)
                if not filepath:
                    # 尝试查找压缩版
                    filepath = find_latest_save(save_dir, f"{save_name}.gz")
                    if not filepath:
                        return False, f"没有找到 {save_name} 的保存文件（含压缩版本）"

        if not os.path.exists(filepath):
            logger.info("保存文件不存在: %s", filepath)
            return False, f"保存文件不存在: {filepath}"

        # 读取保存数据（兼容压缩/未压缩）
        save_data = None
        if filepath.endswith('.gz'):
            # 读取gzip压缩文件
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                save_data = json.load(f)
            logger.info("成功读取压缩存档: %s", filepath)
        else:
            # 读取旧版未压缩文件
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            logger.info("成功读取未压缩存档: %s", filepath)

        # 版本检查
        if save_data["version"] != VERSION:
            logger.warning("存档版本不匹配: 存档版本 %s, 游戏版本 %s",
                           save_data["version"], VERSION)
            tmp = input(
                f"\n[警告]:最新存档具有不匹配的版本号(存档{save_data['version']} -- 游戏{VERSION})\n 强制读取？(y/n)")
            if tmp.lower() != "y":
                return False, "版本号不匹配"
            else:
                logger.warning("强制读取存档")

        # 恢复基础变量
        extra_datas.read_from_dict(save_data["extra_datas"])
        game_engine.game_id = save_data["game_id"]
        game_engine.player_name = save_data["player_name"]
        game_engine.current_response = save_data.get(
            "current_response", "")
        game_engine.current_description = save_data["current_description"]
        game_engine.history_descriptions = save_data["history_descriptions"]
        game_engine.history_choices = save_data["history_choices"]
        game_engine.history_simple_summaries = save_data["history_simple_summaries"]
        game_engine.conversation_history = save_data["conversation_history"]

        # 恢复摘要压缩相关
        game_engine.summary_conclude_val = save_data.get(
            "summary_conclude_val", 24)
        game_engine.conclude_summary_cooldown = save_data["conclude_summary_cooldown"]

        # 恢复Token统计
        game_engine.total_prompt_tokens = save_data["total_prompt_tokens"]
        game_engine.l_p_token = save_data["last_prompt_tokens"]
        game_engine.total_completion_tokens = save_data["total_completion_tokens"]
        game_engine.l_c_token = save_data["last_completion_tokens"]
        game_engine.total_tokens = save_data["total_tokens"]
        game_engine.token_consumes = save_data["token_consumes"]

        # 恢复自定义配置
        config_data = save_data["custom_config"]
        game_engine.custom_config.max_tokens = config_data["max_tokens"]
        game_engine.custom_config.temperature = config_data["temperature"]
        game_engine.custom_config.frequency_penalty = config_data["frequency_penalty"]
        game_engine.custom_config.presence_penalty = config_data["presence_penalty"]
        game_engine.custom_config.player_name = config_data["player_name"]
        game_engine.custom_config.player_story = config_data["player_story"]
        game_engine.custom_config.porn_value = config_data["porn_value"]
        game_engine.custom_config.violence_value = config_data["violence_value"]
        game_engine.custom_config.blood_value = config_data["blood_value"]
        game_engine.custom_config.horror_value = config_data["horror_value"]
        game_engine.custom_config.custom_prompts = config_data["custom_prompts"]
        if "api_provider_choice" in config_data:
            game_engine.custom_config.api_provider_choice = config_data["api_provider_choice"]

        # 恢复其他拓展变量
        game_engine.message_queue = deque(
            save_data["message_queue"])

        # 格式化时间并返回结果
        timestamp = datetime.fromisoformat(
            save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        logger.info("成功加载存档: 游戏ID %s, 保存时间 %s",
                    save_data['game_id'], timestamp)
        return True, f"游戏已加载 (游戏ID: {save_data['game_id']}, 保存时间: {timestamp})"

    except Exception as e:  # type:ignore
        logger.error("加载存档时发生错误: %s", str(e))
        return False, f"加载失败: {str(e)}"


@log_exceptions(logger)
def find_latest_save(save_dir, save_name="autosave", include_manual=False):
    """查找所有游戏中最新的存档文件"""
    all_candidates = []
    added_files = set()
    logger.info("查找最新存档 | 根目录: %s | 前缀: %s", save_dir, save_name)

    if not os.path.exists(save_dir):
        logger.error("存档目录不存在: %s", save_dir)
        return None

    # 遍历所有游戏目录收集候选
    for game_id in os.listdir(save_dir):
        game_save_dir = os.path.join(save_dir, game_id)
        if not os.path.isdir(game_save_dir):
            continue

        # 处理latest文件
        latest_file = os.path.join(
            game_save_dir, f"{save_name}_latest.json.gz")
        if os.path.exists(latest_file) and latest_file not in added_files:
            try:
                with gzip.open(latest_file, 'rt', encoding='utf-8') as f:
                    save_data = json.load(f)
                if "timestamp" in save_data:
                    save_time = datetime.fromisoformat(save_data["timestamp"])
                    # 优先找实际存档
                    ts_str = datetime.fromisoformat(
                        save_data["timestamp"]).strftime("%Y%m%d_%H%M%S")
                    actual_file = os.path.join(
                        game_save_dir, f"{save_name}_{ts_str}.json.gz")
                    if os.path.exists(actual_file) and actual_file not in added_files:
                        all_candidates.append((save_time, actual_file))
                        added_files.add(actual_file)
                    else:
                        all_candidates.append((save_time, latest_file))
                        added_files.add(latest_file)
            except Exception as e:
                logger.error("解析latest文件失败: %s | %s", latest_file, e)

        # 处理实际存档文件
        for filename in os.listdir(game_save_dir):
            filepath = os.path.join(game_save_dir, filename)
            if (filepath in added_files or not filename.endswith(".json.gz") or
                filename.endswith("_latest.json.gz") or
                    not (filename.startswith(f"{save_name}_") or (include_manual and filename.startswith(f"manual_{save_name}_")))):
                continue

            try:
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    save_data = json.load(f)
                if "timestamp" in save_data:
                    save_time = datetime.fromisoformat(save_data["timestamp"])
                    all_candidates.append((save_time, filepath))
                    added_files.add(filepath)
            except Exception as e:
                logger.error("解析存档失败: %s | %s", filepath, e)

    # 全局排序找最新
    if all_candidates:
        all_candidates.sort(key=lambda x: x[0], reverse=True)
        latest_time, latest_save = all_candidates[0]
        logger.info("最新存档: %s | 时间: %s", latest_save,
                    latest_time.strftime('%Y-%m-%d %H:%M:%S'))
        return latest_save
    else:
        logger.warning("未找到有效存档")
        return None


# 列出所有保存文件
@log_exceptions(logger)
def list_saves():
    """
    列出所有保存文件（兼容gzip压缩存档和旧版未压缩存档），按游戏ID分类
    """
    save_dir = "saves"
    if not os.path.exists(save_dir):
        return []

    save_info = []

    # 遍历所有游戏目录
    for game_id in os.listdir(save_dir):
        try:
            game_save_dir = os.path.join(save_dir, game_id)
            if not os.path.isdir(game_save_dir):
                continue

            # 获取该游戏的所有保存文件（同时匹配 .json 和 .json.gz 后缀）
            save_files = [
                f for f in os.listdir(game_save_dir)
                if f.endswith(('.json', '.json.gz'))  # 兼容两种格式
                and not f.startswith('.')  # 排除隐藏文件
            ]

            for filename in save_files:
                filepath = os.path.join(game_save_dir, filename)
                # 根据文件后缀选择读取方式
                if filename.endswith('.gz'):
                    # 读取gzip压缩文件
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        save_data = json.load(f)
                else:
                    # 读取旧版未压缩文件
                    with open(filepath, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)

                # 解析存档信息
                timestamp = datetime.fromisoformat(
                    save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                save_desc = save_data.get("save_desc", "autosave")
                save_info.append({
                    "game_id": game_id,
                    "filename": filename,
                    "player_name": save_data["player_name"],
                    "timestamp": timestamp,
                    "total_turns": save_data["total_turns"],
                    "save_type": "manual" if filename.startswith("manual_") else "auto",
                    "save_desc": save_desc,
                    "ver": save_data["version"],
                    "file_format": "gzip" if filename.endswith('.gz') else "plain"
                })
        except Exception as e:
            logger.error("解析存档 %s 失败: %s", game_id, e)
            continue

    save_info.sort(key=lambda x: x["timestamp"], reverse=True)
    return save_info


# 手动保存函数（供用户调用）
def manual_save(game_engine, extra_datas: ExtraData):
    """
    手动保存游戏，允许用户输入保存名称
    """
    save_name = input("输入保存名称（留空使用默认名称）: ").strip()
    if not save_name:
        save_name = "manual_save"

    success, message = save_game(
        game_engine, extra_datas, save_name, is_manual_save=True)
    print(message)
    return success


# 手动加载函数（供用户调用）
def manual_load(game_engine, extra_datas: ExtraData):
    """
    手动加载游戏，分两级选择：
    1. 先选择游戏ID（其他游戏ID优先，当前游戏ID在最后）
    2. 再选择该游戏ID下的具体存档
    """
    # 获取所有存档数据
    all_saves = list_saves()
    if not all_saves:
        print("没有找到保存文件")
        return False, extra_datas

    current_game_id = getattr(game_engine, "game_id", None)
    if not current_game_id:
        print("无法获取当前游戏ID，将显示所有存档")
        current_game_id = ""

    # 分离当前游戏ID的存档和其他游戏ID的存档
    current_saves = [s for s in all_saves if s["game_id"] == current_game_id]
    other_saves = [s for s in all_saves if s["game_id"] != current_game_id]

    # 提取其他游戏ID的唯一值并去重
    other_game_ids = sorted(
        list(set([s["game_id"] for s in other_saves])), reverse=False)

    # 构建第一级选择菜单（游戏ID选择）
    print("\n===== 选择游戏存档组 =====")
    # 1. 显示其他游戏ID
    for i, game_id in enumerate(other_game_ids, 1):
        # 统计该ID下的存档数量
        save_count = len([s for s in other_saves if s["game_id"] == game_id])
        print(f"{i}. 游戏ID: {game_id} (存档数量: {save_count})")

    # 2. 显示当前游戏ID选项（如果有当前ID且有存档）
    current_option_idx = len(other_game_ids) + 1
    if current_game_id and current_saves:
        print(
            f"{current_option_idx}. 当前游戏ID: {current_game_id} (存档数量: {len(current_saves)})")
    elif current_game_id and not current_saves:
        print(f"{current_option_idx}. 当前游戏ID: {current_game_id} (无存档)")

    # 3. 取消选项
    cancel_idx = len(other_game_ids) + (1 if current_game_id else 0) + 1
    print(f"{cancel_idx}. 取消")

    # 处理第一级选择（游戏ID选择）
    try:
        first_choice = input(f"\n请选择存档组编号（1-{cancel_idx}）: ")
        if first_choice == str(cancel_idx):  # 取消
            return False, extra_datas

        first_choice_idx = int(first_choice)

        # 校验选择范围
        max_valid_idx = len(other_game_ids) + (1 if current_game_id else 0)
        if first_choice_idx < 1 or first_choice_idx > max_valid_idx:
            print("无效的选择编号")
            return False, extra_datas

        # 确定选中的游戏ID
        selected_game_id = ""
        if first_choice_idx <= len(other_game_ids):
            # 选择了其他游戏ID
            selected_game_id = other_game_ids[first_choice_idx - 1]
        else:
            # 选择了当前游戏ID
            selected_game_id = current_game_id

        # 筛选该游戏ID下的所有存档
        target_saves = [
            s for s in all_saves if s["game_id"] == selected_game_id]
        if not target_saves:
            print(f"游戏ID {selected_game_id} 下无可用存档")
            return False, extra_datas

        # 构建第二级选择菜单（具体存档选择）
        print(f"\n===== 选择 {selected_game_id} 的具体存档 =====")
        for i, save in enumerate(target_saves, 1):
            save_type = "手动" if save['save_type'] == 'manual' else "自动"
            version_warn = (
                f"{COLOR_YELLOW}不匹配的游戏版本{save['ver']}{COLOR_RESET}"
                if save['ver'] != VERSION else ""
            )
            save_desc = f"-{save['save_desc']}" if save['save_desc'] != 'autosave' else ""
            print(
                f"{i}. {save['game_id']}{save_desc}-{save['player_name']}-回合{save['total_turns']}-{save_type} {version_warn}"
                f" (存档时间: {save['timestamp']})"
            )

        # 处理第二级选择（具体存档）
        second_choice = input("\n选择要加载的存档编号（输入0取消）: ")
        if second_choice == "0":
            return False, extra_datas

        second_choice_idx = int(second_choice) - 1
        if 0 <= second_choice_idx < len(target_saves):
            selected_save = target_saves[second_choice_idx]
            success, message = load_game(
                game_engine, extra_datas,
                filename=selected_save["filename"],
                game_id=selected_save["game_id"]
            )
            if success:
                print(message)
                return success, extra_datas
            else:
                print(message)
                return False, extra_datas
        else:
            print("无效的存档编号")
            return False, extra_datas

    except ValueError:
        print("请输入有效的数字")
        return False, extra_datas
    except Exception as e:
        print(f"加载存档过程中出错: {e}")
        if logger:
            logger.error("手动加载存档失败", exc_info=e)
        return False, extra_datas


# 自定义行动的处理(必须件)
def custom_action_func(game: GameEngine, skip_inputs: Tuple = ('help',)):
    """
    自定义行动
    """
    print(f"输入 /指令 以使用指令,如/help\n {COLOR_YELLOW}你决定{COLOR_RESET}")
    custom_action = input(
        "::")
    if custom_action in skip_inputs:
        print(f"{COLOR_RED}提示：为了避免误输入，建议使用 /+指令 来进行指令{COLOR_RESET}\n指令将继续执行，按任意键继续")
        input()
        return custom_action
    if custom_action.startswith('/'):
        cmd_input = custom_action[1:]
        if cmd_input in skip_inputs:
            return cmd_input
        else:
            print("无效指令")
    else:
        if custom_action.strip() == "":
            print("自定义行动取消")
            return ""
        game.go_game(custom_action)
    return custom_action


# 打印游戏历史记录(集成到主循环中)
def print_all_history(game: GameEngine, back_range: int = 50):
    """
    打印游戏历史记录（排除当前局，仅显示历史局；超过back_range时取最后back_range条历史）
    """
    total_turns = len(game.history_descriptions)
    history_descs = game.history_descriptions[:-1] if total_turns > 0 else []
    history_choices = game.history_choices
    recent_descs = history_descs[-back_range:] if history_descs else []
    recent_choices = history_choices[-back_range:] if history_choices else []
    start_turn = len(history_descs) - len(recent_descs) + \
        1 if history_descs else 0
    for idx, (desc, choice) in enumerate(zip(recent_descs, recent_choices)):
        real_turn = start_turn + idx
        print(f"{real_turn}:")
        print(text_colorize(desc))
        print(f"{COLOR_YELLOW}我选择:{COLOR_RESET}", text_colorize(choice))
        console.rule(style="white")


@log_exceptions(logger)
def new_game(no_auto_load=False):
    """
    主游戏逻辑
    """
    extra_datas = ExtraData()
    game_instance = GameEngine(config)
    show_init_resp = False
    no_save_again_sign = False  # 运行查看类指令后，不再自动保存

    def init_turn_datas():
        nonlocal no_save_again_sign
        no_save_again_sign = False

    def reg_cmds():
        def cmd_summary():
            clear_screen()
            print("<剧情摘要>")
            print("\n".join(
                [f"{i+1}. {it}" for i, it in enumerate(list(game_instance.history_simple_summaries))]))

        def cmd_ana_token():
            analyze_token_consume(game_instance.token_consumes)

        def cmd_show_init_resp():
            nonlocal show_init_resp
            show_init_resp = not show_init_resp
            print(f"将显示AI原始响应与Token信息：{show_init_resp}")

        def cmd_config():
            nonlocal no_save_again_sign
            game_instance.custom_config.config_game()
            no_save_again_sign = False

        def cmd_load():
            loadsuccess, _ = manual_load(game_instance, extra_datas)
            if loadsuccess:
                print("成功加载，按任意键继续...")
            else:
                print("加载失败，按任意键继续...")

        def cmd_save():
            manual_save(game_instance, extra_datas)

        def cmd_conclude_summary():
            nonlocal no_save_again_sign
            game_instance.go_game("", True)
            no_save_again_sign = False
            print("总结完成")

        cmd_manager.reg("help", cmd_manager.list_cmds, "列出所有指令")
        cmd_manager.reg("ana_token", cmd_ana_token, "进行token消耗分析")
        cmd_manager.reg("show_init_resp", cmd_show_init_resp, "切换显示原始AI回复")
        cmd_manager.reg("config", cmd_config, "配置游戏")
        cmd_manager.reg("load", cmd_load, "读取存档")
        cmd_manager.reg("save", cmd_save, "保存")
        cmd_manager.reg("summary", cmd_summary, "查看当前剧情摘要")
        cmd_manager.reg("conclude_summary", cmd_conclude_summary, "总结摘要")
        cmd_manager.reg("new", lambda: 1, "开始新游戏")
        cmd_manager.reg("exit", lambda: 1, "退出游戏")
    reg_cmds()

    commands = cmd_manager.cmds

    clear_screen()
    print("等待读取..")

    if not no_auto_load:
        loadsuccess, message = load_game(game_instance, extra_datas)
        print(message)
    else:
        loadsuccess = False
    if not loadsuccess:
        input("按任意键开始新游戏")
        game_instance.custom_config.config_game()
        game_instance = GameEngine(config)  # 防止部分配置未加载？
        game_instance.game_id = input("为本局游戏命名(或留空)：\n::").strip()
        st_story = input('输入开局故事(留空随机）:\n:: ')
        game_instance.anime_loader.start_animation(
            "spinner", message="*等待<世界>回应*")
        game_instance.start_game(st_story)
        game_instance.anime_loader.stop_animation()
        # 游戏ID
        if not game_instance.game_id:
            game_instance.game_id = generate_game_id()

    while True:
        clear_screen()
        print_all_history(game_instance)
        print(text_colorize(game_instance.current_description))
        game_instance.print_all_messages_await()
        print(
            f"字数:{sum([len(it) for it in game_instance.history_descriptions])} | Token/all:{game_instance.l_c_token+game_instance.l_p_token}/{game_instance.total_tokens} | Ver:{VERSION} | [{game_instance.game_id}]")

        if show_init_resp:
            print(game_instance.current_response)
            print(game_instance.get_token_stats())

        if not no_save_again_sign:
            game_instance.log_game(os.path.join(
                LOG_DIR, game_instance.game_id+f"_t{extra_datas.turns}.log"))
            save_game(game_instance, extra_datas)
            no_save_again_sign = True

        user_input = custom_action_func(
            game_instance, commands)

        if user_input == "exit":
            return 'exit'
        elif user_input == "new":
            return 'new_game'
        elif user_input in commands:
            cmd_manager.run(user_input)
            input("按任意键继续..")
        elif user_input:
            extra_datas.turns += 1
            init_turn_datas()


def main():
    """
    主函数，游戏入口
    """
    game_title = GameTitle()
    game_title.show()

    no_auto_load = False
    while True:
        i = new_game(no_auto_load)
        if i == 'exit':
            break
        elif i == 'new_game':
            no_auto_load = True
            continue
        else:
            print("新的开始...")


if __name__ == "__main__":
    main()
