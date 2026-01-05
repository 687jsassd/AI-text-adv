"""
游戏引擎
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 游戏引擎
import json
import os
import time
import logging
import gzip
from math import atan
from collections import deque
from typing import Optional
import openai
from rich import print
from json_repair import repair_json
from config import CustomConfig, CURRENT_TIME
from libs.practical_funcs import (COLOR_RESET,
                                  COLOR_RED,
                                  COLOR_GREEN,
                                  COLOR_YELLOW,)
from libs.prompt_manager import PromptManager
from libs.animes import SyncLoadingAnimation
from libs.extra_item_inventory import ItemInventory
from libs.extra_attributes import Attributes
from libs.extra_situation import Situation
from libs.formula_and_checks import GameFormulas, GameChecks
from libs.logger import log_exceptions


logger = logging.getLogger(__name__)

AnimeLoader = SyncLoadingAnimation()


class GameEngine:
    """
    游戏引擎
    """

    def __init__(self, custom_config: Optional[CustomConfig] = None):
        # 基础部分
        self.game_id = ''
        self.prompt_manager = PromptManager()
        self.current_response = ""
        self.conversation_history = []
        self.history_descriptions = []  # 存储历史剧情
        self.history_choices = []  # 存储历史玩家选择
        self.history_simple_summaries = []
        self.current_description = "游戏开始"
        self.current_options = []
        self.current_game_status = "ongoing"

        # 摘要压缩部分
        self.summary_conclude_val = 24  # 当历史剧情超过24条时，对其进行压缩总结;所有摘要都会参与剧情生成.
        self.conclude_summary_cooldown = 10
        self.compressed_summary_textmin = 320  # 可认为为压缩摘要时的最小长度

        # Token统计部分
        self.total_prompt_tokens = 0
        self.l_p_token = 0
        self.total_completion_tokens = 0
        self.l_c_token = 0
        self.total_tokens = 0
        self.token_consumes = []

        # 用户配置
        self.custom_config = custom_config or CustomConfig()
        self.player_name = self.custom_config.player_name
        self.prompt_manager.iset_user_story(self.custom_config.player_story)

        # 动画
        self.anime_loader = AnimeLoader

        # 拓展
        self.attr_system = Attributes()  # 属性系统
        self.item_system = ItemInventory()  # 物品系统
        self.situation_system = Situation()  # 形势系统
        self.check_system = GameChecks()  # 检定系统  (不参与持久化，待完善，TODO:检定系统)
        self.formula_system = GameFormulas()  # 各公式  (不参与持久化，待完善，TODO:公式系统)

        # 拓展-待显示消息的队列
        self.message_queue = deque()

        # 拓展-游戏变量表
        self.variables = {
        }

    # 基础-调用AI模型
    @log_exceptions(logger)
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
            logger.debug("调用AI模型: %s, 参数: %s", model_name, params)
            response = client.chat.completions.create(**params)
            logger.debug("AI模型返回: %s", response)
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
            self.conversation_history.append(
                {"role": "user", "content": prompt})
            self.conversation_history.append(
                {"role": "assistant", "content": self.current_response})
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
            logger.error("相应超时")
            print("相应超时 - 检查网络或者向我们反馈?")
            print(f"当前配置:model={model_name},base_url={base_url}")
            input("按任意键继续")
            return None
        except (openai.OpenAIError, ValueError) as e:
            self.anime_loader.stop_animation()
            logger.error("调用AI模型时出错: %s", e)
            print(f"调用AI模型时出错: {e}")
            input("按任意键继续")
            return None

    # 基础-解析AI响应
    @log_exceptions(logger)
    def parse_ai_response(self, response: str):
        """
        解析AI响应
        """
        logger.debug("解析AI响应: %s", response)
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
                logger.warning("未能解析JSON响应??\n %s", json_response)
                if isinstance(json_response, list):
                    logger.warning("列表类型？尝试第一个元素")
                    json_response = json_response[0]
                elif isinstance(json_response, str):
                    logger.warning("字符串类型？尝试解析为JSON")
                    json_response = json.loads(json_response)
                else:
                    self.anime_loader.stop_animation()
                    logger.error("解析JSON失败！")
                    return None
            try:
                # 检查是否有指令(commands),有则执行
                if json_response.get("commands"):
                    commands = json_response.get(
                        "commands", [])
                    self.handle_command(commands)
            except (ValueError, TypeError) as e:
                logger.error("解析指令时出错: %s", e)

            self.current_options = json_response.get("options", [])
            if not self.current_options and not self.prompt_manager.is_no_options:
                logger.warning("未能解析选项??\n %s", json_response)
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
                logger.warning("未能解析描述??\n %s", json_response)
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
                    logger.error("解析某选项时出错: %s,选项: %s", e, option)
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
            logger.error("解析AI响应时出错: %s , 响应内容: %s", e, response)
            print(f"解析AI响应时出错: {e}")
            print("响应内容:")
            print(response)
            input("按任意键继续")
            return None

    # 基础-指令处理
    @log_exceptions(logger)
    def handle_command(self, commands: list):
        """
        处理指令
        """
        logger.debug("处理指令: %s", commands)
        for command in commands:
            if not isinstance(command, dict):
                self.anime_loader.stop_animation()
                logger.error("指令格式错误: %s", command)
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
                        logger.warning("指令值格式错误(不是字典): %s", item_info)
                        return
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
                    logger.info("添加道具: %s, 描述: %s", item_name, item_desc)
                else:
                    logger.warning("添加道具时未提供道具信息或者信息格式不正确: %s", command)
            elif command_type == "remove_item":
                if value:
                    if value in self.item_system.inventory:
                        del self.item_system.inventory[value]
                        # self.history_simple_summaries.append(
                        #    f"{self.custom_config.player_name}失去了道具{value}")
                        self.message_queue.append(
                            f"{COLOR_RED}你失去了道具{value}{COLOR_RESET}")
                        logger.info("移除道具: %s", value)
                    else:
                        logger.warning("移除时玩家没有道具【%s】: %s", value, command)
                else:
                    logger.warning("移除道具时未提供道具信息: %s", command)
            elif command_type == "change_attr":
                # value: 对象{"属性名": "属性值"}，属性名为力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA中的一个，属性值可以是负数。
                if value:
                    if not isinstance(value, dict) or len(value) != 1:
                        logger.warning("改变属性时提供的信息格式错误: %s", command)
                        continue
                    # 解析属性名和属性值
                    attribute_name, attribute_value = list(value.keys())[
                        0], float(list(value.values())[0])
                    desc = command.get("desc", "")
                    if self.attr_system.in_attrs(attribute_name):
                        self.attr_system.set_attr(attribute_name, self.attr_system.get_attr(
                            attribute_name) + attribute_value)
                        # self.history_simple_summaries.append(
                        #    f"{self.custom_config.player_name}的{attribute_name}属性{"因为"+desc+"而" if desc else ""}改变了{attribute_value}")
                        change_message = f"{self.custom_config.player_name}的属性{attribute_name}{"因为"+desc+"而" if desc else ""}变动{attribute_value:+}(总{self.attr_system.get_attr(attribute_name)})"
                        change_message = COLOR_GREEN + \
                            f"{change_message}"+COLOR_RESET if attribute_value > 0 else COLOR_RED + \
                            f"{change_message}"+COLOR_RESET
                        self.message_queue.append(
                            change_message)
                        logger.info("改变属性: %s, 描述: %s, 变动值: %s",
                                    attribute_name, desc, attribute_value)
                    else:
                        logger.warning("改变属性时玩家没有属性【%s】: %s", value, command)
                else:
                    logger.warning("改变属性时未提供属性信息: %s", command)
            elif command_type == "change_situation":
                if value is not None:
                    if isinstance(value, str) and ((value.startswith(("+", "-")) and value[1:].isdigit()) or value.isdigit()):
                        logger.warning("形势值不是整数,但可以转换: %s", command)
                        value = int(value)
                    if not isinstance(value, int):
                        logger.warning("改变形势值时提供的信息格式错误: %s", command)
                        continue
                    self.situation_system.situation += value
                    self.situation_system.situation = max(
                        -10, min(self.situation_system.situation, 10))
                    logger.info("改变形势值: %s, 变动值: %s", command, value)
                else:
                    logger.warning("改变形势值时未提供形势值信息: %s", command)
            elif command_type == "gameover":
                self.current_game_status = "failure"
                logger.info("游戏结束: %s", command)
                self.anime_loader.stop_animation()
                self.anime_loader.start_animation(
                    "dot", message=COLOR_RED+"游戏结束"+COLOR_RESET)
                time.sleep(4)
                self.anime_loader.stop_animation()
                break
            elif command_type == "set_var":
                if value is not None:
                    logger.debug("设置变量时提供的信息: %s", value)
                    if not isinstance(value, dict):
                        logger.warning("设置变量时提供的信息格式错误: %s", command)
                        continue
                    # 解析变量名和变量值(为多变量设置提供支持)
                    for var_name, var_value in value.items():
                        self.variables[var_name] = var_value
                else:
                    logger.warning("设置变量时未提供变量信息: %s", command)
            elif command_type == "del_var":
                if value:
                    # 解析变量名
                    var_name = str(value)
                    if var_name in self.variables:
                        del self.variables[var_name]
                    else:
                        logger.warning("删除变量时玩家没有变量【%s】: %s",
                                       var_name, command)
                else:
                    logger.warning("删除变量时未提供变量信息: %s", command)

    # AI调用-开始游戏
    @log_exceptions(logger)
    def start_game(self, st_story: str = ''):
        """
        开始游戏（第一轮）
        """
        logger.info("开始游戏: %s", st_story)
        init_prompt = self.prompt_manager.get_initial_prompt(
            self.player_name,
            st_story,
            self.custom_config.get_custom_prompt(),
            self.item_system.get_inventory_text_for_prompt(),
            self.attr_system.get_attribute_text())
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
        self.history_descriptions.append(self.current_description)
        self.token_consumes.append(self.l_p_token+self.l_c_token)

    # AI调用-进行游戏(后续轮次)
    @log_exceptions(logger)
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
            logger.info("自定义选项: %s", option_id)
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
                    self.attr_system.get_attribute_text(),
                    self.situation_system.get_situation_text(),
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
                            logger.info("自定义选项修饰: %s", resp_dict)
                        except (ValueError, json.JSONDecodeError) as e:
                            self.anime_loader.stop_animation()
                            logger.error("解析AI响应时出错: %s", e)
                            input(
                                f"解析AI响应时出错，按任意键重试,注意token消耗(本次){self.l_c_token+self.l_p_token}")
                            print("正在重试...")
                            response = self.call_ai(custom_prompt)
        else:
            selected_option = next(
                (opt for opt in self.current_options if int(opt["id"]) == int(option_id)), None)
            logger.info("选项不修饰: %s", selected_option)
        if not selected_option:
            logger.warning("无效的选项ID: %s", option_id)
            print("无效的选项ID")
            return -1
        if selected_option:
            if selected_option["type"] == "must" and selected_option.get("extra", "") != "custom_action":
                if self.attr_system.get_attr(selected_option["main_factor"]) < selected_option["difficulty"]:
                    print(
                        f"不满足选项要求[{selected_option['main_factor']}≥{selected_option['difficulty']}]")
                    logger.info("选项要求未满足: %s", selected_option)
                    return -1
            elif selected_option["type"] == "must":
                # 对于自定义操作，我们根据是否达到门槛添加是否成功标识即可，不直接return
                if self.attr_system.get_attr(selected_option["main_factor"]) >= selected_option["difficulty"]:
                    selected_option["text"] += COLOR_GREEN + \
                        "<满足行动条件>"+COLOR_RESET
                    logger.info("选项要求满足: %s", selected_option)
                else:
                    selected_option["text"] += COLOR_RED + \
                        "<不满足行动条件>"+COLOR_RESET
                    logger.info("选项要求未满足: %s", selected_option)
            # 处理并检定概率(两次判定:第一次就成功：大成功；第二次:小成功；)
            if selected_option["type"] == "check":
                logger.info("选项检定: %s", selected_option)
                main_attr_val = self.attr_system.get_attr(
                    selected_option["main_factor"])
                diff_attr_difficulty = main_attr_val - \
                    selected_option["difficulty"]
                target_prob = selected_option["probability"] + \
                    diff_attr_difficulty * 3 / 2000
                situation_factor = self.situation_system.situation
                if situation_factor > 0:
                    target_prob += 0.01 * 2.2 * (situation_factor ** 1.25)
                else:
                    target_prob += 0.04 * situation_factor
                is_enable_final_chance = diff_attr_difficulty > 5
                final_chance_prob = final_chance_target = 0.0
                if is_enable_final_chance:
                    final_chance_prob = final_chance_target = (
                        diff_attr_difficulty - 5) / 100
                check_result = self.check_system.probability_check(
                    target=target_prob,
                    is_enable_normal=False,  # 无"不成功也不失败"的情况
                    is_enable_double_check=True,  # 启用二次检定（大成功/小成功/失败逻辑）
                    first_check_factor=0.65,  # 第一次检定目标值系数（0.65）
                    second_check_factor=1.00,  # 第二次检定目标值系数（1.0）
                    allow_base_first_success=True,  # 第一次检定保底1%概率
                    big_failure_prob_addon=0.20,  # 大失败触发阈值（+0.20）
                    is_enable_final_chance=is_enable_final_chance,  # 动态启用最后机会
                    final_chance_prob=final_chance_prob,  # 最后机会触发概率
                    final_chance_target=final_chance_target,  # 最后机会判定目标值
                    first_check_anime_duration=2.0,  # 第一次检定动画时长（2s）
                    second_check_anime_duration=3.0,  # 第二次检定动画时长（3s）
                    final_chance_anime_duration=2.5  # 最后机会动画时长（2.5s）
                )
                if check_result == 3:
                    # 大成功
                    stext = "检定大成功!"
                    print(stext)
                elif check_result == 1:
                    # 小成功（含最后机会成功）
                    stext = "检定小成功"
                elif check_result == -1:
                    # 小失败
                    stext = "检定小失败"
                elif check_result == -3:
                    # 大失败
                    stext = "检定大失败"
                selected_option["text"] += f'<{stext}>'
                logger.info("选项检定结果: %s", check_result)
            self.history_choices.append('['+selected_option["text"]+']')

            prompt = self.prompt_manager.get_continuation_prompt(
                self.player_name,
                self.current_description,
                "\n".join(
                    [str(s) for s in self.history_simple_summaries[:-1] if s is not None]),
                selected_option["text"],
                selected_option["next_preview"],
                self.custom_config.get_custom_prompt(),
                self.item_system.get_inventory_text_for_prompt(),
                self.attr_system.get_attribute_text(),
                self.situation_system.get_situation_text(),
                self.get_vars_text())

        if not prompt:
            logger.error("prompt为空")
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
        self.history_descriptions.append(self.current_description)
        return 0

    # AI调用-思考(think指令)
    @log_exceptions(logger)
    def think_go_game(self, think_context):
        """玩家思考游戏中的情况"""
        logger.info("思考: %s", think_context)
        think_success_or_not = self.check_system.probability_check(
            0.2 + 0.6873 * atan(0.02345 * self.attr_system.get_attr("INT")), is_enable_double_check=True)
        logger.info("思考结果: %s", think_success_or_not)
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
            self.situation_system.get_situation_text())
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation("dot", message="思考中")
        res = self.call_ai(prompt)
        while not res:
            self.anime_loader.stop_animation()
            logger.error("思考时调用AI模型相应为空")
            input(f"AI响应失败，按任意键重试.[注意Token消耗{self.total_tokens}]\n")
            res = self.call_ai(prompt)
        self.current_description += "\n[思考:{think_context}] "+res
        self.history_descriptions[-1] = self.current_description
        self.token_consumes[-1] += self.l_p_token+self.l_c_token
        self.anime_loader.stop_animation()
        return 0

    # AI调用-判断使用物品是否合理
    @log_exceptions(logger)
    def is_use_item_ok(self, focus_item: str, player_move: str, target: str = ""):
        """判断使用物品是否合理"""
        logger.info("判断使用物品是否合理: %s, %s, %s", focus_item, player_move, target)
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
            logger.error("判断使用物品是否合理时调用AI模型相应为空")
            return True
        try:
            is_ok = json.loads(response)["is_valid"] == 1
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("判断使用物品是否合理时解析AI模型相应失败，默认返回False")
            is_ok = False
        self.token_consumes[-1] += self.l_p_token+self.l_c_token
        logger.info("判断使用物品是否合理结果: %s", is_ok)
        return is_ok

    # AI调用-总结摘要并去除无用物品和变量
    @log_exceptions(logger)
    def conclude_summary(self):
        """
        总结摘要，清理无用物品和变量
        """
        logger.info("总结摘要并去除无用物品和变量")

        def phase_summary(resp):
            try:
                r = json.loads(repair_json(resp))
                summ = r["summary"]
                rmv_item = r["useless_items"]
                rmv_var = r["useless_vars"]
                return 1, summ, rmv_item, rmv_var
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("[警告]:总结历史剧情时解析json失败%s，错误信息：%s", resp, e)
                return 0, "", [], []

        # 当所有摘要都经过了压缩，我们采取稀释旧摘要策略
        if not any(i and len(i) < self.compressed_summary_textmin for i in self.history_simple_summaries[:-1]):
            logger.info("使用稀释旧摘要策略")
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
                logger.error("总结历史剧情时解析json失败(稀释旧摘要)%s", summary)
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
        logger.info("使用压缩新摘要策略")
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
            logger.error("总结历史剧情时解析json失败(压缩新摘要)%s", summary)
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

    # 统计-获取token统计信息

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

    # 文本-获取当前变量的文本描述

    def get_vars_text(self):
        """获取当前变量的文本描述"""
        if not self.variables:
            return "当前没有变量"
        text = "游戏变量表(变量名:值)：\n"
        for var_name, var_value in self.variables.items():
            text += f"{var_name}:{var_value}\n"
        return text

    # 日志-记录游戏剧本
    @log_exceptions(logger)
    def log_game(self, log_file: str):
        """记录游戏信息，处理Unicode编码问题"""
        def safe_json_dump(data, file_handle):
            """安全地序列化并写入JSON数据"""
            try:
                json_str = json.dumps(data, ensure_ascii=False, indent=2)
                file_handle.write(json_str + "\n")
            except (UnicodeEncodeError, UnicodeDecodeError):
                logger.warning("数据包含非ASCII字符，使用ASCII安全模式序列化")
                json_str = json.dumps(data, ensure_ascii=True, indent=2)
                file_handle.write(json_str + "\n")
            except Exception as e:
                logger.error("序列化失败: %s, 数据类型: %s", str(e), str(type(data)))

        def clean_text(text):
            """清理文本，处理None/非字符串类型"""
            if text is None:
                return ""
            if isinstance(text, str):
                return text.strip()
            return str(text).strip()

        logger.info("记录游戏信息到压缩文件: %s", log_file)
        base_dir = os.path.dirname(log_file)
        log_filename = os.path.basename(log_file)
        game_dir = os.path.join(base_dir, str(self.game_id))
        os.makedirs(game_dir, exist_ok=True)

        log_filename_gz = log_filename.replace(".log", ".log.gz")
        new_log_file = os.path.join(game_dir, log_filename_gz)
        narrative_filename = log_filename.replace(".log", "_narrative.log.gz")
        new_narrative_file = os.path.join(game_dir, narrative_filename)

        with gzip.open(new_log_file, "wt", encoding="utf-8", errors="replace") as f:
            safe_json_dump({"player_name": self.player_name}, f)
            safe_json_dump({"Time": CURRENT_TIME}, f)
            safe_json_dump({"token_usage": self.get_token_stats()}, f)
            for entry in self.conversation_history:
                safe_json_dump(entry, f)

        narrative_data = {}
        for idx, (desc, choice) in enumerate(zip(self.history_descriptions, self.history_choices)):
            round_num = idx + 1
            narrative_data[round_num] = {
                "desc": clean_text(desc),
                "choice": clean_text(choice)
            }
        logger.info("记录游戏剧本到压缩文件: %s", new_narrative_file)
        with gzip.open(new_narrative_file, "wt", encoding="utf-8", errors="replace") as f:
            safe_json_dump(narrative_data, f)

    # 显示-打印所有待显示消息

    def print_all_messages_await(self):
        """打印所有待显示消息"""
        while self.message_queue:
            print(self.message_queue.popleft())

    # 快捷指令-移除物品

    def iremove_item(self, item: str):
        """
        构造命令，从物品列表中移除物品
        """
        commands = [{
            "command": "remove_item",
            "value": item
        }]
        self.handle_command(commands)

    # 快捷指令-移除变量

    def idel_var(self, var: str):
        """
        构造命令，从变量列表中移除变量
        """
        commands = [{
            "command": "del_var",
            "value": var
        }]
        self.handle_command(commands)
