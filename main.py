"""
游戏主程序，用于进行游戏循环流程，进行显示等。
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
from typing import Tuple
from datetime import datetime
import json
import os
import sys
from config import (LOG_DIR,
                    CURRENT_TIME,
                    CustomConfig)
from libs.event_manager import CommandManager
from libs.practical_funcs import (clear_screen,
                                  COLOR_GREEN,
                                  COLOR_RESET,
                                  COLOR_RED,
                                  COLOR_YELLOW,
                                  COLOR_MAGENTA,
                                  generate_game_id,
                                  find_file_by_name,
                                  text_colorize,
                                  )
from libs.animes import display_narrative_with_typewriter, SyncLoadingAnimation
from game_engine import GameEngine


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


VERSION = "0.1.6c"


# 额外数据，存储回合数等必要的需要持久化的信息
class ExtraData:
    """
    引擎用，额外数据，存储回合数等必要的需要持久化的信息
    """

    def __init__(self):
        self.turns = 0
        self.think_count_remain = 0
        self.skip_csmode_action_modify = False

    def read_from_dict(self, extra_datas: dict):
        """
        从字典读取额外数据
        """
        self.turns = extra_datas.get("turns", 0)
        self.think_count_remain = extra_datas.get("think_count_remain", 0)
        self.skip_csmode_action_modify = extra_datas.get(
            "skip_csmode_action_modify", False)

    def to_dict(self) -> dict:
        """
        转换为字典
        """
        return {
            "turns": self.turns,
            "think_count_remain": self.think_count_remain,
            "skip_csmode_action_modify": self.skip_csmode_action_modify,
        }


config = CustomConfig()
anime_loader = SyncLoadingAnimation()
cmd_manager = CommandManager()  # TODO 事件化指令


# 保存
def save_game(game_engine, extra_datas: ExtraData, save_name="autosave", is_manual_save=False):
    """
    保存游戏状态到文件
    """
    if extra_datas is None:
        extra_datas = ExtraData()
    try:
        # 创建保存目录
        save_dir = "saves"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # 获取或生成游戏ID
        if not game_engine.game_id:
            game_engine.game_id = generate_game_id()

        # 创建游戏专属目录
        game_save_dir = os.path.join(save_dir, game_engine.game_id)
        if not os.path.exists(game_save_dir):
            os.makedirs(game_save_dir)

        # 构建保存数据
        save_data = {
            "version": VERSION,
            "save_desc": save_name,
            "game_id": game_engine.game_id,
            "timestamp": datetime.now().isoformat(),
            "player_name": game_engine.player_name,
            "player_story": game_engine.prompt_manager.prompts_sections.get("user_story", ""),
            "current_description": game_engine.current_description,
            "current_options": game_engine.current_options,
            "current_game_status": game_engine.current_game_status,
            "history_descriptions": game_engine.history_descriptions,
            "history_choices": game_engine.history_choices,
            "history_simple_summaries": game_engine.history_simple_summaries,
            "inventory": game_engine.item_system.inventory,
            # "conversation_history": game_engine.conversation_history,
            "total_turns": len(game_engine.history_descriptions),
            "total_prompt_tokens": game_engine.total_prompt_tokens,
            "last_prompt_tokens": game_engine.l_p_token,
            "total_completion_tokens": game_engine.total_completion_tokens,
            "last_completion_tokens": game_engine.l_c_token,
            "total_tokens": game_engine.total_tokens,
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
            "character_attributes": game_engine.character_attributes,
            "situation_value": game_engine.situation,
            "token_consumes": game_engine.token_consumes,
            "extra_datas": extra_datas.to_dict(),
            "item_repo": game_engine.item_system.item_repository,
            "is_no_options": game_engine.prompt_manager.is_no_options,
            "variables": game_engine.variables,
            "conclude_cooldown": game_engine.conclude_summary_cooldown,
        }

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if is_manual_save:
            filename = f"manual_{save_name}_{timestamp}.json"
        else:
            filename = f"{save_name}_{timestamp}.json"
        filepath = os.path.join(game_save_dir, filename)

        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # 更新最新保存文件
        latest_file = os.path.join(game_save_dir, f"{save_name}_latest.json")
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        # 如果不是手动保存，进行自动存档管理
        if not is_manual_save:
            manage_auto_saves(game_save_dir, save_name)

        return True, f"游戏已保存到 {game_engine.game_id}/{filename}"

    except Exception as e:  # type:ignore
        return False, f"保存失败: {str(e)}"


# 管理自动保存文件，每局游戏不超过10个
def manage_auto_saves(game_save_dir, save_name="autosave"):
    """管理自动保存，只保留最近的10个存档"""
    try:
        # 获取所有自动保存文件
        auto_save_files = [f for f in os.listdir(game_save_dir)
                           if f.startswith(save_name) and f.endswith('.json')
                           and not f.startswith('manual_') and not f.endswith('_latest.json')]

        if len(auto_save_files) > 10:
            # 按时间排序，删除最早的存档
            auto_save_files.sort()  # 文件名包含时间戳，排序后最早的在前
            files_to_delete = auto_save_files[:-10]  # 保留最后10个

            for filename in files_to_delete:
                filepath = os.path.join(game_save_dir, filename)
                os.remove(filepath)

    except Exception as e:  # type:ignore
        print(f"自动存档管理失败: {e}")


# 读取
def load_game(game_engine, extra_datas: ExtraData, save_name="autosave", filename=None, game_id=None,):
    """
    从文件加载游戏状态
    """
    try:
        save_dir = "saves"

        if not os.path.exists(save_dir):
            return False, "没有找到保存文件目录"

        # 确定要加载的文件
        if filename and game_id:
            # 直接指定游戏ID和文件名
            filepath = os.path.join(save_dir, game_id, filename)
        elif filename:
            # 查找包含该文件名的游戏目录
            filepath = find_file_by_name(save_dir, filename)
            if not filepath:
                return False, f"没有找到保存文件 {filename}"
        else:
            # 加载最新的保存
            if game_id:
                # 指定游戏ID的最新保存
                game_save_dir = os.path.join(save_dir, game_id)
                if not os.path.exists(game_save_dir):
                    return False, f"没有找到游戏 {game_id} 的保存目录"
                filepath = os.path.join(
                    game_save_dir, f"{save_name}_latest.json")
            else:
                # 查找所有游戏的最新保存
                filepath = find_latest_save(save_dir, save_name)
                if not filepath:
                    return False, f"没有找到 {save_name} 的保存文件"

        if not os.path.exists(filepath):
            return False, f"保存文件不存在: {filepath}"

        # 读取保存数据
        with open(filepath, 'r', encoding='utf-8') as f:
            save_data = json.load(f)

        # 恢复游戏状态
        if save_data["version"] != VERSION:
            tmp = input(
                f"\n[警告]:不匹配的版本号(存档{save_data['version']} -- 游戏{VERSION})\n 强制读取？(y/n)")
            if tmp.lower() != "y":
                return False, "版本号不匹配"

        extra_datas.read_from_dict(save_data["extra_datas"])
        game_engine.game_id = save_data["game_id"]
        game_engine.player_name = save_data["player_name"]
        game_engine.prompt_manager.prompts_sections["user_story"] = save_data["player_story"]
        game_engine.current_description = save_data["current_description"]
        game_engine.current_options = save_data["current_options"]
        game_engine.current_game_status = save_data["current_game_status"]
        game_engine.history_descriptions = save_data["history_descriptions"]
        game_engine.history_choices = save_data["history_choices"]
        game_engine.history_simple_summaries = save_data["history_simple_summaries"]
        game_engine.item_system.inventory = save_data["inventory"]
        # game_engine.conversation_history = save_data["conversation_history"]
        game_engine.total_prompt_tokens = save_data["total_prompt_tokens"]
        game_engine.l_p_token = save_data["last_prompt_tokens"]
        game_engine.total_completion_tokens = save_data["total_completion_tokens"]
        game_engine.l_c_token = save_data["last_completion_tokens"]
        game_engine.total_tokens = save_data["total_tokens"]
        game_engine.character_attributes = save_data["character_attributes"]
        game_engine.situation = save_data["situation_value"]
        game_engine.token_consumes = save_data["token_consumes"]
        game_engine.item_system.item_repository = save_data["item_repo"]
        game_engine.prompt_manager.is_no_options = save_data["is_no_options"]
        game_engine.variables = save_data["variables"]
        game_engine.conclude_summary_cooldown = save_data["conclude_cooldown"]

        # 恢复配置
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

        timestamp = datetime.fromisoformat(
            save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        return True, f"游戏已加载 (游戏ID: {save_data['game_id']}, 保存时间: {timestamp})"

    except Exception as e:  # type:ignore
        return False, f"加载失败: {str(e)}"


# 找最新存档
def find_latest_save(save_dir, save_name="autosave"):
    """查找所有游戏中最新的保存文件"""
    latest_save = None
    latest_time = None

    for game_id in os.listdir(save_dir):
        game_save_dir = os.path.join(save_dir, game_id)
        if os.path.isdir(game_save_dir):
            latest_file = os.path.join(
                game_save_dir, f"{save_name}_latest.json")
            if os.path.exists(latest_file):
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
                    save_time = datetime.fromisoformat(save_data["timestamp"])
                    if latest_time is None or save_time > latest_time:
                        latest_time = save_time
                        latest_save = latest_file
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    print(f"解析保存文件时出错: {e}, 文件: {latest_file}")
                    continue

    return latest_save


# 列出存档文件
def list_saves():
    """
    列出所有保存文件，按游戏ID分类
    """
    try:
        save_dir = "saves"
        if not os.path.exists(save_dir):
            return []

        save_info = []

        # 遍历所有游戏目录
        for game_id in os.listdir(save_dir):
            game_save_dir = os.path.join(save_dir, game_id)
            if not os.path.isdir(game_save_dir):
                continue

            # 获取该游戏的所有保存文件
            save_files = [f for f in os.listdir(
                game_save_dir) if f.endswith('.json')]

            for filename in save_files:
                filepath = os.path.join(game_save_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        save_data = json.load(f)
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
                    })
                except (ValueError, TypeError) as e:
                    print(f"解析保存文件时出错: {e}, 文件: {filepath}")
                    continue

        # 按时间排序
        save_info.sort(key=lambda x: x["timestamp"], reverse=True)
        return save_info

    except Exception as e:  # type:ignore
        print(f"列出保存文件时出错: {e}")
        return []


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
    手动加载游戏，显示保存列表供用户选择
    """
    saves = list_saves()
    if not saves:
        print("没有找到保存文件")
        return False, extra_datas

    print("\n可用的保存文件 (按游戏ID分类):")
    for i, save in enumerate(saves, 1):
        save_type = "手动" if save['save_type'] == 'manual' else "自动"
        print(
            f"{i}.{save['game_id']}{'-'+save['save_desc']if save['save_desc'] != 'autosave' else ''}-{save['player_name']}-回合{save['total_turns']}-{save_type}{'-'+COLOR_YELLOW+"不匹配的游戏版本"+save['ver']+COLOR_RESET if save['ver'] != VERSION else ''}")

    try:
        choice = input("选择要加载的存档编号（输入0取消）: ")
        if choice == "0":
            return False, extra_datas

        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(saves):
            selected_save = saves[choice_idx]
            success, message = load_game(
                game_engine, extra_datas, filename=selected_save["filename"], game_id=selected_save["game_id"])
            if success:
                print(message)
                return success, extra_datas
            else:
                print(message)
                return False, extra_datas
        else:
            print("无效的选择")
            return False, extra_datas
    except ValueError:
        print("请输入有效的数字")
        return False, extra_datas


