"""
游戏引擎
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 游戏引擎
import json
import time
import random
from math import atan
from collections import deque
from typing import Optional
import openai
from json_repair import repair_json
from config import CustomConfig
from libs.practical_funcs import (COLOR_CYAN,
                                  COLOR_RESET,
                                  COLOR_RED,
                                  COLOR_GREEN,
                                  COLOR_YELLOW,
                                  COLOR_BLUE,
                                  COLOR_MAGENTA)
from libs.prompt_manager import PromptManager
from libs.animes import SyncLoadingAnimation, probability_check_animation
from libs.extra_item_inventory import ItemInventory


class GameEngine:
    """
    游戏引擎
    """

    def __init__(self, custom_config: Optional[CustomConfig] = None):
        # 基础部分
        self.game_id = ''
        self.prompt_manager = PromptManager()
        self.current_response = ""
        # self.conversation_history = [] #因大小过大，暂时弃用
        self.history_descriptions = []  # 存储历史剧情
        self.history_choices = []  # 存储历史玩家选择
        self.history_simple_summaries = []
        self.current_description = "游戏开始"
        self.current_options = []
        self.current_game_status = "ongoing"
        self.summary_conclude_val = 24  # 当历史剧情超过24条时，对其进行压缩总结;所有摘要都会参与剧情生成.

        # Token统计部分
        self.total_prompt_tokens = 0
        self.l_p_token = 0
        self.total_completion_tokens = 0
        self.l_c_token = 0
        self.total_tokens = 0

        # 用户配置
        self.custom_config = custom_config or CustomConfig()

        # 玩家相关部分
        self.player_name = self.custom_config.player_name
        self.prompt_manager.iset_user_story(self.custom_config.player_story)

        # 动画
        self.anime_loader = SyncLoadingAnimation()

        # 拓展-玩家属性
        self.character_attributes = {
            "STR": 20.0,
            "DEX": 20.0,
            "INT": 20.0,
            "WIS": 20.0,
            "CHA": 20.0,
            "LUK": 20.0,
        }
        # 拓展-形势(-10 到 10)
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
        # 拓展-待显示消息的队列
        self.message_queue = deque()

        # 拓展-每轮token消耗
        self.token_consumes = []

        # 拓展-历史摘要总结的cooldown
        # 用于解决当压缩摘要占很多格子导致普通摘要没添加几个就总结时，间隔过短的问题。
        self.conclude_summary_cooldown = 10
        self.compressed_summary_textmin = 320  # 可认为为压缩摘要时的最小长度

        # 拓展-物品(用于存储物品,不参与剧情)
        self.item_system = ItemInventory()

        # 拓展-变量表
        self.variables = {
        }

    # 调用AI模型

    def call_ai(self, prompt: str):
        """
        调用AI模型
        """
        max_tokens = self.custom_config.max_tokens
        temperature = self.custom_config.temperature
        frequency_penalty = self.custom_config.frequency_penalty
        presence_penalty = self.custom_config.presence_penalty
        provider = self.custom_config.get_current_provider()
        model_name = provider["model"]
        api_key = provider["api_key"]
        base_url = provider["base_url"]
        try:
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
            # 构建请求参数字典
            params = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "frequency_penalty": frequency_penalty,
                "presence_penalty": presence_penalty,
                "timeout": openai.Timeout(
                    connect=10.0,
                    read=100.0,
                    write=20.0,
                    pool=5.0
                )
            }
            # 混元不支持frequency_penalty,presence_penalty,如果模型是混元，去掉这两条
            if "hunyuan" in model_name:
                del params["frequency_penalty"]
                del params["presence_penalty"]
                params["extra_body"] = {}
            # 调用API
            response = client.chat.completions.create(**params)
            # 记录token使用情况
            if hasattr(response, 'usage'):
                self.total_prompt_tokens += response.usage.prompt_tokens
                self.l_p_token = response.usage.prompt_tokens
                self.total_completion_tokens += response.usage.completion_tokens
                self.l_c_token = response.usage.completion_tokens
                self.total_tokens += response.usage.total_tokens
                print(
                    f"\nToken消耗 - 提示词: {response.usage.prompt_tokens}, 输出: {response.usage.completion_tokens}, 总计: {response.usage.total_tokens}")
            self.current_response = response.choices[0].message.content
            if self.current_response:
                # 有响应内容时直接返回
                return self.current_response
            else:
                # 此时，可能和reason部分整合到了一起，进行分离
                self.current_response = response.choices[0].message.reasoning_content
                if not self.current_response:
                    raise ValueError("AI模型返回空响应")
                start_idx = self.current_response.find('{')
                end_idx = self.current_response.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    # 提取完整的JSON部分
                    self.current_response = self.current_response[start_idx:end_idx+1]
                    return self.current_response
        except openai.APITimeoutError:
            self.anime_loader.stop_animation()
            print("相应超时 - 检查网络或者向我们反馈?")
            print(f"当前配置:model={model_name},base_url={base_url}")
            input("按任意键继续")
            return None
        except (openai.OpenAIError, ValueError) as e:
            self.anime_loader.stop_animation()
            print(f"调用AI模型时出错: {e}")
            input("按任意键继续")
            return None

    # 解析AI响应

    def parse_ai_response(self, response: str):
        """
        解析AI响应
        """
        json_content = "未解析"
        # 把中文的引号和冒号、逗号替换为英文
        response = response.replace("“", '"').replace(
            "”", '"').replace("：", ":").replace('，', ',')
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                # 提取完整的JSON部分
                json_content = response[start_idx:end_idx+1]
            else:
                # 如果找不到完整的花括号对，使用原始响应
                json_content = response

            json_response = json.loads(repair_json(json_content))
            while not isinstance(json_response, dict):
                print(f"未能解析JSON响应??\n {json_response}")
                if isinstance(json_response, list):
                    print("列表类型？尝试第一个元素")
                    json_response = json_response[0]
                elif isinstance(json_response, str):
                    print("字符串类型？尝试解析为JSON")
                    json_response = json.loads(json_response)
                else:
                    self.anime_loader.stop_animation()
                    input("解析JSON失败！")
                    return None
            try:
                # 检查是否有指令(commands),有则执行
                if json_response.get("commands"):
                    commands = json_response.get(
                        "commands", [])
                    self.handle_command(commands)
            except (ValueError, TypeError) as e:
                print(f"解析指令时出错: {e}")
                input("已跳过指令处理,按任意键继续解析\n")

            self.current_options = json_response.get("options", [])
            if not self.current_options and not self.prompt_manager.is_no_options:
                input(f"未能解析选项?? 按键重试 {json_response}\n")
                return None
            elif self.prompt_manager.is_no_options:
                self.current_options = [{
                    "id": 0,
                    "text": "为跳过无选项模式，请使用custom自由输入行动以经过本轮",
                    "type": "must",
                    "main_factor": "LUK",
                    "difficulty": 99999,
                    "base_probability": 0.0,
                    "next_preview": "",
                }]
            self.current_description = json_response.get("description", "")
            if not self.current_description.strip():
                input(f"未能解析描述?? 按键重试 {json_response}\n")
                return None
            if self.current_description:
                self.history_simple_summaries.append(
                    json_response.get("summary", ""))
            # 解析选项({'id': 1, 'text': '选项1', 'type': 'check','main_factor':'STR','base_probability': 0.5,'next_preview': '下一个预览'})
            tmp = []
            for option in self.current_options:
                try:
                    tmp.append({
                        "id": int(option.get("id", 0)),
                        "text": option.get("text", ""),
                        "type": option.get("type", "normal"),
                        "main_factor": option.get("main_factor", ""),
                        "difficulty": int(option.get("difficulty", 0)),
                        # 基础概率作为初始概率
                        "base_probability": option.get("base_probability", 0.0),
                        "probability": option.get("base_probability", 0.0),
                        "next_preview": option.get("next_preview", ""),
                    })
                except (ValueError, TypeError) as e:
                    print(f"解析某选项时出错: {e},选项: {option}")
                    input("已跳过该选项,按任意键继续解析\n")

            self.current_options = tmp
            # 规范化选项，去除不是check但有probability的选项的probability条目
            for option in self.current_options:
                if option["type"] != "check":
                    del option["probability"]
                if option.get("probability") and option["probability"] in [0, 0.0, "0", "0.0", "", " "]:
                    del option["probability"]
                if option.get("probability"):
                    option["probability"] = float(option["probability"])
                if option["type"] == "must":
                    if not option.get("difficulty"):
                        option["difficulty"] = 0
                    if not option.get("main_factor"):
                        option["main_factor"] = "LUK"
            return json_response
        except (ValueError, json.JSONDecodeError) as e:
            self.anime_loader.stop_animation()
            print(f"解析AI响应时出错: {e}")
            print("响应内容:")
            print(response)
            print("解析内容:")
            print(json_content)
            input("按任意键继续")
            return None

    # 指令处理
    def handle_command(self, commands: list):
        """
        处理指令
        """
        for command in commands:
            if not isinstance(command, dict):
                self.anime_loader.stop_animation()
                input(f'注意：指令{command}出错！\n\n{commands}\n')
                continue
            command_type = command.get("command")
            value = command.get("value")
            if command_type == "add_item":
                if value:
                    item_info = value  # 是字典
                    if isinstance(item_info, dict):
                        item_name, item_desc = list(item_info.keys())[
                            0], list(item_info.values())[0]
                    else:
                        item_name, item_desc = item_info, '无描述'
                        # 对错误地将字典转换为字符串而作为物品名的物品进行修复
                        if item_name.startswith('{') and item_name.endswith('}'):
                            item_name = item_name[1:-1]
                            # 以:进行分割，获取道具名和道具描述
                            item_name, item_desc = item_name.split(':')
                            # 去除首尾可能的引号
                            item_name = item_name.strip('"').strip("'")
                            item_desc = item_desc.strip('"').strip("'")
                    # 调用修复函数，继续深层修复
                    self.item_system.fix_item_name_error()
                    # 如果已经有这个道具就不添加
                    if item_name in self.item_system.inventory:
                        return
                    self.item_system.inventory[item_name] = item_desc
                    # self.history_simple_summaries.append(
                    #    f"{self.custom_config.player_name}获得了道具{item_name}")
                    self.message_queue.append(
                        f"{COLOR_GREEN}你获得了道具{item_name}{COLOR_RESET}")
                else:
                    print(f"[警告]:添加道具时未提供道具信息或者信息格式不正确{command}")
            elif command_type == "remove_item":
                if value:
                    if value in self.item_system.inventory:
                        del self.item_system.inventory[value]
                        # self.history_simple_summaries.append(
                        #    f"{self.custom_config.player_name}失去了道具{value}")
                        self.message_queue.append(
                            f"{COLOR_RED}你失去了道具{value}{COLOR_RESET}")
                    else:
                        print(f"[警告]:移除时玩家没有道具【{value}】{command}")
                else:
                    print(f"[警告]:移除道具时未提供道具信息{command}")
            elif command_type == "change_attr":
                # value: 对象{"属性名": "属性值"}，属性名为力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA中的一个，属性值可以是负数。
                if value:
                    if not isinstance(value, dict) or len(value) != 1:
                        print("[警告]:改变属性时提供的信息格式错误")
                        continue
                    # 解析属性名和属性值
                    attribute_name, attribute_value = list(value.keys())[
                        0], float(list(value.values())[0])
                    desc = command.get("desc", "")
                    if attribute_name in self.character_attributes:
                        self.character_attributes[attribute_name] += attribute_value
                        # self.history_simple_summaries.append(
                        #    f"{self.custom_config.player_name}的{attribute_name}属性{"因为"+desc+"而" if desc else ""}改变了{attribute_value}")
                        change_message = f"{self.custom_config.player_name}的属性{attribute_name}{"因为"+desc+"而" if desc else ""}变动{attribute_value:+}(总{self.character_attributes[attribute_name]})"
                        change_message = COLOR_GREEN + \
                            f"{change_message}"+COLOR_RESET if attribute_value > 0 else COLOR_RED + \
                            f"{change_message}"+COLOR_RESET
                        self.message_queue.append(
                            change_message)
                    else:
                        print(f"[警告]:改变属性时玩家没有属性【{value}】{command}")
                else:
                    print(f"[警告]:改变属性时未提供属性信息{command}")
            elif command_type == "change_situation":
                if value:
                    if isinstance(value, str) and ((value.startswith(("+", "-")) and value[1:].isdigit()) or value.isdigit()):
                        value = int(value)
                    if not isinstance(value, int):
                        print(f"[警告]:改变形势值时提供的信息格式错误{command}")
                        continue
                    self.situation += value
                    self.situation = max(0, min(self.situation, 10))
                else:
                    print(f"[警告]:改变形势值时未提供形势值信息{command}")
            elif command_type == "gameover":
                self.current_game_status = "failure"
                self.anime_loader.stop_animation()
                self.anime_loader.start_animation(
                    "dot", message=COLOR_RED+"游戏结束"+COLOR_RESET)
                time.sleep(4)
                self.anime_loader.stop_animation()
                break
            elif command_type == "set_var":
                if value:
                    print(f"[调试]:设置变量时提供的信息{value}")
                    if not isinstance(value, dict):
                        print(f"[警告]:设置变量时提供的信息格式错误{command}")
                        continue
                    # 解析变量名和变量值(为多变量设置提供支持)
                    for var_name, var_value in value.items():
                        self.variables[var_name] = var_value
                else:
                    print(f"[警告]:设置变量时未提供变量信息{command}")
            elif command_type == "del_var":
                if value:
                    # 解析变量名
                    var_name = str(value)
                    if var_name in self.variables:
                        del self.variables[var_name]
                    else:
                        print(f"[警告]:删除变量时玩家没有变量【{var_name}】{command}")
                else:
                    print(f"[警告]:删除变量时未提供变量信息{command}")

    # 开始游戏

    def start_game(self, st_story: str = ''):
        """
        开始游戏（第一轮）
        """
        init_prompt = self.prompt_manager.get_initial_prompt(
            self.player_name,
            st_story,
            self.custom_config.get_custom_prompt(),
            self.item_system.get_inventory_text_for_prompt(),
            self.get_attribute_text())
        # self.conversation_history.append(
        #    {"role": "user", "content": init_prompt})
        ai_response = self.call_ai(init_prompt)
        while not ai_response:
            input('无响应内容？任意键重试\n')
            ai_response = self.call_ai(init_prompt)
        if ai_response:
            ok_sign = self.parse_ai_response(ai_response)
            while not ok_sign:
                self.anime_loader.stop_animation()
                input(f"解析失败，按任意键重试.[注意Token消耗{self.total_tokens}]\n")
                ai_response = self.call_ai(init_prompt)
                if ai_response:
                    ok_sign = self.parse_ai_response(ai_response)
        # self.conversation_history.append(
        #    {"role": "assistant", "content": ai_response})
        self.history_descriptions.append(self.current_description)
        self.token_consumes.append(self.l_p_token+self.l_c_token)

    def go_game(self, option_id, is_custom=False, is_prompt_concluding=False, is_skip_csmode_action_modify=False):
        """
        进行游戏（后续轮次）
        """
        if len(self.history_simple_summaries) > self.summary_conclude_val and not is_prompt_concluding and self.conclude_summary_cooldown < 1:
            self.go_game(option_id, is_custom, True)
        prompt = ""
        if is_prompt_concluding:
            self.conclude_summary()
            return 0
        if is_custom:
            selected_option = {"id": 999,
                               "text": option_id, "type": "normal", "next_preview": ""}
            if not is_skip_csmode_action_modify:
                # 调用get_action_mode_prompt获取自定义动作的类型等修饰后选项的提示词，对选项进行修饰
                custom_prompt = self.prompt_manager.get_action_mode_prompt(
                    self.player_name,
                    self.current_description,
                    '\n'.join(
                        [i for i in self.history_simple_summaries[-7:] if i]),
                    option_id,
                    self.item_system.get_inventory_text_for_prompt(),
                    self.get_attribute_text(),
                    self.get_situation_text(),
                    self.custom_config.get_custom_prompt(),
                    self.get_vars_text())
                # 手动解析response，获取type、main_factor、difficulty、base_probability、next_preview并赋予给selected_option
                self.anime_loader.stop_animation()
                self.anime_loader.start_animation(
                    "dot", message="等待选项修饰")
                response = self.call_ai(custom_prompt)
                self.token_consumes[-1] += self.l_p_token+self.l_c_token
                self.anime_loader.stop_animation()
                ok_sign = False
                if response:
                    while not ok_sign:
                        try:
                            if not response:
                                raise ValueError("AI响应为空")
                            resp_dict = json.loads(repair_json(response))
                            selected_option["type"] = resp_dict.get(
                                "type", "normal")
                            selected_option["main_factor"] = resp_dict.get(
                                "main_factor", "LUK")
                            selected_option["difficulty"] = resp_dict.get(
                                "difficulty", 0)
                            selected_option["base_probability"] = resp_dict.get(
                                "base_probability", 0.3)
                            selected_option["probability"] = selected_option["base_probability"]
                            # 添加标记，以绕过门槛检测
                            selected_option["extra"] = "custom_action"
                            ok_sign = True
                        except (ValueError, json.JSONDecodeError) as e:
                            self.anime_loader.stop_animation()
                            print(f"解析AI响应时出错: {e}")
                            input(
                                f"按任意键重试,注意token消耗(本次){self.l_c_token+self.l_p_token}")
                            print("正在重试...")
                            response = self.call_ai(custom_prompt)
        else:
            selected_option = next(
                (opt for opt in self.current_options if int(opt["id"]) == int(option_id)), None)
        if not selected_option:
            print("无效的选项ID")
            return -1
        if selected_option:
            if selected_option["type"] == "must" and selected_option.get("extra", "") != "custom_action":
                if self.character_attributes.get(selected_option["main_factor"], 0) < selected_option["difficulty"]:
                    print(
                        f"不满足选项要求[{selected_option['main_factor']}≥{selected_option['difficulty']}]")
                    return -1
            elif selected_option["type"] == "must":
                # 对于自定义操作，我们根据是否达到门槛添加是否成功标识即可，不直接return
                if self.character_attributes.get(selected_option["main_factor"], 0) >= selected_option["difficulty"]:
                    selected_option["text"] += COLOR_GREEN + \
                        "<满足行动条件>"+COLOR_RESET
                else:
                    selected_option["text"] += COLOR_RED + \
                        "<不满足行动条件>"+COLOR_RESET
            # 处理并检定概率(两次判定:第一次就成功：大成功；第二次:小成功；)
            if selected_option["type"] == "check":
                final_chance_mark = False
                target_prob = selected_option["probability"] + \
                    (self.character_attributes.get(
                        selected_option["main_factor"], 0)-selected_option["difficulty"]) * 3 / 2000
                # 计算形势n影响(若n为正，几率增加0.01*2.2*n**1.25,否则减少0.04*n)
                situation_factor = self.situation
                if situation_factor > 0:
                    target_prob += 0.01*2.2*situation_factor**1.25
                else:
                    target_prob += 0.04*situation_factor
                # 检定成功概率(第一次判定)
                success_prob = random.uniform(0, 1)
                print("正在进行第一次检定")
                probability_check_animation(
                    success_prob,
                    target_prob=max(target_prob*0.65, 0.01),
                    duration=2
                )
                if success_prob < max(target_prob*0.65, 0.01):
                    # 成功
                    selected_option["text"] += COLOR_GREEN + \
                        "<检定大成功!>"+COLOR_RESET
                    print(COLOR_GREEN+"检定大成功! "+COLOR_RESET)
                else:
                    print("正在进行第二次检定")
                    new_success_prob = random.uniform(0, 1)
                    cur_min = min(new_success_prob, success_prob)
                    probability_check_animation(
                        new_success_prob,
                        target_prob=target_prob,
                        duration=3
                    )
                    if new_success_prob < target_prob:
                        # 成功
                        selected_option["text"] += COLOR_YELLOW + \
                            "<检定小成功>"+COLOR_RESET
                    else:
                        # 如果自己的主属性>选项要求+5,则差值的百分比的概率获得最后一次机会
                        # 目标值是差值的百分比
                        if self.character_attributes.get(
                                selected_option["main_factor"], 0)-selected_option["difficulty"] > 5:
                            last_chance_prob = random.uniform(0, 1)
                            last_target = (self.character_attributes.get(
                                selected_option["main_factor"], 0)-selected_option["difficulty"]-5) / 100
                            if last_chance_prob < last_target:
                                print(COLOR_MAGENTA+"最后机会"+COLOR_RESET)
                                last_chance_prob = random.uniform(0, 1)
                                probability_check_animation(
                                    last_chance_prob,
                                    target_prob=last_target,
                                    duration=2.5
                                )
                                if last_chance_prob < last_target:
                                    selected_option["text"] += COLOR_MAGENTA + \
                                        "<检定小成功>"+COLOR_RESET
                                    final_chance_mark = True
                                else:
                                    cur_min = min(last_chance_prob, cur_min)

                        if not final_chance_mark and cur_min >= 0.20+target_prob:
                            selected_option["text"] += COLOR_RED + \
                                "<检定大失败>"+COLOR_RESET
                        elif not final_chance_mark:
                            selected_option["text"] += COLOR_RED + \
                                "<检定小失败>"+COLOR_RESET

            self.history_choices.append(
                COLOR_BLUE+selected_option["text"]+COLOR_RESET)

            prompt = self.prompt_manager.get_continuation_prompt(
                self.player_name,
                self.current_description,
                "\n".join(
                    [str(s) for s in self.history_simple_summaries[:-1] if s is not None]),
                selected_option["text"],
                selected_option["next_preview"],
                self.custom_config.get_custom_prompt(),
                self.item_system.get_inventory_text_for_prompt(),
                self.get_attribute_text(),
                self.get_situation_text(),
                self.get_vars_text())

            # self.conversation_history.append(
            #    {"role": "user", "content": prompt})

        if not prompt:
            raise ValueError("prompt为空")
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation("spinner", message="等待<世界>回应")
        ai_response = self.call_ai(prompt)
        if ai_response:
            ok_sign = self.parse_ai_response(ai_response)
            while not ok_sign:
                input(f"解析失败，按任意键重试.[注意Token消耗{self.total_tokens}]")
                ai_response = self.call_ai(prompt)
                if ai_response:
                    ok_sign = self.parse_ai_response(ai_response)
        self.token_consumes.append(self.l_p_token+self.l_c_token)
        self.conclude_summary_cooldown -= 1

        self.anime_loader.stop_animation()  # type:ignore
        # self.conversation_history.append(
        #    {"role": "assistant", "content": ai_response})
        self.history_descriptions.append(self.current_description)
        return 0

    def think_go_game(self, think_context):
        """玩家思考游戏中的情况"""
        think_success_or_not = self.probability_check(
            0.2 + 0.6873 * atan(0.02345 * self.character_attributes.get("INT", 10)), is_enable_double_check=True)
        if think_success_or_not == 3:
            think_context += "(大成功)"
        elif think_success_or_not == 1:
            think_context += "(小成功)"
        elif think_success_or_not == -1:
            think_context += "(小失败)"
        elif think_success_or_not == -3:
            think_context += "(大失败)"
        prompt = self.prompt_manager.get_think_prompt(
            think_context,
            self.player_name,
            self.current_description,
            "\n".join(
                [str(s) for s in self.history_simple_summaries[:-1] if s is not None]),
            self.item_system.get_inventory_text_for_prompt(),
            self.get_situation_text())
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation("dot", message="思考中")
        res = self.call_ai(prompt)
        while not res:
            self.anime_loader.stop_animation()
            input(f"AI响应失败，按任意键重试.[注意Token消耗{self.total_tokens}]\n")
            res = self.call_ai(prompt)
        self.current_description += "\n\n" + \
            COLOR_BLUE+f"[思考:{think_context}] "+COLOR_RESET+res
        self.history_descriptions[-1] = self.current_description
        self.token_consumes[-1] += self.l_p_token+self.l_c_token
        self.anime_loader.stop_animation()  # type:ignore
        return 0

    def get_token_stats(self):
        """获取token统计信息"""
        return {
            "本次输入消耗": self.l_p_token,
            "本次生成消耗": self.l_c_token,
            "本轮总消耗token": self.l_p_token+self.l_c_token,
            "全局输入token消耗量": self.total_prompt_tokens,
            "全局生成token消耗量": self.total_completion_tokens,
            "全局总token消耗量": self.total_tokens,
        }

    def get_attribute_text(self, colorize=False):
        """获取当前属性列表的文本描述"""
        if not self.character_attributes:
            return "玩家当前没有属性"
        if colorize:
            ret = f"""
            当前属性
            {COLOR_RED}力量 STR:{self.character_attributes["STR"]}{COLOR_RESET}
            {COLOR_GREEN}敏捷 DEX:{self.character_attributes["DEX"]}{COLOR_RESET}
            {COLOR_BLUE}智力 INT:{self.character_attributes["INT"]}{COLOR_RESET}
            {COLOR_CYAN}感知 WIS:{self.character_attributes["WIS"]}{COLOR_RESET}
            {COLOR_MAGENTA}魅力 CHA:{self.character_attributes["CHA"]}{COLOR_RESET}
            {COLOR_YELLOW}幸运 LUK:{self.character_attributes["LUK"]}{COLOR_RESET}
            """
            return ret
        return "玩家属性：\n" + "\n".join([f"{attr}: {value}" for attr, value in self.character_attributes.items()])

    def get_situation_text(self, add_numbers=False):
        """获取当前形势的文本描述"""
        if self.situation > 10:
            self.situation = 10
        if self.situation < -10:
            self.situation = -10
        for tp, texts in self.situation_text.items():
            if tp[0] <= self.situation < tp[1]:
                if add_numbers:
                    return f"当前的形势值:{self.situation}({texts})"
                return texts

    def get_vars_text(self):
        """获取当前变量的文本描述"""
        if not self.variables:
            return "当前没有变量"
        text = "游戏变量表(变量名:值)：\n"
        for var_name, var_value in self.variables.items():
            text += f"{var_name}:{var_value}\n"
        return text

    def log_game(self, log_file: str):
        """记录游戏信息，处理Unicode编码问题"""
        # def safe_json_dump(data, file_handle):
        #    """安全地序列化并写入JSON数据"""
        #    try:
        #        json_str = json.dumps(data, ensure_ascii=False)
        #        file_handle.write(json_str + "\n")
        #    except (UnicodeEncodeError, UnicodeDecodeError):
        #        # 如果遇到编码问题，使用ASCII安全模式
        #        json_str = json.dumps(data, ensure_ascii=True)
        #        file_handle.write(json_str + "\n")
        #    except Exception as e:
        #        # 记录错误信息
        #        error_data = {
        #            "error": f"序列化失败: {str(e)}", "data_type": str(type(data))}
        #        file_handle.write(json.dumps(
        #            error_data, ensure_ascii=True) + "\n")
        # 使用内置open函数，设置errors='replace'处理编码问题
        # with open(log_file, "w", encoding="utf-8", errors="replace") as f:
        #    safe_json_dump({"player_name": self.player_name}, f)
        #    safe_json_dump({"Time": CURRENT_TIME}, f)
        #    safe_json_dump({"token_usage": self.get_token_stats()}, f)

        #    for entry in self.conversation_history:
        #        safe_json_dump(entry, f)

        # 新文件导出剧情及玩家对应的选择
        narrative_file = log_file.replace(".log", "_narrative.log")
        with open(narrative_file, "w", encoding="utf-8", errors="replace") as f:
            for desc, choice in zip(self.history_descriptions, self.history_choices):
                # 清理文本
                def clean_text(text):
                    if text is None:
                        return ""
                    if isinstance(text, str):
                        return text
                    return str(text)

                clean_desc = clean_text(desc)
                clean_choice = clean_text(choice)
                f.write(f"{clean_desc}\n{clean_choice}\n\n")

    def print_all_messages_await(self):
        """打印所有待显示消息"""
        while self.message_queue:
            print(self.message_queue.popleft())

    def probability_check(self,
                          target: float,
                          is_enable_normal: bool = False,
                          normal_range_factor: float = 0.1,
                          is_enable_double_check: bool = False,
                          first_check_factor: float = 0.65,
                          second_check_factor: float = 1.00,
                          allow_base_first_success: bool = True,
                          big_failure_prob_addon: float = 0.20,
                          is_enable_final_chance: bool = False,
                          final_chance_prob: float = 0.05,
                          final_chance_target: float = 0.05,

                          ):
        """
        概率判定函数
        target:目标值 0-1
        is_enable_normal: 是否允许"不成功也不失败"的情况
        normal_range_factor: 上述情况所占范围系数(为目标值左右范围)
        is_enable_double_check: 是否启用二次判定,如不启用则只判定一次
            若启用，则返回值分别为3,1,-1或-3，分别表示大成功、小成功、小失败、大失败
            否则，返回2或-2，表示成功、失败
        first_check_factor:二次判定中第一次判定的目标值系数
        second_check_factor二次判定中第二次判定的目标值系数
        allow_base_first_success: 是否允许第一次判定中保底有1%的概率
        big_failure_prob_addon: 大失败当判定中最小值大于目标值多少才会触发
        is_enable_final_chance: 是否启用最后机会
        final_chance_prob: 最后机会触发概率
        final_chance_target: 最后机会的目标值
        """
        result = 0
        if is_enable_double_check:
            first_result, second_result = 0, 0
            first_target = target * first_check_factor
            if allow_base_first_success:
                first_target = max(first_target, 0.01)
            rand_first = random.uniform(0, 1)
            print("正在进行第一次检定")
            probability_check_animation(
                rand_first,
                target_prob=first_target,
                duration=2
            )
            if rand_first < first_target:
                first_result = 1

            second_target = target * second_check_factor
            if allow_base_first_success:
                second_target = max(second_target, 0.01)
            rand_second = random.uniform(0, 1)
            print("正在进行第二次检定")
            probability_check_animation(
                rand_second,
                target_prob=second_target,
                duration=2
            )
            if rand_second < second_target:
                second_result = 1

            if first_result == 1:
                return 3  # 第一次就成功，则大成功

            if second_result == 1:
                return 1  # 第二次才成功，则小成功

            if is_enable_normal and abs(rand_first - target) < normal_range_factor:
                return 0  # 不成功不失败

            if min(rand_first, rand_second) < target + big_failure_prob_addon:
                result = -1  # 小失败

            else:
                result = -3  # 大失败

        else:
            rand = random.uniform(0, 1)
            probability_check_animation(
                rand,
                target_prob=target,
                duration=2
            )
            if rand < target:
                return 2  # 成功

            if is_enable_normal and abs(rand - target) < normal_range_factor:
                return 0  # 不成功不失败

            else:
                result = -2  # 失败

        # 最后机会
        # 随机数决定是否启用
        if not is_enable_final_chance:
            return result

        enable_final_chance_prob = random.uniform(0, 1)
        if enable_final_chance_prob < final_chance_prob:
            final_chance_rand = random.uniform(0, 1)
            probability_check_animation(
                final_chance_rand,
                target_prob=final_chance_target,
                duration=2
            )
            if final_chance_rand < final_chance_target:
                return 1  # 小成功
        return result

    def is_use_item_ok(self, focus_item: str, player_move: str, target: str = ""):
        """判断使用物品是否合理"""

        prompt = self.prompt_manager.get_use_item_prompt(
            player_name=self.player_name,
            cur_desc=self.current_description,
            player_move=player_move,
            focus_item=focus_item,
            focus_item_desc=self.item_system.inventory[focus_item],
            target=target
        )
        response = self.call_ai(prompt)
        if not response:
            input('注意：AI未给出响应')
            return True
        try:
            is_ok = json.loads(response)["is_valid"] == 1
        except (json.JSONDecodeError, KeyError, ValueError):
            is_ok = False
        self.token_consumes[-1] += self.l_p_token+self.l_c_token
        return is_ok

    def conclude_summary(self):
        """
        总结摘要，清理无用物品和变量
        """
        def phase_summary(resp):
            try:
                r = json.loads(repair_json(resp))
                summ = r["summary"]
                rmv_item = r["useless_items"]
                rmv_var = r["useless_vars"]
                return 1, summ, rmv_item, rmv_var
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[警告]:总结历史剧情时解析json失败{resp}，错误信息：{e}")
                return 0, "", [], []

        # 当所有摘要都经过了压缩，我们采取稀释旧摘要策略
        if not any(i and len(i) < self.compressed_summary_textmin for i in self.history_simple_summaries[:-1]):
            prompt = self.prompt_manager.get_summary_prompt(
                '\n'.join(
                    [str(s) for s in self.history_simple_summaries[:10] if s is not None]),
                self.item_system.get_inventory_text_for_prompt(),
                self.get_vars_text())
            self.anime_loader.stop_animation()
            self.anime_loader.start_animation(
                "dot", message=COLOR_YELLOW+"正在总结历史剧情 并清理无用信息"+COLOR_RESET)
            tmp = self.custom_config.max_tokens
            self.custom_config.max_tokens = 20480
            summary = self.call_ai(prompt)
            self.custom_config.max_tokens = tmp
            self.anime_loader.stop_animation()
            ok_sign, summ, rmv_item, rmv_var = phase_summary(summary)
            while not ok_sign:
                input(f"[警告]:总结历史剧情时解析json失败{summary}，按任意键重试")
                summary = self.call_ai(prompt)
                ok_sign, summ, rmv_item, rmv_var = phase_summary(summary)
            self.history_simple_summaries = [
                summ]+self.history_simple_summaries[10:]
            for item in rmv_item:
                self.iremove_item(item)
            for var in rmv_var:
                self.idel_var(var)
            self.conclude_summary_cooldown = 10
            self.token_consumes[-1] += self.l_p_token+self.l_c_token
            return 0

        # 否则，我们只总结新摘要，形成压缩摘要
        prompt = self.prompt_manager.get_summary_prompt(
            "\n".join(
                [i for i in self.history_simple_summaries if i and len(i) < self.compressed_summary_textmin]),
            self.item_system.get_inventory_text_for_prompt(),
            self.get_vars_text())
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation(
            "dot", message=COLOR_YELLOW+"正在总结历史剧情 并清理无用信息"+COLOR_RESET)
        tmp = self.custom_config.max_tokens
        self.custom_config.max_tokens = 2048
        summary = self.call_ai(prompt)
        self.custom_config.max_tokens = tmp
        self.anime_loader.stop_animation()
        ok_sign, summ, rmv_item, rmv_var = phase_summary(summary)
        while not ok_sign:
            input(f"[警告]:总结历史剧情时解析json失败{summary}，按任意键重试")
            summary = self.call_ai(prompt)
            ok_sign, summ, rmv_item, rmv_var = phase_summary(summary)
        self.history_simple_summaries = [
            i for i in self.history_simple_summaries if i and len(i) >= self.compressed_summary_textmin] + [summ]
        for item in rmv_item:
            self.iremove_item(item)
        for var in rmv_var:
            self.idel_var(var)
        self.conclude_summary_cooldown = 10
        self.token_consumes[-1] += self.l_p_token+self.l_c_token
        return 0

    def iremove_item(self, item: str):
        """
        构造命令，从物品列表中移除物品
        """
        commands = [{
            "command": "remove_item",
            "value": item
        }]
        self.handle_command(commands)

    def idel_var(self, var: str):
        """
        构造命令，从变量列表中移除变量
        """
        commands = [{
            "command": "del_var",
            "value": var
        }]
        self.handle_command(commands)
