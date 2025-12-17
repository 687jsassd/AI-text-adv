# Copyright (c) 2025 [687jsassd]
# MIT License
import uuid
import hashlib
from datetime import datetime
import json
import os
from game_engine import GameEngine
from config import LOG_DIR, CURRENT_TIME, CustomConfig, COLOR_GREEN, COLOR_RESET, COLOR_RED, COLOR_YELLOW
from animes import typewriter_narrative, show_loading_animation, SyncLoadingAnimation

config = CustomConfig()

VERSION = "0.1.4"

extra_datas = {
    "turn": 0,
    "think_count_remain": 0,
}

# 显示函数


def display_narrative_with_typewriter(narr: str,
                                      separator: str = "",
                                      color: str = "") -> bool:
    """
    增强版的叙述显示函数，带有打字机效果

    Args:
        narr: 叙述文本
        separator: 分隔线
        color: 颜色代码

    Returns:
        bool: 是否被用户中断
    """
    print("\n" + separator)

    paras = narr.split("\n")
    interrupted = False

    for para in paras:
        if para.strip() and not interrupted:
            para_interrupted = typewriter_narrative(
                para.strip(),
                color=color,
                suffix="\n"
            )
            if para_interrupted:
                interrupted = True
                break

    if not interrupted:
        print(separator)

    return interrupted


def generate_game_id():
    """生成8位字符的唯一游戏标识符"""
    # 使用UUID和哈希生成8位唯一标识
    unique_id = str(uuid.uuid4())
    hash_object = hashlib.md5(unique_id.encode())
    return hash_object.hexdigest()[:8]


def save_game(game_engine, save_name="autosave", is_manual_save=False):
    """
    保存游戏状态到文件
    """
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
            "inventory": game_engine.inventory,
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
                "base_urls_choice": game_engine.custom_config.base_urls_choice,
                "model_names_choice": game_engine.custom_config.model_names_choice,
                "api_keys_choice": game_engine.custom_config.api_keys_choice,
            },
            "character_attributes": game_engine.character_attributes,
            "situation_value": game_engine.situation,
            "token_consumes": game_engine.token_consumes,
            "extra_datas": extra_datas,
            "item_repo": game_engine.item_repository,
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

    except Exception as e:
        return False, f"保存失败: {str(e)}"


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

    except Exception as e:
        print(f"自动存档管理失败: {e}")