# 显示游戏选项(必须件)
def display_options(game: GameEngine):
    """
    显示游戏选项
    """
    if game.prompt_manager.is_no_options:
        print('-'*30)
        return
    has_impossible, has_danger, has_event, has_goods = False, False, False, False
    options, chara_attrs, situation = game.current_options, game.character_attributes, game.situation
    print("\n" + "你准备：")
    for opt in options:
        print(f"{opt['id']}. {text_colorize(opt['text'])}", end="")
        fix_value = (chara_attrs.get(
            opt["main_factor"], 0)-opt["difficulty"])*3/2000
        # 处理形势
        if situation > 0:
            fix_value += 0.01*2.2*situation**1.25
        elif situation < 0:
            fix_value += 0.04*situation
        if opt["type"] == "check":
            # 根据几率来添加不同提示
            if opt["probability"] < 0.1-fix_value:
                print(f"[{COLOR_RED}✘{COLOR_RESET}]")
                has_impossible = True
            elif opt["probability"] < 0.3-fix_value:
                print(f"[{COLOR_RED}!{COLOR_RESET}]")
                has_danger = True
            elif opt["probability"] < 0.65-fix_value:
                print(f"[{COLOR_YELLOW}?{COLOR_RESET}]")
                has_event = True
            else:
                print(f"[{COLOR_GREEN}▲{COLOR_RESET}]")
                has_goods = True
        elif opt["type"] == "must":
            if chara_attrs.get(opt["main_factor"], 0) >= opt["difficulty"]:
                print(
                    f"{COLOR_GREEN}[✓ {opt['main_factor']}≥{opt['difficulty']}]{COLOR_RESET}")
            else:
                print(
                    f"{COLOR_RED}[✘ {opt['main_factor']}≥{opt['difficulty']}]{COLOR_RESET}")
        else:
            print()
    if has_impossible:
        print(f"[{COLOR_RED}✘]极难检定{COLOR_RESET}")
    if has_danger:
        print(f"{COLOR_MAGENTA}[!]困难检定{COLOR_RESET}")
    if has_event:
        print(f"{COLOR_YELLOW}[?]中等检定{COLOR_RESET}")
    if has_goods:
        print(f"{COLOR_GREEN}[▲]简单检定{COLOR_RESET}")
    print("输入help 查看帮助")
    print('-'*30)


