"""
游戏引擎
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 游戏引擎
import json
import os
import logging
import gzip
from collections import deque
from typing import Optional, Dict, List
from datetime import datetime
import openai
from rich import print
from json_repair import repair_json
from config import CustomConfig, CURRENT_TIME
from libs.animes import SyncLoadingAnimation
from libs.logger import log_exceptions
from libs.prompt_manager import PromptSection, PromptManager
from libs.replace_manager import TextReplaceManager
from libs.practical_funcs import generate_game_id, find_file_by_name, clear_screen
from libs.event_manager import CommandManager
from libs.token_ana import analyze_token_consume

logger = logging.getLogger(__name__)
AnimeLoader = SyncLoadingAnimation()
ReplaceManager = TextReplaceManager()
CommandManager = CommandManager()

VERSION = "Reborn-v0.1.9"


class ExtraData:
    """
    引擎用，额外数据，存储回合数等必要的需要持久化的信息
    务必添加可以被json序列化的额外数据,否则会导致持久化失败
    """

    def __init__(self):
        self.turns = 0  # 示例:回合数

        self.datas = {
            "preference_view_settings": {  # 显示偏好
                'show_init_resp': False,  # 显示原本AI相应
                'show_word_count': True,  # 显示字数
                'show_token_consume': True,  # 显示Token消耗
                'show_fee': True,  # 显示费用
                'show_game_id': True,  # 显示游戏ID
                'show_game_version': True,  # 显示游戏版本
                'show_model_name': True,  # 显示模型名称
                'show_mod_count': True,  # 显示加载的Mod数量
            }
        }

    def set_data(self, key: str, value, is_del=False):
        """
        设置额外数据
        """
        if is_del:
            if key in self.datas:
                del self.datas[key]
        else:
            self.datas[key] = value

    def get_data(self, key: str, default=None):
        """
        获取额外数据
        """
        return self.datas.get(key, default)

    def read_from_dict(self, extra_datas: dict):
        """
        从字典读取额外数据
        """
        self.turns = extra_datas.get("turns", 0)
        self.datas.update(extra_datas.get("extra_datas", {}))

    def to_dict(self) -> dict:
        """
        转换为字典
        """
        return {
            "turns": self.turns,
            "extra_datas": self.datas,
        }


class GameEngine:
    """
    游戏引擎
    """

    def __init__(self, custom_config: Optional[CustomConfig] = None):
        # 基础部分
        self.game_id = ''
        self.prompt_manager = PromptManager({
            'start': "./prompts/start_prompt.json",
            'continue': "./prompts/continue_prompt.json",
            'summary': "./prompts/summary_prompt.json"
        })
        self.prompt_manager.load_config_from_json()  # 恢复配置
        self.current_response = ""
        self.conversation_history = []
        self.history_descriptions = []  # 存储历史剧情
        self.history_choices = []  # 存储历史行动
        self.history_simple_summaries = []
        self.current_description = "游戏开始"
        self.current_user_input = ""

        # 摘要压缩部分
        self.summary_conclude_val = 20  # 当历史剧情超过20条时，对其进行压缩总结;所有摘要都会参与剧情生成.
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

        # 动画
        self.anime_loader = AnimeLoader

        # 待显示消息的队列
        self.message_queue = deque()

        # 额外数据
        self.extra_data = ExtraData()

        # 注册默认替换规则和变量
        default_replace_rules = {
            "game:player_name": "{GAME:PLAYER_NAME}",
            "game:player_story": "{GAME:PLAYER_STORY}",
            "game:current_desc": "{GAME:CURRENT_DESC}",
            "game:current_user_input": "{GAME:CURRENT_USER_INPUT}",
            "game:last_3_desc": "{GAME:LAST_3_DESC}",
            "game:pre_3_all_summary": "{GAME:PRE_3_ALL_SUMMARY}",
            "game:compressed_summary_textmin": "{GAME:COMPRESSED_SUMMARY_TEXTMIN}",
            "user:custom_pre_prompt": "{USER:CUSTOM_PRE_PROMPT}",
            "user:custom_body_prompt": "{USER:CUSTOM_BODY_PROMPT}",
            "user:custom_post_prompt": "{USER:CUSTOM_POST_PROMPT}",
            "user:preferences": "{USER:PREFERENCES}",
        }
        ReplaceManager.update_rule_dict(default_replace_rules)

        default_values_dict = {
            "GAME:PLAYER_NAME": lambda: self.custom_config.player_name,
            "GAME:PLAYER_STORY": lambda: self.custom_config.player_story,
            "GAME:LAST_3_DESC": lambda: "\n".join(self.history_descriptions[-4:-1]),
            "GAME:PRE_3_ALL_SUMMARY": lambda: "\n".join(
                # 条件2：所有长度大于self.compressed_summary_textmin的字符串（前置）
                [s for s in self.history_simple_summaries if len(s) > self.compressed_summary_textmin] +
                # 条件1：[:-4]范围内且长度小于self.compressed_summary_textmin的字符串（后置）
                [s for s in self.history_simple_summaries[:-4]
                    if len(s) < self.compressed_summary_textmin]
            ),
            "GAME:CURRENT_DESC": lambda: self.current_description,
            "GAME:CURRENT_USER_INPUT": lambda: self.current_user_input,
            "GAME:COMPRESSED_SUMMARY_TEXTMIN": lambda: str(self.compressed_summary_textmin),
            "USER:CUSTOM_PRE_PROMPT": lambda: self.custom_config.custom_prompts['pre'],
            "USER:CUSTOM_BODY_PROMPT": lambda: self.custom_config.custom_prompts['body'],
            "USER:CUSTOM_POST_PROMPT": lambda: self.custom_config.custom_prompts['post'],
            "USER:PREFERENCES": lambda: self.custom_config.get_preference_prompt()  # pylint: disable=unnecessary-lambda
        }
        ReplaceManager.update_values_dict(default_values_dict)

        # 注册默认命令
        self.register_default_commands()

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
                    return False
            self.current_description = json_response.get("description", "")
            if not self.current_description.strip():
                logger.warning("未能解析描述??\n %s", json_response)
                input(f"未能解析描述?? 按键重试 {json_response}\n")
                return False
            if self.current_description:
                self.history_simple_summaries.append(
                    json_response.get("summary", ""))
            return True
        except (ValueError, json.JSONDecodeError) as e:
            self.anime_loader.stop_animation()
            logger.error("解析AI响应时出错: %s , 响应内容: %s", e, response)
            print(f"解析AI响应时出错: {e}")
            print("响应内容:")
            print(response)
            input("按任意键继续")
            return False

    # AI调用-开始游戏
    @log_exceptions(logger)
    def start_game(self, st_story: str = ''):
        """
        开始游戏（第一轮）
        """
        logger.info("开始游戏: %s", st_story)
        if st_story:
            self.history_simple_summaries.append(f"[开局故事]:{st_story}")
        init_prompt = self.prompt_manager.get('start').get_full_prompt(
            extra_prompts={
                PromptSection.USER_INPUT: f"以{st_story if st_story else '一个完全随机的场景'}为故事开头，开始本局沉浸式文字游戏",
            }
        )
        replaced_prompt = ReplaceManager.replace(init_prompt)
        ai_response = self.call_ai(replaced_prompt)
        while not ai_response:
            input('无响应内容？任意键重试\n')
            ai_response = self.call_ai(replaced_prompt)
        if ai_response:
            ok_sign = self.parse_ai_response(ai_response)
            while not ok_sign:
                self.anime_loader.stop_animation()
                input(f"解析失败，按任意键重试.[注意Token消耗{self.total_tokens}]\n")
                ai_response = self.call_ai(replaced_prompt)
                if ai_response:
                    ok_sign = self.parse_ai_response(ai_response)
        self.history_descriptions.append(self.current_description)
        self.token_consumes.append(self.l_p_token+self.l_c_token)

    # AI调用-进行游戏(后续轮次)
    @log_exceptions(logger)
    def go_game(self, user_ipt, is_prompt_concluding=False):
        """
        进行游戏（后续轮次）
        """
        if len(self.history_simple_summaries) > self.summary_conclude_val and not is_prompt_concluding and self.conclude_summary_cooldown < 1:
            self.go_game(user_ipt, True)
        prompt = ""
        if is_prompt_concluding:
            self.conclude_summary()
            return 0
        if user_ipt:
            self.current_user_input = user_ipt
            prompt = self.prompt_manager.get('continue').get_full_prompt()
            prompt = ReplaceManager.replace(prompt)
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
                print("请耐心等待重试")
                ai_response = self.call_ai(prompt)
                if ai_response:
                    ok_sign = self.parse_ai_response(ai_response)
        self.token_consumes.append(self.l_p_token+self.l_c_token)
        self.conclude_summary_cooldown -= 1

        self.anime_loader.stop_animation()  # type:ignore
        self.history_descriptions.append(self.current_description)
        self.history_choices.append(user_ipt)
        return 0

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
                return 1, summ
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("[警告]:总结历史剧情时解析json失败%s，错误信息：%s", resp, e)
                return 0, ""

        # 当所有摘要都经过了压缩，我们采取稀释旧摘要策略
        if not any(i and len(i) < self.compressed_summary_textmin for i in self.history_simple_summaries[:-1]):
            logger.info("使用稀释旧摘要策略")
            prompt = self.prompt_manager.get('summary').get_full_prompt(
                extra_prompts={
                    PromptSection.USER_INPUT: f"历史剧情摘要: {'\n'.join([i for i in self.history_simple_summaries[:-10] if i])}"
                }
            )
            prompt = ReplaceManager.replace(prompt)
            self.anime_loader.stop_animation()
            self.anime_loader.start_animation(
                "dot", message="正在总结历史剧情")
            tmp = self.custom_config.max_tokens
            self.custom_config.max_tokens = 20480
            summary = self.call_ai(prompt)
            self.custom_config.max_tokens = tmp
            self.anime_loader.stop_animation()
            ok_sign, summ = phase_summary(summary)
            while not ok_sign:
                logger.error("总结历史剧情时解析json失败(稀释旧摘要)%s", summary)
                input(f"[警告]:总结历史剧情时解析json失败{summary}，按任意键重试")
                summary = self.call_ai(prompt)
                ok_sign, summ = phase_summary(summary)
            self.history_simple_summaries = [
                summ]+self.history_simple_summaries[10:]
            self.conclude_summary_cooldown = 10
            self.token_consumes[-1] += self.l_p_token+self.l_c_token
            return 0

        # 否则，我们只总结新摘要，形成压缩摘要
        logger.info("使用压缩新摘要策略")
        prompt = self.prompt_manager.get('summary').get_full_prompt(
            extra_prompts={
                PromptSection.USER_INPUT: f"历史剧情摘要: {'\n'.join(
                    [i for i in self.history_simple_summaries if i and len(i) < self.compressed_summary_textmin])}",
            }
        )
        prompt = ReplaceManager.replace(prompt)
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation(
            "dot", message="正在总结历史剧情")
        tmp = self.custom_config.max_tokens
        self.custom_config.max_tokens = 2048
        summary = self.call_ai(prompt)
        self.custom_config.max_tokens = tmp
        self.anime_loader.stop_animation()
        ok_sign, summ = phase_summary(summary)
        while not ok_sign:
            logger.error("总结历史剧情时解析json失败(压缩新摘要)%s", summary)
            input(f"[警告]:总结历史剧情时解析json失败{summary}，按任意键重试")
            summary = self.call_ai(prompt)
            ok_sign, summ = phase_summary(summary)
        self.history_simple_summaries = [
            i for i in self.history_simple_summaries if i and len(i) >= self.compressed_summary_textmin] + [summ]
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
            safe_json_dump({"player_name": self.custom_config.player_name}, f)
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
        print()
        while self.message_queue:
            print(self.message_queue.popleft())

    # 保存-管理自动存档
    @log_exceptions(logger)
    def manage_auto_saves(self, save_name="autosave"):
        """管理自动保存，每回合仅保留1个最新存档，且整体只保留最近的15个存档"""
        save_dir = "saves"
        game_save_dir = os.path.join(save_dir, self.game_id)

        if not os.path.exists(game_save_dir):
            return

        # 辅助函数：读取存档文件获取回合数
        def get_turn_and_timestamp(filename: str) -> tuple:
            filepath = os.path.join(game_save_dir, filename)
            total_turns = None
            # 提取文件时间戳（原逻辑）
            timestamp = get_file_timestamp(filename)

            # 读取存档文件获取回合数
            try:
                if filename.endswith('.json.gz'):
                    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                        data = json.load(f)
                        total_turns = data.get("total_turns")
                elif filename.endswith('.json'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        total_turns = data.get("total_turns")
            except (json.JSONDecodeError, OSError, Exception) as e:
                logger.warning("读取文件%s的回合数失败: %s", filename, str(e))

            # 回合数为None时用特殊值，避免分组异常
            return (total_turns if total_turns is not None else -1, timestamp, filename)

        # 辅助函数：提取文件时间戳（复用原逻辑）
        def get_file_timestamp(filename: str) -> str:
            parts = filename.replace('.json', '').replace('.gz', '').split('_')
            for part in parts:
                if len(part) == 15 and part[:8].isdigit() and part[9:].isdigit():
                    return part
            return filename

        # 1. 筛选符合条件的自动存档文件
        auto_save_files = []
        for f in os.listdir(game_save_dir):
            if (f.startswith(save_name) and
                not f.startswith('manual_') and
                not f.endswith('_latest.json') and
                not f.endswith('_latest.json.gz') and
                    f.endswith(('.json', '.json.gz'))):
                auto_save_files.append(f)
        logger.info("找到了%s个自动保存文件", len(auto_save_files))

        if not auto_save_files:
            return

        # 2. 按回合数分组，每组保留最新的文件（按时间戳排序）
        turn_groups: Dict[int, List[tuple]] = {}
        for file in auto_save_files:
            turn, ts, fname = get_turn_and_timestamp(file)
            if turn not in turn_groups:
                turn_groups[turn] = []
            turn_groups[turn].append((ts, fname))

        # 提取每个回合的最新文件（时间戳最大的）
        unique_turn_files = []
        for turn, files in turn_groups.items():
            if turn == -1:  # 无法读取回合数的文件，保留原逻辑
                unique_turn_files.extend([f[1] for f in files])
            else:
                # 按时间戳排序，取最新的一个
                files_sorted = sorted(files, key=lambda x: x[0])
                unique_turn_files.append(files_sorted[-1][1])

        # 3. 在去重后的文件中，保留最近的15个（按时间戳排序）
        unique_turn_files_sorted = sorted(
            unique_turn_files, key=get_file_timestamp)
        files_to_keep = unique_turn_files_sorted[-15:] if len(
            unique_turn_files_sorted) > 15 else unique_turn_files_sorted
        files_to_delete = [
            f for f in auto_save_files if f not in files_to_keep]

        # 4. 删除多余文件
        for filename in files_to_delete:
            filepath = os.path.join(game_save_dir, filename)
            try:
                os.remove(filepath)
                logger.info("自动删除旧存档: %s", filepath)
            except OSError as e:
                logger.error("删除文件%s失败: %s", filepath, str(e))
    # 保存-保存游戏

    @log_exceptions(logger)
    def save_game(self, save_name="autosave", is_manual_save=False):
        """
        保存游戏状态到文件（使用gzip压缩）
        """
        try:
            # 创建保存目录
            save_dir = "saves"
            if not os.path.exists(save_dir):
                logger.info("创建保存目录 %s", save_dir)
                os.makedirs(save_dir)

            # 获取或生成游戏ID
            if not self.game_id:
                self.game_id = generate_game_id()
                logger.info("生成游戏ID %s", self.game_id)

            # 创建游戏专属目录
            game_save_dir = os.path.join(save_dir, self.game_id)
            if not os.path.exists(game_save_dir):
                logger.info("创建游戏专属目录 %s", game_save_dir)
                os.makedirs(game_save_dir)

            save_data = {
                "version": VERSION,
                "save_desc": save_name,
                "game_id": self.game_id,
                "timestamp": datetime.now().isoformat(),
                "player_name": self.custom_config.player_name,
                # 基础变量
                "current_response": self.current_response,
                "current_description": self.current_description,
                "history_descriptions": self.history_descriptions,
                "history_choices": self.history_choices,
                "history_simple_summaries": self.history_simple_summaries,
                "conversation_history": self.conversation_history,
                # 摘要压缩相关
                "summary_conclude_val": self.summary_conclude_val,
                "conclude_summary_cooldown": self.conclude_summary_cooldown,
                # Token统计
                "total_prompt_tokens": self.total_prompt_tokens,
                "last_prompt_tokens": self.l_p_token,
                "total_completion_tokens": self.total_completion_tokens,
                "last_completion_tokens": self.l_c_token,
                "total_tokens": self.total_tokens,
                "token_consumes": self.token_consumes,
                # 自定义配置（保留）
                "custom_config": {
                    "max_tokens": self.custom_config.max_tokens,
                    "temperature": self.custom_config.temperature,
                    "frequency_penalty": self.custom_config.frequency_penalty,
                    "presence_penalty": self.custom_config.presence_penalty,
                    "player_name": self.custom_config.player_name,
                    "player_story": self.custom_config.player_story,
                    "porn_value": self.custom_config.porn_value,
                    "violence_value": self.custom_config.violence_value,
                    "blood_value": self.custom_config.blood_value,
                    "horror_value": self.custom_config.horror_value,
                    "custom_prompts": self.custom_config.custom_prompts,
                    "api_provider_choice": self.custom_config.api_provider_choice,
                },
                # 其他拓展变量
                "message_queue": list(self.message_queue),
                "total_turns": len(self.history_descriptions),
                "extra_datas": self.extra_data.to_dict(),
            }

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if is_manual_save:
                filename = f"manual_{save_name}_{timestamp}.json.gz"
            else:
                filename = f"{save_name}_{timestamp}.json.gz"
            filepath = os.path.join(game_save_dir, filename)
            logger.info("保存游戏数据到 %s", filepath)

            # 保存到压缩文件
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
                self.manage_auto_saves(save_name)

            return True, f"游戏已保存到 {self.game_id}/{filename}"

        except Exception as e:
            logger.error("保存失败: %s", str(e))
            return False, f"保存失败: {str(e)}"

    # 读取-查找最新存档
    @log_exceptions(logger)
    def find_latest_save(self, save_dir, save_name="autosave", include_manual=False):
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
                        save_time = datetime.fromisoformat(
                            save_data["timestamp"])
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
                        save_time = datetime.fromisoformat(
                            save_data["timestamp"])
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

    # 读取-列出所有存档
    @log_exceptions(logger)
    def list_saves(self):
        """
        列出所有保存文件
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

                save_files = [
                    f for f in os.listdir(game_save_dir)
                    if f.endswith(('.json', '.json.gz'))
                    and not f.startswith('.')
                ]

                for filename in save_files:
                    filepath = os.path.join(game_save_dir, filename)
                    if filename.endswith('.gz'):
                        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                            save_data = json.load(f)
                    else:
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
                        "file_format": "gzip" if filename.endswith('.gz') else "plain"
                    })
            except Exception as e:
                logger.error("解析存档 %s 失败: %s", game_id, e)
                continue

        save_info.sort(key=lambda x: x["timestamp"], reverse=True)
        return save_info

    # 读取-加载游戏
    @log_exceptions(logger)
    def load_game(self, save_name="autosave", filename=None, game_id=None):
        """
        从文件加载游戏状态
        """
        try:
            save_dir = "saves"
            if not os.path.exists(save_dir):
                logger.info("没有找到保存文件目录")
                return False, "没有找到保存文件目录"

            # 确定要加载的文件
            if filename and game_id:
                if not filename.endswith(('.json', '.json.gz')):
                    filepath = os.path.join(
                        save_dir, game_id, f"{filename}.json.gz")
                else:
                    filepath = os.path.join(save_dir, game_id, filename)
            elif filename:
                filepath = find_file_by_name(save_dir, filename)
                if not filepath:
                    filepath = find_file_by_name(save_dir, f"{filename}.gz")
                    if not filepath:
                        return False, f"没有找到保存文件 {filename}（含压缩版本）"
            else:
                if game_id:
                    game_save_dir = os.path.join(save_dir, game_id)
                    if not os.path.exists(game_save_dir):
                        return False, f"没有找到游戏 {game_id} 的保存目录"
                    filepath = os.path.join(
                        game_save_dir, f"{save_name}_latest.json.gz")
                    if not os.path.exists(filepath):
                        filepath = os.path.join(
                            game_save_dir, f"{save_name}_latest.json")
                else:
                    filepath = self.find_latest_save(save_dir, save_name)
                    if not filepath:
                        filepath = self.find_latest_save(
                            save_dir, f"{save_name}.gz")
                        if not filepath:
                            return False, f"没有找到 {save_name} 的保存文件（含压缩版本）"

            if not os.path.exists(filepath):
                logger.info("保存文件不存在: %s", filepath)
                return False, f"保存文件不存在: {filepath}"

            # 读取保存数据
            save_data = None
            if filepath.endswith('.gz'):
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    save_data = json.load(f)
                logger.info("成功读取压缩存档: %s", filepath)
            else:
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
            self.extra_data.read_from_dict(save_data["extra_datas"])
            self.game_id = save_data["game_id"]
            self.custom_config.player_name = save_data["player_name"]
            self.current_response = save_data.get("current_response", "")
            self.current_description = save_data["current_description"]
            self.history_descriptions = save_data["history_descriptions"]
            self.history_choices = save_data["history_choices"]
            self.history_simple_summaries = save_data["history_simple_summaries"]
            self.conversation_history = save_data["conversation_history"]

            # 恢复摘要压缩相关
            self.summary_conclude_val = save_data.get(
                "summary_conclude_val", 24)
            self.conclude_summary_cooldown = save_data["conclude_summary_cooldown"]

            # 恢复Token统计
            self.total_prompt_tokens = save_data["total_prompt_tokens"]
            self.l_p_token = save_data["last_prompt_tokens"]
            self.total_completion_tokens = save_data["total_completion_tokens"]
            self.l_c_token = save_data["last_completion_tokens"]
            self.total_tokens = save_data["total_tokens"]
            self.token_consumes = save_data["token_consumes"]

            # 恢复自定义配置
            config_data = save_data["custom_config"]
            self.custom_config.max_tokens = config_data["max_tokens"]
            self.custom_config.temperature = config_data["temperature"]
            self.custom_config.frequency_penalty = config_data["frequency_penalty"]
            self.custom_config.presence_penalty = config_data["presence_penalty"]
            self.custom_config.player_name = config_data["player_name"]
            self.custom_config.player_story = config_data["player_story"]
            self.custom_config.porn_value = config_data["porn_value"]
            self.custom_config.violence_value = config_data["violence_value"]
            self.custom_config.blood_value = config_data["blood_value"]
            self.custom_config.horror_value = config_data["horror_value"]
            self.custom_config.custom_prompts = config_data["custom_prompts"]
            if "api_provider_choice" in config_data:
                self.custom_config.api_provider_choice = config_data["api_provider_choice"]

            # 恢复其他拓展变量
            self.message_queue = deque(save_data["message_queue"])

            # 格式化时间并返回结果
            timestamp = datetime.fromisoformat(
                save_data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            logger.info("成功加载存档: 游戏ID %s, 保存时间 %s",
                        save_data['game_id'], timestamp)
            return True, f"游戏已加载 (游戏ID: {save_data['game_id']}, 保存时间: {timestamp})"

        except Exception as e:
            logger.error("加载存档时发生错误: %s", str(e))
            return False, f"加载失败: {str(e)}"

    # 手动保存
    def manual_save(self):
        """
        手动保存游戏，允许用户输入保存名称
        """
        save_name = input("输入保存名称（留空使用默认名称）: ").strip()
        if not save_name:
            save_name = "manual_save"

        success, message = self.save_game(save_name, is_manual_save=True)
        print(message)
        return success

    # 手动加载
    def manual_load(self):
        """
        手动加载游戏，分两级选择
        """
        all_saves = self.list_saves()
        if not all_saves:
            print("没有找到保存文件")
            return False

        current_game_id = self.game_id if self.game_id else ""

        current_saves = [
            s for s in all_saves if s["game_id"] == current_game_id]
        other_saves = [s for s in all_saves if s["game_id"] != current_game_id]
        other_game_ids = sorted(
            list(set([s["game_id"] for s in other_saves])), reverse=False)

        print("\n===== 选择游戏存档组 =====")
        for i, game_id in enumerate(other_game_ids, 1):
            save_count = len(
                [s for s in other_saves if s["game_id"] == game_id])
            print(f"{i}. 游戏ID: {game_id} (存档数量: {save_count})")

        current_option_idx = len(other_game_ids) + 1
        if current_game_id and current_saves:
            print(
                f"{current_option_idx}. 当前游戏ID: {current_game_id} (存档数量: {len(current_saves)})")
        elif current_game_id and not current_saves:
            print(f"{current_option_idx}. 当前游戏ID: {current_game_id} (无存档)")

        cancel_idx = len(other_game_ids) + (1 if current_game_id else 0) + 1
        print(f"{cancel_idx}. 取消")

        try:
            first_choice = input(f"\n请选择存档组编号（1-{cancel_idx}）: ")
            if first_choice == str(cancel_idx):
                return False

            first_choice_idx = int(first_choice)
            max_valid_idx = len(other_game_ids) + (1 if current_game_id else 0)
            if first_choice_idx < 1 or first_choice_idx > max_valid_idx:
                print("无效的选择编号")
                return False

            if first_choice_idx <= len(other_game_ids):
                selected_game_id = other_game_ids[first_choice_idx - 1]
            else:
                selected_game_id = current_game_id

            target_saves = [
                s for s in all_saves if s["game_id"] == selected_game_id]
            if not target_saves:
                print(f"游戏ID {selected_game_id} 下无可用存档")
                return False

            print(f"\n===== 选择 {selected_game_id} 的具体存档 =====")
            for i, save in enumerate(target_saves, 1):
                save_type = "手动" if save['save_type'] == 'manual' else "自动"
                print(
                    f"{i}. {save['game_id']}-{save['player_name']}-回合{save['total_turns']}-{save_type}"
                    f" (存档时间: {save['timestamp']})"
                )

            second_choice = input("\n选择要加载的存档编号（输入0取消）: ")
            if second_choice == "0":
                return False

            second_choice_idx = int(second_choice) - 1
            if 0 <= second_choice_idx < len(target_saves):
                selected_save = target_saves[second_choice_idx]
                success, message = self.load_game(
                    filename=selected_save["filename"],
                    game_id=selected_save["game_id"]
                )
                print(message)
                return success
            else:
                print("无效的存档编号")
                return False

        except ValueError:
            print("请输入有效的数字")
            return False
        except Exception as e:
            print(f"加载存档过程中出错: {e}")
            logger.error("手动加载存档失败", exc_info=e)
            return False

    # 命令-注册默认游戏指令
    def register_default_commands(self):
        """
        注册游戏指令到命令管理器
        """
        cmd_manager = CommandManager

        def cmd_summary():
            clear_screen()
            print("<剧情摘要>")
            print("\n".join(
                [f"{i+1}. {it}" for i, it in enumerate(list(self.history_simple_summaries))]))

        def cmd_ana_token():
            analyze_token_consume(self.token_consumes)

        def cmd_preference_view():
            while True:
                clear_screen()
                preference_view_settings = self.extra_data.datas.get(
                    "preference_view_settings", {})
                print("\n===== 显示偏好配置 =====")
                for id, (key, value) in enumerate(preference_view_settings.items()):
                    print(f"{id+1}. {key}: {value}")
                print("输入要配置的序号以切换开关，或者exit以退出配置")
                ipt = input("::")
                if ipt == "exit":
                    return
                try:
                    idx = int(ipt) - 1
                    if 0 <= idx < len(preference_view_settings):
                        key = list(preference_view_settings.keys())[idx]
                        preference_view_settings[key] = not preference_view_settings[key]
                        print(f"将 {key} 切换为 {preference_view_settings[key]}")
                    else:
                        print("无效的序号")
                except ValueError:
                    print("请输入有效的序号")

        def cmd_config():
            self.custom_config.config_game()

        def cmd_load():
            loadsuccess = self.manual_load()
            if loadsuccess:
                print("成功加载，按任意键继续...")
            else:
                print("加载失败，按任意键继续...")

        def cmd_save():
            self.manual_save()

        def cmd_prev_turn():
            """回到上一回合存档"""
            current_turns = len(self.history_descriptions)

            if current_turns <= 1:
                print(" 当前已是第一回合，无法回到上一回合！")
                return

            target_turn = current_turns - 1
            save_dir = "saves"
            game_save_dir = os.path.join(save_dir, self.game_id)

            if not os.path.exists(game_save_dir):
                print(f" 未找到游戏ID {self.game_id} 的存档目录！")
                return

            candidate_saves = []
            for filename in os.listdir(game_save_dir):
                # 过滤非存档文件
                if not filename.endswith(('.json', '.json.gz')) or filename.startswith('.'):
                    continue

                filepath = os.path.join(game_save_dir, filename)
                try:
                    # 读取存档文件（兼容压缩/非压缩格式）
                    if filename.endswith('.gz'):
                        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                            save_data = json.load(f)
                    else:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            save_data = json.load(f)

                    # 匹配目标回合数
                    save_turns = save_data.get("total_turns", 0)
                    if save_turns == target_turn:
                        # 记录存档时间戳和路径，用于后续选最新的
                        timestamp = datetime.fromisoformat(
                            save_data["timestamp"])
                        candidate_saves.append((timestamp, filepath))
                except Exception as e:
                    logger.warning(" 解析存档文件 %s 失败: %s", filename, e)
                    continue

            if not candidate_saves:
                print(f" 未找到第 {target_turn} 回合的存档！")
                return

            candidate_saves.sort(key=lambda x: x[0], reverse=True)
            _, latest_file = candidate_saves[0]

            # 加载找到的存档
            success, message = self.load_game(
                filename=os.path.basename(latest_file),
                game_id=self.game_id
            )
            print(f"\n{message}")
            if not success:
                print(f"加载第 {target_turn} 回合存档失败！")

        def cmd_conclude_summary():
            self.go_game("", True)
            print("总结完成")

        cmd_manager.reg("help", cmd_manager.list_cmds, "列出所有指令")
        cmd_manager.reg("mod",
                        self.prompt_manager.action_menu, "管理自定义提示词")
        cmd_manager.reg("ana_token", cmd_ana_token, "进行token消耗分析")
        cmd_manager.reg("back", cmd_prev_turn, "回到上一回合")
        cmd_manager.reg("viewsys", cmd_preference_view, "配置显示偏好")
        cmd_manager.reg("config", cmd_config, "配置游戏")
        cmd_manager.reg("load", cmd_load, "读取存档")
        cmd_manager.reg("save", cmd_save, "保存")
        cmd_manager.reg("summary", cmd_summary, "查看当前剧情摘要")
        cmd_manager.reg("conclude", cmd_conclude_summary, "总结摘要")
        cmd_manager.reg("new", lambda: 1, "开始新游戏")
        cmd_manager.reg("exit", lambda: 1, "退出游戏")

        return self.extra_data.datas.get("preference_view_settings", {}).get("show_init_resp", False)

    # 游戏日志-记录游戏
    def log_game_file(self, log_file: str):
        """记录游戏信息到日志文件"""
        return self.log_game(log_file)

    # 获取版本号
    @property
    def version(self):
        """获取游戏版本号"""
        return VERSION