def load_game(game_engine, save_name="autosave", filename=None, game_id=None):
    """
    从文件加载游戏状态
    """
    global extra_datas
    try:
        save_dir = "saves"

        if not os.path.exists(save_dir):
            return False, 0, "没有找到保存文件目录"

        # 确定要加载的文件
        if filename and game_id:
            # 直接指定游戏ID和文件名
            filepath = os.path.join(save_dir, game_id, filename)
        elif filename:
            # 查找包含该文件名的游戏目录
            filepath = find_save_file_by_name(save_dir, filename)
            if not filepath:
                return False, 0, f"没有找到保存文件 {filename}"
        else:
            # 加载最新的保存
            if game_id:
                # 指定游戏ID的最新保存
                game_save_dir = os.path.join(save_dir, game_id)
                if not os.path.exists(game_save_dir):
                    return False, 0, f"没有找到游戏 {game_id} 的保存目录"
                filepath = os.path.join(
                    game_save_dir, f"{save_name}_latest.json")
            else:
                # 查找所有游戏的最新保存
                filepath = find_latest_save(save_dir, save_name)
                if not filepath:
                    return False, 0, f"没有找到 {save_name} 的保存文件"

        if not os.path.exists(filepath):
            return False, 0, f"保存文件不存在: {filepath}"

        # 读取保存数据
        with open(filepath, 'r', encoding='utf-8') as f:
            save_data = json.load(f)

        # 恢复游戏状态
        if save_data["version"] != VERSION:
            input(f"[警告]:不匹配的版本号(存档{save_data['version']} -- 游戏{VERSION})")
        game_engine.game_id = save_data["game_id"]
        game_engine.player_name = save_data["player_name"]
        game_engine.prompt_manager.prompts_sections["user_story"] = save_data["player_story"]
        game_engine.current_description = save_data["current_description"]
        game_engine.current_options = save_data["current_options"]
        game_engine.current_game_status = save_data["current_game_status"]
        game_engine.history_descriptions = save_data["history_descriptions"]
        game_engine.history_choices = save_data["history_choices"]
        game_engine.history_simple_summaries = save_data["history_simple_summaries"]
        game_engine.inventory = save_data["inventory"]
        # game_engine.conversation_history = save_data["conversation_history"]
        game_engine.total_prompt_tokens = save_data["total_prompt_tokens"]
        game_engine.l_p_token = save_data["last_prompt_tokens"]
        game_engine.total_completion_tokens = save_data["total_completion_tokens"]
        game_engine.l_c_token = save_data["last_completion_tokens"]
        game_engine.total_tokens = save_data["total_tokens"]
        game_engine.character_attributes = save_data["character_attributes"]
        game_engine.situation = save_data["situation_value"]
        game_engine.token_consumes = save_data["token_consumes"]
        game_engine.item_repository = save_data["item_repo"]

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
        game_engine.custom_config.base_urls_choice = config_data["base_urls_choice"]
        game_engine.custom_config.model_names_choice = config_data["model_names_choice"]
        game_engine.custom_config.api_keys_choice = config_data["api_keys_choice"]
        extra_datas = save_data["extra_datas"]

        timestamp = datetime.fromisoformat(
            save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        return True, save_data['total_turns'], f"游戏已加载 (游戏ID: {save_data['game_id']}, 保存时间: {timestamp})"

    except Exception as e:
        return False, 0, f"加载失败: {str(e)}"


def find_save_file_by_name(save_dir, filename):
    """根据文件名查找保存文件"""
    for game_id in os.listdir(save_dir):
        game_save_dir = os.path.join(save_dir, game_id)
        if os.path.isdir(game_save_dir):
            filepath = os.path.join(game_save_dir, filename)
            if os.path.exists(filepath):
                return filepath
    return None


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
                except:
                    continue

    return latest_save


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
                    save_info.append({
                        "game_id": game_id,
                        "filename": filename,
                        "timestamp": timestamp,
                        "player_name": save_data["player_name"],
                        "total_turns": save_data["total_turns"],
                        "save_type": "manual" if filename.startswith("manual_") else "auto"
                    })
                except:
                    continue

        # 按时间排序
        save_info.sort(key=lambda x: x["timestamp"], reverse=True)
        return save_info

    except Exception as e:
        print(f"列出保存文件时出错: {e}")
        return []


def delete_save(game_id, filename):
    """
    删除指定的保存文件
    """
    try:
        filepath = os.path.join("saves", game_id, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True, f"保存文件 {game_id}/{filename} 已删除"
        else:
            return False, f"保存文件 {game_id}/{filename} 不存在"

    except Exception as e:
        return False, f"删除失败: {str(e)}"

# 手动保存函数（供用户调用）


def manual_save(game_engine):
    """
    手动保存游戏，允许用户输入保存名称
    """
    save_name = input("输入保存名称（留空使用默认名称）: ").strip()
    if not save_name:
        save_name = "manual_save"

    success, message = save_game(game_engine, save_name, is_manual_save=True)
    print(message)
    return success

# 手动加载函数（供用户调用）


def manual_load(game_engine):
    """
    手动加载游戏，显示保存列表供用户选择
    """
    saves = list_saves()
    if not saves:
        print("没有找到保存文件")
        return False, 0

    print("\n可用的保存文件 (按游戏ID分类):")
    for i, save in enumerate(saves, 1):
        save_type = "手动" if save['save_type'] == 'manual' else "自动"
        print(
            f"{i}.{save['game_id']}-{save['player_name']}-回合{save['total_turns']}-类型: {save_type}")

    try:
        choice = input("选择要加载的存档编号（输入0取消）: ")
        if choice == "0":
            return False, 0

        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(saves):
            selected_save = saves[choice_idx]
            success, turns, message = load_game(
                game_engine, filename=selected_save["filename"], game_id=selected_save["game_id"])
            if success:
                print(message)
                return success, turns
            else:
                print(message)
                return False, 0
        else:
            print("无效的选择")
            return False, 0
    except ValueError:
        print("请输入有效的数字")
        return False, 0


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def display_narrative(narr: str):
    return display_narrative_with_typewriter(narr)


def display_options(GAME: GameEngine):
    has_danger, has_event, has_goods = False, False, False
    options, chara_attrs, situation = GAME.current_options, GAME.character_attributes, GAME.situation
    print("\n" + "你准备：")
    for opt in options:
        print(f"{opt['id']}. {opt['text']}", end="")
        fix_value = (chara_attrs.get(
            opt["main_factor"], 0)-opt["difficulty"])*3/2000
        # 处理形势
        if situation > 0:
            fix_value += 0.01*3*situation**1.5
        elif situation < 0:
            fix_value += 0.03*situation
        if opt["type"] == "check":
            # 根据几率来添加不同提示
            if opt["probability"] < 0.05-fix_value:
                print(f"[{COLOR_RED}✘{COLOR_RESET}]", end="")
                has_danger = True
            elif opt["probability"] < 0.25-fix_value:
                print(f"[{COLOR_RED}!{COLOR_RESET}]", end="")
                has_danger = True
            elif opt["probability"] < 0.70-fix_value:
                print(f"[{COLOR_YELLOW}?{COLOR_RESET}]", end="")
                has_event = True
            else:
                print(f"[{COLOR_GREEN}▲{COLOR_RESET}]", end="")
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

        if opt["type"] == "check" and opt['main_factor'] in chara_attrs:
            print(f" ^{opt['main_factor']}")

    if has_danger:
        print(f"[{COLOR_RED}✘ !{COLOR_RESET}] {COLOR_RED}困难检定{COLOR_RESET}")
    if has_event:
        print(f"[{COLOR_YELLOW}?{COLOR_RESET}] {COLOR_YELLOW}中等检定{COLOR_RESET}")
    if has_goods:
        print(f"[{COLOR_GREEN}▲{COLOR_RESET}] {COLOR_GREEN}简单检定{COLOR_RESET}")
    print("输入help 查看帮助")
    print('-'*30)


def get_user_input_and_go(GAME: GameEngine):
    while True:
        loader = show_loading_animation("dot", message="整理中")
        loader.stop_animation()  # type:ignore
        user_input = input(":: ")
        if user_input in ['exit', 'opi', 'think', 'inv', 'attr', 'conclude_summary', 'help', 'summary', 'save', 'load', 'new', 'config', 'show_init_resp', 'fix_item_name', 'ana_token']:
            return user_input
        if user_input.isdigit() and 1 <= int(user_input) <= len(GAME.current_options):
            display_narrative(
                GAME.current_options[int(user_input)-1]['next_preview'])
        if user_input == "custom":
            custom_action = input("你决定：")
            if GAME.go_game(custom_action, is_custom=True) == -1:
                print("自定义行动无效，请重新输入。")
                continue
            return custom_action
        if not user_input.isdigit() or GAME.go_game(user_input) == -1:
            print("无效的选项ID，请重新输入。")
            continue
        return user_input


def print_all_history(GAME: GameEngine, back_range: int = 50):
    for turn, desc, choice in zip(range(1, len(GAME.history_descriptions[-back_range:])+1), GAME.history_descriptions[-back_range:], GAME.history_choices[-back_range:]):
        print(f"{turn}:")
        print(desc)
        print(choice)
        print("\n" + '-'*60)


def config_game():
    is_exit = False
    while not is_exit:
        clear_screen()
        print("输入你想要配置的参数:")
        print(f"1.最大输出Token [{config.max_tokens}]")
        print(f"2.温度 [{config.temperature}]")
        print(f"3.频率惩罚 [{config.frequency_penalty}]")
        print(f"4.存在惩罚 [{config.presence_penalty}]")
        print(f"5.玩家姓名 [{config.player_name}]")
        print(f"6.玩家故事 [{config.player_story}]")
        print(f"7.偏好:色情 [{config.frequency_reflect[config.porn_value]}]")
        print(f"8.偏好:特别暴力 [{config.frequency_reflect[config.violence_value]}]")
        print(f"9.偏好:血腥 [{config.frequency_reflect[config.blood_value]}]")
        print(f"10.偏好:恐怖 [{config.frequency_reflect[config.horror_value]}]")
        print(f"11.自定义附加提示词 [{config.custom_prompts}]")
        print(f"12.模型 [{config.model_names[config.model_names_choice][1]}]")
        print(f"13.API密钥 [{config.api_keys[config.api_keys_choice][1]}]")
        print(f"14.基础URL [{config.base_urls[config.base_urls_choice][1]}]")
        print("exit. 退出配置(完成配置)")

        while True:
            choice = input("输入你想要配置的参数ID：")
            if choice == "exit":
                is_exit = True
                config.save_to_file()
                break
            if choice.isdigit() and 1 <= int(choice) <= 14:
                choice = int(choice)
                if choice == 1:
                    config.max_tokens = int(input("输入最大输出Token数："))
                elif choice == 2:
                    config.temperature = float(input("输入温度："))
                elif choice == 3:
                    config.frequency_penalty = float(input("输入频率惩罚："))
                elif choice == 4:
                    config.presence_penalty = float(input("输入存在惩罚："))
                elif choice == 5:
                    config.player_name = input("输入玩家姓名：")
                elif choice == 6:
                    config.player_story = input("输入玩家故事：")
                elif choice == 7:
                    config.porn_value = int(input("输入色情偏好（0-5）："))
                elif choice == 8:
                    config.violence_value = int(input("输入特别暴力偏好（0-5）："))
                elif choice == 9:
                    config.blood_value = int(input("输入血腥偏好（0-5）："))
                elif choice == 10:
                    config.horror_value = int(input("输入恐怖偏好（0-5）："))
                elif choice == 11:
                    config.custom_prompts = input("输入自定义附加提示词：")
                elif choice == 12:
                    print("可用模型:")
                    for key, val in config.model_names.items():
                        print(f"{key}. {val[1]}")
                    config.model_names_choice = int(input("输入模型ID："))
                elif choice == 13:
                    print("可用API密钥:")
                    for key, val in config.api_keys.items():
                        print(f"{key}. {val[1]}")
                    config.api_keys_choice = int(input("输入API密钥ID："))
                elif choice == 14:
                    print("可用基础URL:")
                    for key, val in config.base_urls.items():
                        print(f"{key}. {val[1]}")
                    config.base_urls_choice = int(input("输入基础URL ID："))
                break
            else:
                print("无效的选项ID，请重新输入。")
                continue


def operate_item(GAME: GameEngine):
    show_desc = True
    while True:
        clear_screen()
        print(GAME.current_description)
        print("当前物品:" + GAME.get_inventory_text(show_desc))
        print("仓库物品:" + GAME.get_item_repository_text(show_desc))
        print("\n物品操作")
        print("输入 '*use 被操作的物品名(或id) 进行什么操作 对哪个目标' 以操作物品(会推进剧情) 例如:'石子 投掷 梅超风'表示对梅超风投掷石子 ")
        print("输入 '*remove 物品名(或id)' 以销毁物品")
        print("输入 '*put 物品名(或id)' 以存储物品  (只有前25个物品会参与剧情，无用物品请进行存储)")
        print("输入 '*get 物品名(或id)' 以从存储获得物品")
        print("输入 '*add 物品名 物品描述' 以添加物品")
        print("输入 '*rename 物品id 新名称' 以重命名物品")
        print("输入 '*redesc 物品id 新描述' 以改变物品描述")
        print("输入 '*putall' 将所有物品转移到仓库")
        print("输入 '*getall' 获得所有仓库中物品")
        print("输入 '*desc 物品名(或id)' 以查看该物品描述")
        print("输入 '*showdesc' 以切换是否显示描述")
        print("exit. 退出物品操作")
        user_input = input("输入操作:\n::")
        if user_input == "exit":
            return False
        elif user_input.startswith("*remove"):
            item_name = user_input.split("*remove")[1].strip()
            if item_name.isdigit() and int(item_name) <= len(GAME.inventory):
                item_name = list(GAME.inventory.keys())[int(item_name)-1]
            if item_name in GAME.inventory:
                del GAME.inventory[item_name]
                print(f"物品 {item_name} 已被销毁")
            else:
                print(f"物品 {item_name} 不存在于你的库存中")
        elif user_input.startswith("*put"):
            item_name = user_input.split("*put")[1].strip()
            if item_name.isdigit() and int(item_name) <= len(GAME.inventory):
                item_name = list(GAME.inventory.keys())[int(item_name)-1]
            if item_name in GAME.inventory:
                GAME.item_repository[item_name] = GAME.inventory[item_name]
                del GAME.inventory[item_name]
                print(f"物品 {item_name} 已被存储")
            else:
                print(f"物品 {item_name} 不存在于你的库存中")
        elif user_input.startswith("*get"):
            item_name = user_input.split("*get")[1].strip()
            if item_name.isdigit() and int(item_name) <= len(GAME.item_repository):
                item_name = list(GAME.item_repository.keys())[int(item_name)-1]
            if item_name in GAME.item_repository:
                GAME.inventory[item_name] = GAME.item_repository[item_name]
                del GAME.item_repository[item_name]
                print(f"物品 {item_name} 已被获得")
            else:
                print(f"物品 {item_name} 不存在于物品仓库中")
        elif user_input.startswith("*add"):
            item_name, item_desc = user_input.split(
                "*add")[1].strip().split(" ", 1)
            GAME.item_repository[item_name] = item_desc
            print(f"物品 {item_name} 已被添加")
        elif user_input.startswith("*rename"):
            item_id, new_name = user_input.split(
                "*rename")[1].strip().split(" ", 1)
            if item_id.isdigit() and int(item_id) <= len(GAME.inventory):
                item_name = list(GAME.inventory.keys())[int(item_id)-1]
            if item_name in GAME.inventory:
                GAME.inventory[new_name] = GAME.inventory[item_name]
                del GAME.inventory[item_name]
                print(f"物品 {item_name} 已被重命名为 {new_name}")
            else:
                print(f"物品 {item_name} 不存在于你的库存中")
        elif user_input.startswith("*redesc"):
            item_id, new_desc = user_input.split(
                "*redesc")[1].strip().split(" ", 1)
            if item_id.isdigit() and int(item_id) <= len(GAME.inventory):
                item_name = list(GAME.inventory.keys())[int(item_id)-1]
            if item_name in GAME.inventory:
                GAME.inventory[item_name] = new_desc
                print(f"物品 {item_name} 已被重描述为 {new_desc}")
            else:
                print(f"物品 {item_name} 不存在于你的库存中")
        elif user_input == "*putall":
            GAME.item_repository.update(GAME.inventory)
            GAME.inventory.clear()
            print("所有物品已被存储")
        elif user_input == "*getall":
            GAME.inventory.update(GAME.item_repository)
            GAME.item_repository.clear()
            print("所有物品已被获得")
        elif user_input.startswith("*use"):
            itemname, action, target = user_input.split(
                "*use")[1].strip().split()
            if itemname.isdigit() and int(itemname) <= len(GAME.inventory):
                itemname = list(GAME.inventory.keys())[int(itemname)-1]
            if itemname in GAME.inventory:
                print("等待合理性判定...")
                if GAME.is_use_item_ok(itemname, action, target):
                    print("操作合理，正在执行...")
                    GAME.go_game(
                        f"对{target}使用背包里的物品{itemname}进行{action}操作", True)
                    return True
                else:
                    print("警告:操作不合理,仍要执行吗? (y/n)")
                    user_confirm = input()
                    if user_confirm.lower() == "y":
                        print("正在执行...")
                        GAME.go_game(
                            f"对{target}使用背包里的物品{itemname}进行{action}操作 (操作不合理!)", True)
                        return True
                    else:
                        print("操作已取消")
            else:
                print(f"物品 {itemname} 不存在于你的库存中")
        elif user_input.startswith("*desc"):
            item_name = user_input.split("*desc")[1].strip()
            if item_name.isdigit() and int(item_name) <= len(GAME.inventory):
                item_name = list(GAME.inventory.keys())[int(item_name)-1]
            if item_name in GAME.inventory:
                print(f"物品 {item_name} 的描述为: {GAME.inventory[item_name]}")
            else:
                print(f"物品 {item_name} 不存在于你的库存中")
        elif user_input == "*showdesc":
            show_desc = not show_desc
        else:
            print("无效输入")
            continue
    return False


def analyze_token_consume(GAME: GameEngine):
    # 获取总轮数
    total_rounds = len(GAME.token_consumes)

    # 存储结果
    results = []

    # 从10轮开始，每10轮作为一个区间，直到总轮数
    for interval_end in range(10, total_rounds + 1, 10):
        # 计算当前区间(1到interval_end轮)的平均token消耗
        rounds_data = GAME.token_consumes[:interval_end]
        avg_consume = sum(rounds_data) / interval_end

        # 为简单线性回归准备数据
        x_vals = list(range(1, interval_end + 1))
        y_vals = GAME.token_consumes[:interval_end]

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
        rounds_data = GAME.token_consumes[:total_rounds]
        avg_consume = sum(rounds_data) / total_rounds

        x_vals = list(range(1, total_rounds + 1))
        y_vals = GAME.token_consumes[:total_rounds]

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
    global extra_datas
    anime_loader = SyncLoadingAnimation()
    GAME = GameEngine(config)
    extra_datas = {"turns": 0,
                   "think_count_remain": 0}
    clear_screen()
    anime_loader.start_animation("spinner", message="读取中")
    show_init_resp = False
    if not no_auto_load:
        loadsuccess, _, message = load_game(GAME)
        print(message)
    else:
        loadsuccess = False
    anime_loader.stop_animation()
    if not loadsuccess:
        input("按任意键开始配置游戏参数,配置完毕后，将设置主角初始属性,之后游戏开始。")
        config_game()
        GAME = GameEngine(config)  # 防止部分配置未加载？
        # 设定属性
        while True:
            attrs = input(
                "依次输入6个数来决定你的属性(力、敏、智、感、魅、运;一般建议均在5到20之间,默认均为10)\n::")
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
            for key, val in zip(GAME.character_attributes.keys(), attrs):
                GAME.character_attributes[key] = val
            break
        print(GAME.get_attribute_text(colorize=True))
        GAME.game_id = input("为本局游戏命名(或留空)：\n::").strip()
        st_story = input('输入开局故事(留空随机）:\n:: ')
        anime_loader.start_animation("spinner", message="*等待<世界>回应*")
        GAME.start_game(st_story)
        anime_loader.stop_animation()
        # 思考次数
        extra_datas["think_count_remain"] = int(max(
            min(GAME.character_attributes["INT"]//8, 4), -1)) + 1
        # 游戏ID
        if not GAME.game_id:
            GAME.game_id = generate_game_id()
    no_repeat_sign = False  # 运行指令后，原本的文字不再打字机效果输出

    def init_turn_datas():
        global no_repeat_sign, extra_datas
        no_repeat_sign = False
        extra_datas["think_count_remain"] = int(max(
            min(GAME.character_attributes["INT"]//8, 4), -1)) + 1  # 重置思考次数

    while GAME.current_game_status == "ongoing":
        extra_datas["turns"] += 1
        clear_screen()
        print_all_history(GAME)
        if not no_repeat_sign:
            display_narrative(GAME.current_description)
            print(GAME.get_situation_text())
            display_options(GAME)
            no_repeat_sign = True
        else:
            print(GAME.current_description)
            print(GAME.get_situation_text())
            display_options(GAME)
        print(
            f"字数:{sum([len(it) for it in GAME.history_descriptions])} | Token/all:{GAME.l_c_token+GAME.l_p_token}/{GAME.total_tokens} | Ver:{VERSION} | [{GAME.game_id}]")
        if show_init_resp:
            print(GAME.current_response)
            print(GAME.get_token_stats())
        if not GAME.current_description.strip() or not GAME.current_options:
            print("可能出现错误")
            print(GAME.current_response)
        GAME.log_game(os.path.join(
            LOG_DIR, GAME.game_id+f"_{CURRENT_TIME}.log"))
        save_game(GAME)
        user_input = get_user_input_and_go(GAME)

        if user_input == "exit":
            return 'exit'
        elif user_input == "inv":
            print(GAME.get_inventory_text())
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "opi":
            if operate_item(GAME):
                init_turn_datas()
                continue
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "summary":
            clear_screen()
            print("摘要")
            print("\n".join(
                [f"{i+1}. {it}" for i, it in enumerate(list(GAME.history_simple_summaries))]))
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "conclude_summary":
            GAME.go_game("", False, True)
            extra_datas["turns"] -= 1
            input("总结完成，按任意键继续...")
            continue
        elif user_input == "attr":
            print(GAME.get_attribute_text(colorize=True))
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "save":
            manual_save(GAME)
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "load":
            loadsuccess, _ = manual_load(GAME)
            if loadsuccess:
                print("成功加载，按任意键继续...")
                no_repeat_sign = False  # 加载游戏成功，重新启用打字机效果
                continue
            else:
                print("加载失败，按任意键继续...")
                continue
        elif user_input == "config":
            config_game()
            extra_datas["turns"] -= 1
            continue
        elif user_input == "new":
            return 'new_game'
        elif user_input == "show_init_resp":
            show_init_resp = not show_init_resp
            print(f"将显示AI原始响应与Token信息：{show_init_resp}")
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "fix_item_name":
            GAME.fix_item_name_error()
            print("道具名修复完成")
            extra_datas["turns"] -= 1
            input("按任意键继续...")
            continue
        elif user_input == "ana_token":
            analyze_token_consume(GAME)
            extra_datas["turns"] -= 1
            continue
        elif user_input == "think":
            if extra_datas["think_count_remain"] <= 0:
                input("你无法再思考了，做出决定吧.(按任意键继续)")
                extra_datas["turns"] -= 1
                continue
            content = input(
                f"你思索某个疑问(思考次数还剩{int(extra_datas['think_count_remain'])}次) 不输入内容以放弃思考 注意token消耗:\n:: ")
            if content.strip() == "":
                input("你放弃了思考.(按任意键继续)")
                extra_datas["turns"] -= 1
                continue
            GAME.think_go_game(content)
            extra_datas["think_count_remain"] -= 1
            extra_datas["turns"] -= 1
            input("思考完成，按任意键继续...")
            continue

        elif user_input == "help":
            extra_datas["turns"] -= 1
            print("可用指令：")
            print("exit: 退出游戏")
            print("inv: 查看道具")
            print("add_item: 添加道具")
            print("remove_item: 丢弃道具")
            print('summary:查看摘要')
            print('conclude_summary:手动总结当前摘要(不推荐)')
            print('save:保存游戏')
            print('load:读取游戏')
            print('new:新游戏')
            print('config:配置游戏')
            print('custom:自定义行动')
            print('think:思考/联想')
            print('attr:显示属性')
            print('ana_token:统计token数据')
            print('fix_item_name:修复道具名中的错误')
            print('show_init_resp:切换显示AI的原始相应与Token信息(debug)')
            input("按任意键继续...")
            continue
        else:
            init_turn_datas()

    clear_screen()
    print("游戏结束,下面是你本局游戏的摘要")
    print(f"你共进行了{extra_datas['turns']}轮游戏")
    for turn, it in enumerate(GAME.history_simple_summaries):
        print(f"第{turn+1}轮：{it}")
    input("按任意键退出...")


def main():
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