# 自定义行动的处理(必须件)
def custom_action_func(game: GameEngine, extra_datas: ExtraData, skip_inputs: Tuple = ('help',)):
    """
    自定义行动
    """
    custom_action = input(
        f"输入 /指令 以使用指令,如/help\n {COLOR_YELLOW}你决定{COLOR_RESET} \n::")
    if custom_action in skip_inputs:
        input(f"{COLOR_RED}提示：为了避免误输入，建议使用 /+指令 来进行指令{COLOR_RESET}\n指令将继续执行，按任意键继续")
        return custom_action
    if custom_action.startswith('/'):
        cmd_input = custom_action[1:]
        if cmd_input in skip_inputs:
            return cmd_input
        else:
            print("无效指令")
    else:
        if custom_action.strip() == "" or game.go_game(custom_action, is_custom=True, is_skip_csmode_action_modify=extra_datas.skip_csmode_action_modify) == -1:
            print("自定义行动无效/取消")
    return custom_action


# 获取用户输入并执行游戏操作(必须件)
def get_user_input_and_go(game: GameEngine, extra_datas: ExtraData, skip_inputs: Tuple = ('help',)):
    """
    获取用户输入并执行游戏操作
    """
    while True:
        if game.prompt_manager.is_no_options:
            custom_action = custom_action_func(game, extra_datas, skip_inputs)
            if custom_action:
                return custom_action
            else:
                continue
        anime_loader.stop_animation()
        user_input = input(":: ")
        if user_input in skip_inputs:
            return user_input
        if user_input.isdigit() and 1 <= int(user_input) <= len(game.current_options):
            display_narrative_with_typewriter(
                text_colorize(game.current_options[int(user_input)-1]['next_preview']))
        if not user_input.isdigit() or game.go_game(user_input) == -1:
            print("无效的选项ID，请重新输入。")
            continue
        return user_input


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
        print(desc)
        print(f"{COLOR_YELLOW}我选择:{COLOR_RESET}", choice)
        print("\n" + '-'*40)


