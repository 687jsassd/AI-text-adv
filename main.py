"""
游戏主程序，用于进行游戏循环流程，进行显示等。
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

import sys
import os
from rich import print
from config import CustomConfig
from libs.animes_rich import GameTitle, console
from libs.logger import init_global_logger
from libs.practical_funcs import (clear_screen,
                                  COLOR_RESET,
                                  COLOR_RED,
                                  COLOR_YELLOW,
                                  generate_game_id,
                                  text_colorize,
                                  get_multiline_input
                                  )
from game_engine import GameEngine, VERSION, CommandManager


# 日志初始化
init_global_logger()


if getattr(sys, 'frozen', False):
    # 打包后：exe所在目录（处理符号链接/中文路径）
    exe_path = os.path.abspath(sys.executable)
    root_path = os.path.dirname(exe_path)
else:
    # 未打包：脚本所在目录
    script_path = os.path.abspath(__file__)
    root_path = os.path.dirname(script_path)
# 强制切换工作目录到程序根目录
os.chdir(root_path)


config = CustomConfig()


# 自定义行动的处理
def custom_action_func(game: GameEngine, skip_inputs=('cmd',)):
    """
    自定义行动
    """
    print(f"输入 /指令 以使用指令,如/cmd\n {COLOR_YELLOW}你决定{COLOR_RESET}")
    custom_action = get_multiline_input()
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
        # 有斜杠，执行确认一下
        if '/' in custom_action:
            confirm = input("输入了带/的语句,确定要视为自定义行动执行？[y/n]")
            if not confirm.strip() or confirm.strip().lower() != 'y':
                return ""
        # 没有任何一个中文，执行确认一下
        if not any('\u4e00' <= char <= '\u9fff' for char in custom_action):
            confirm = input("输入不含中文,确定要视为自定义行动执行？[y/n]")
            if not confirm.strip() or confirm.strip().lower() != 'y':
                return ""
        if custom_action.strip() == "":
            print("自定义行动取消")
            return ""
        game.go_game(custom_action)
    return custom_action


# 打印游戏历史记录
def print_all_history(game: GameEngine, back_range: int = 50):
    """
    打印游戏历史记录
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


def new_game(no_auto_load=False, renew_game=False):
    """
    主游戏逻辑
    """
    game_instance = GameEngine(config)

    def preference_view():
        return game_instance.extra_data.datas.get("preference_view_settings", {})
    no_save_again_sign = False

    def init_turn_datas():
        nonlocal no_save_again_sign
        no_save_again_sign = False

    commands = CommandManager.cmds

    clear_screen()
    print("等待读取..")

    # 尝试加载存档
    if not no_auto_load:
        loadsuccess, message = game_instance.load_game()
        print(message)
    else:
        loadsuccess = False

    if not loadsuccess:  # 新游戏逻辑
        if not renew_game:
            input("按任意键开始新游戏")
            game_instance.custom_config.config_game()
            game_instance = GameEngine(config)  # 防止部分配置未加载
            game_instance.game_id = input("为本局游戏命名(或留空随机)：\n::").strip()
            st_story = get_multiline_input('输入开局故事(留空随机）\n::')
            game_instance.anime_loader.start_animation(
                "spinner", message="*等待<世界>回应*")
            game_instance.start_game(st_story)
            game_instance.anime_loader.stop_animation()
            # 游戏ID
            if not game_instance.game_id:
                game_instance.game_id = generate_game_id()
        else:
            print("正在重新从头生成")
            game_instance = GameEngine(config)  # 防止部分配置未加载
            game_instance.game_id = generate_game_id()
            st_story = get_multiline_input('输入开局故事(留空随机）\n::')
            game_instance.anime_loader.start_animation(
                "spinner", message="*等待<世界>回应*")
            game_instance.start_game(st_story)
            game_instance.anime_loader.stop_animation()

    while True:
        clear_screen()
        print_all_history(game_instance)
        print(text_colorize(game_instance.current_description))
        game_instance.print_all_messages_await()
        wait_to_screen = []
        if preference_view().get("show_word_count", True):
            wait_to_screen.append(
                f"字数:{sum([len(it) for it in game_instance.history_descriptions])}")
        if preference_view().get("show_token_consume", True):
            wait_to_screen.append(
                f"RollToken/all:{game_instance.l_c_token+game_instance.l_p_token}/{game_instance.total_tokens}")
        if preference_view().get("show_fee", True):
            prompt_fee = game_instance.total_prompt_tokens * \
                game_instance.custom_config.get_current_provider()[
                    'price'][0] / 1000000
            completion_fee = game_instance.total_completion_tokens * \
                game_instance.custom_config.get_current_provider()[
                    'price'][1] / 1000000
            wait_to_screen.append(
                f"费用估计:I={prompt_fee:.3f} O={completion_fee:.3f} ALL={prompt_fee+completion_fee:.3f}")
        if preference_view().get("show_game_id", True):
            wait_to_screen.append(
                f"[{game_instance.game_id}]")
        if preference_view().get("show_game_version", True):
            wait_to_screen.append(
                f"Ver:{VERSION}")
        if preference_view().get("show_model_name", True):
            wait_to_screen.append(
                f"Model:{game_instance.custom_config.get_current_provider()['model']}")
        if preference_view().get("show_mod_count", True):
            wait_to_screen.append(
                f"{len(game_instance.prompt_manager.loaded_prompt_jsons)} mods loaded")

        if wait_to_screen:
            print(" | ".join(wait_to_screen))

        if preference_view().get("show_init_resp", False):
            print(game_instance.current_response)
            print(game_instance.get_token_stats())

        if not no_save_again_sign:
            game_instance.log_game_file(os.path.join(
                "logs", game_instance.game_id+f"_t{game_instance.extra_data.turns}.log"))
            game_instance.save_game()
            no_save_again_sign = True

        user_input = custom_action_func(game_instance, commands)

        if user_input == "exit":
            return 'exit'
        elif user_input == "new":
            return 'new_game'
        elif user_input == "renew":
            return 'renew_game'
        elif user_input in commands:  # pylint: disable=unsupported-membership-test
            CommandManager.run(  # pylint: disable=no-value-for-parameter
                user_input)
            input("按任意键继续..")
        elif user_input:
            game_instance.extra_data.turns += 1
            init_turn_datas()


def main():
    """
    主函数，游戏入口
    """
    # 如果是linux，就不放动画,避免权限不足的报错
    if sys.platform != "linux":
        game_title = GameTitle()
        game_title.show()
        input()  # 用于捕获标题时玩家按的回车
    no_auto_load = False
    renew_game = False
    while True:
        i = new_game(no_auto_load, renew_game)
        if i == 'exit':
            break
        elif i == 'new_game':
            no_auto_load = True
            renew_game = False
            continue
        elif i == 'renew_game':
            no_auto_load = True
            renew_game = True
            continue
        else:
            print("新的开始...")


if __name__ == "__main__":
    main()