# 显示物品/变量数警告(已集成到主循环中)
def show_item_var_caution(game: GameEngine):
    """如果物品数/变量数超过35.分别提醒用户注意token消耗和适用性"""
    if len(game.item_system.inventory) > 35:
        print(COLOR_YELLOW +
              f"*物品数超过35个({len(game.item_system.inventory)}/50),建议调整背包"+COLOR_RESET)
    if len(game.variables) > 35:
        print(COLOR_YELLOW +
              f"*变量数超过35个({len(game.variables)}),建议清理不必要变量"+COLOR_RESET)


# 操作物品(opi指令)
def operate_item(game: GameEngine):
    """
    操作物品
    """
    is_use_item, (itemname, action, target) = game.item_system.operate_item()
    if is_use_item:
        print("等待合理性判定...")
        if game.is_use_item_ok(itemname, action, target):
            print("操作合理，正在执行...")
            game.go_game(
                f"对{target}使用背包里的物品{itemname}进行{action}操作", is_custom=True)
            return True
        else:
            user_confirm = input("警告:操作不合理,仍要执行吗? (y/n)")
            if user_confirm.lower() == "y":
                print("正在执行...")
                game.go_game(
                    f"对{target}使用背包里的物品{itemname}进行{action}操作 (操作不合理!)", True)
                return True
            else:
                input("操作已取消")
    else:
        return False


# 分析token消耗趋势(ana_token指令)
def analyze_token_consume(game: GameEngine):
    """
    分析游戏过程中token消耗趋势
    """
    # 获取总轮数
    total_rounds = len(game.token_consumes)

    # 存储结果
    results = []

    # 从10轮开始，每10轮作为一个区间，直到总轮数
    for interval_end in range(10, total_rounds + 1, 10):
        # 计算当前区间(1到interval_end轮)的平均token消耗
        rounds_data = game.token_consumes[:interval_end]
        avg_consume = sum(rounds_data) / interval_end

        # 为简单线性回归准备数据
        x_vals = list(range(1, interval_end + 1))
        y_vals = game.token_consumes[:interval_end]

        # 简单线性回归（最小二乘法）
        n = interval_end
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        # 计算斜率和截距
        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / \
                (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = avg_consume

        # 保存结果
        results.append({
            'rounds': interval_end,
            'avg_consume': avg_consume,
            'slope': slope,
            'intercept': intercept
        })

    # 如果总轮数不是10的倍数，添加最后一个区间
    if total_rounds % 10 != 0:
        rounds_data = game.token_consumes[:total_rounds]
        avg_consume = sum(rounds_data) / total_rounds

        x_vals = list(range(1, total_rounds + 1))
        y_vals = game.token_consumes[:total_rounds]

        n = total_rounds
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / \
                (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = avg_consume

        results.append({
            'rounds': total_rounds,
            'avg_consume': avg_consume,
            'slope': slope,
            'intercept': intercept
        })

    # 输出结果
    for result in results:
        rounds = result['rounds']
        avg = result['avg_consume']
        slope = result['slope']
        intercept = result['intercept']

        print(f"1-{rounds}轮:")
        print(f"  平均token消耗: {avg:.2f}")
        print(f"  拟合直线: y = {slope:.4f}x + {intercept:.4f}")
        print(f"  预测下一轮消耗: {slope * (rounds + 1) + intercept:.2f}")
        print()
    input('按任意键继续')


def new_game(no_auto_load=False):
    """
    主游戏逻辑
    """
    commands = (
        "help",
        "save",
        "load",
        "new",
        "config",
        "exit",
        "inv",
        "opi",
        "attr",
        "summary",
        "vars",
        "custom",
        "csmode",
        "cs*f",
        "think",
        "setvar",
        "delvar",
        "conclude_summary",
        "ana_token",
        "fix_item_name",
        "show_init_resp"
    )

    extra_datas = ExtraData()

    game_instance = GameEngine(config)
    clear_screen()
    print("等待读取..")
    show_init_resp = False
    if not no_auto_load:
        loadsuccess, message = load_game(game_instance, extra_datas)
        print(message)
    else:
        loadsuccess = False
    if not loadsuccess:
        input("按任意键开始配置游戏参数,配置完毕后，将设置主角初始属性,之后游戏开始。")
        game_instance.custom_config.config_game()
        game_instance = GameEngine(config)  # 防止部分配置未加载？
        # 设定属性
        while True:
            attrs = input(
                "依次输入6个数来决定你的属性(力、敏、智、感、魅、运;一般建议均在5-50间,默认均为20)\n::")
            if attrs.strip() == "":
                break
            attrs = attrs.split()
            if len(attrs) != 6:
                print("请输入6个数")
                continue
            try:
                attrs = [float(it) for it in attrs]
            except ValueError:
                print("请输入6个数")
                continue
            for key, val in zip(game_instance.character_attributes.keys(), attrs):
                game_instance.character_attributes[key] = val
            break
        print(game_instance.get_attribute_text(colorize=True))
        tmp = input("以自定义模式开局？(y/n)\n::")
        if tmp.strip() == "y":
            game_instance.prompt_manager.is_no_options = True
        game_instance.game_id = input("为本局游戏命名(或留空)：\n::").strip()
        st_story = input('输入开局故事(留空随机）:\n:: ')
        anime_loader.start_animation("spinner", message="*等待<世界>回应*")
        game_instance.start_game(st_story)
        anime_loader.stop_animation()
        # 思考次数
        extra_datas.think_count_remain = int(max(
            min(game_instance.character_attributes["INT"]//8, 4), -1)) + 1
        # 游戏ID
        if not game_instance.game_id:
            game_instance.game_id = generate_game_id()
    no_repeat_sign = False  # 运行指令后，原本的文字不再打字机效果输出

    def init_turn_datas():
        nonlocal no_repeat_sign
        no_repeat_sign = False
        extra_datas.think_count_remain = int(max(
            # 重置思考次数
            min(game_instance.character_attributes["INT"]//8, 4), -1)) + 1

    while game_instance.current_game_status == "ongoing":
        clear_screen()
        print_all_history(game_instance)
        if not no_repeat_sign:
            display_narrative_with_typewriter(
                text_colorize(game_instance.current_description))
            no_repeat_sign = True
        else:
            print(text_colorize(game_instance.current_description))
        print(game_instance.get_situation_text())
        game_instance.print_all_messages_await()
        show_item_var_caution(game_instance)
        display_options(game_instance)

        print(
            f"字数:{sum([len(it) for it in game_instance.history_descriptions])} | Token/all:{game_instance.l_c_token+game_instance.l_p_token}/{game_instance.total_tokens} | Ver:{VERSION} | [{game_instance.game_id}]")
        if show_init_resp:
            print(game_instance.current_response)
            print(game_instance.get_token_stats())
        if not game_instance.current_description.strip() or not game_instance.current_options:
            print("可能出现错误")
            print(game_instance.current_response)
        game_instance.log_game(os.path.join(
            LOG_DIR, game_instance.game_id+f"_{CURRENT_TIME}.log"))
        save_game(game_instance, extra_datas)
        user_input = get_user_input_and_go(
            game_instance, extra_datas, commands)

        if user_input == "exit":
            return 'exit'
        elif user_input == "csmode":
            game_instance.prompt_manager.is_no_options = not game_instance.prompt_manager.is_no_options
            print(
                f"自定义模式{'开启' if game_instance.prompt_manager.is_no_options else '关闭'}")
            input("按任意键继续...")
            continue
        elif user_input == "inv":
            print(game_instance.item_system.get_inventory_text())
            input("按任意键继续...")
            continue
        elif user_input == "opi":
            if operate_item(game_instance):
                init_turn_datas()
                continue
            input("按任意键继续...")
            continue
        elif user_input == "summary":
            clear_screen()
            print("摘要")
            print("\n".join(
                [f"{i+1}. {it}" for i, it in enumerate(list(game_instance.history_simple_summaries))]))
            input("按任意键继续...")
            continue
        elif user_input == "conclude_summary":
            game_instance.go_game("", False, True)
            input("总结完成，按任意键继续...")
            continue
        elif user_input == "attr":
            print(game_instance.get_attribute_text(colorize=True))
            input("按任意键继续...")
            continue
        elif user_input == "vars":
            clear_screen()
            print(game_instance.get_vars_text())
            input("按任意键继续...")
            continue
        elif user_input == "setvar":
            clear_screen()
            print(game_instance.get_vars_text())
            name = input("请输入要设置的变量名：\n:: ")
            val = input("请输入要设置的变量值：\n:: ")
            game_instance.variables[name] = val
            input("完成设置，按任意键继续...")
            continue
        elif user_input == "delvar":
            clear_screen()
            print(game_instance.get_vars_text())
            name = input("请输入要删除的变量名：\n:: ")
            if name not in game_instance.variables:
                input("变量不存在，按任意键继续...")
                continue
            del game_instance.variables[name]
            input("完成删除，按任意键继续...")
            continue
        elif user_input == "save":
            manual_save(game_instance, extra_datas)
            input("按任意键继续...")
            continue
        elif user_input == "load":
            loadsuccess, message = manual_load(game_instance, extra_datas)
            if loadsuccess:
                print("成功加载，按任意键继续...")
                no_repeat_sign = False  # 加载游戏成功，重新启用打字机效果
                continue
            else:
                print("加载失败，按任意键继续...")
                continue
        elif user_input == "config":
            game_instance.custom_config.config_game()
            continue
        elif user_input == "new":
            return 'new_game'
        elif user_input == "show_init_resp":
            show_init_resp = not show_init_resp
            print(f"将显示AI原始响应与Token信息：{show_init_resp}")
            input("按任意键继续...")
            continue
        elif user_input == "fix_item_name":
            game_instance.item_system.fix_item_name_error()
            print("道具名修复完成")
            input("按任意键继续...")
            continue
        elif user_input == "ana_token":
            analyze_token_consume(game_instance)
            continue
        elif user_input == "think":
            if extra_datas and extra_datas.think_count_remain <= 0:
                input("你无法再思考了，做出决定吧.(按任意键继续)")
                continue
            content = input(
                f"你思索某个疑问(思考次数还剩{int(extra_datas.think_count_remain)}次) 不输入内容以放弃思考 注意token消耗:\n:: ")
            if content.strip() == "":
                input("你放弃了思考.(按任意键继续)")
                continue
            game_instance.think_go_game(content)
            extra_datas.think_count_remain -= 1
            input("思考完成，按任意键继续...")
            continue
        elif user_input == "cs*f":
            extra_datas.skip_csmode_action_modify = not extra_datas.skip_csmode_action_modify
            print(
                f"将{'跳过' if extra_datas.skip_csmode_action_modify else '不跳过'}自定义行动的行动修饰")
            input("按任意键继续...")
            continue

        elif user_input == "help":
            print("可用指令：")
            print("-"*20)
            print(f"{COLOR_GREEN}save{COLOR_RESET}:保存游戏")
            print(f"{COLOR_GREEN}load{COLOR_RESET}:读取游戏")
            print(f"{COLOR_GREEN}new{COLOR_RESET}:新游戏")
            print(f"{COLOR_GREEN}config{COLOR_RESET}:配置游戏")
            print(f"{COLOR_GREEN}exit{COLOR_RESET}: 退出游戏")
            print(f"{COLOR_GREEN}inv{COLOR_RESET}: 查看道具")
            print(f"{COLOR_GREEN}opi{COLOR_RESET}:进行道具操作")
            print(f"{COLOR_GREEN}attr{COLOR_RESET}:显示属性")
            print(f"{COLOR_GREEN}summary{COLOR_RESET}:查看摘要")
            print(f"{COLOR_GREEN}vars{COLOR_RESET}:查看变量")
            print("-"*20)
            print(f"{COLOR_YELLOW}custom{COLOR_RESET}:自定义行动")
            print(f"{COLOR_YELLOW}csmode{COLOR_RESET}:切换自定义模式")
            print(f"{COLOR_YELLOW}cs*f{COLOR_RESET}:切换自定义行动的行动修饰")
            print(f"{COLOR_YELLOW}think{COLOR_RESET}:思考/联想")
            print(f"{COLOR_YELLOW}setvar{COLOR_RESET}:添加/设置变量")
            print(f"{COLOR_YELLOW}delvar{COLOR_RESET}:删除变量")
            print("-"*20)
            print(f"{COLOR_RED}conclude_summary{COLOR_RESET}:手动总结当前摘要(不推荐)")
            print(f"{COLOR_RED}ana_token{COLOR_RESET}:统计token数据")
            print(f"{COLOR_RED}fix_item_name{COLOR_RESET}:修复道具名中的错误")
            print(
                f"{COLOR_RED}show_init_resp{COLOR_RESET}:切换显示对每轮剧情的AI的原始相应与Token信息(debug)")
            print('-'*20)
            input("按任意键继续...")
            continue
        else:
            extra_datas.turns += 1
            init_turn_datas()

    clear_screen()
    print("游戏结束,下面是你本局游戏的摘要")
    print(f"你共进行了{extra_datas.turns}轮游戏")
    for turn, it in enumerate(game_instance.history_simple_summaries):
        print(f"第{turn+1}轮：{it}")
    input("按任意键退出...")


def main():
    """
    主函数，游戏入口
    """
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
