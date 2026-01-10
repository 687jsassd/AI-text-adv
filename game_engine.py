"""
游戏引擎
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 游戏引擎
import json
import os
import re
import logging
import gzip
from collections import deque
from typing import Optional
import openai
from rich import print
from json_repair import repair_json
from config import CustomConfig, CURRENT_TIME
from libs.practical_funcs import (COLOR_RESET,
                                  COLOR_YELLOW,)
from libs.animes import SyncLoadingAnimation
from libs.logger import log_exceptions
from libs.prompt_manager import PromptManagerRebuild, PromptSection

logger = logging.getLogger(__name__)

AnimeLoader = SyncLoadingAnimation()


class GameEngine:
    """
    游戏引擎
    """

    def __init__(self, custom_config: Optional[CustomConfig] = None):
        # 基础部分
        self.game_id = ''
        self.prompt_managers = {
            'start': PromptManagerRebuild("./prompts/start_prompt.json"),
            'continue': PromptManagerRebuild("./prompts/continue_prompt.json"),
            'summary': PromptManagerRebuild("./prompts/summary_prompt.json")
        }
        self.current_response = ""
        self.conversation_history = []
        self.history_descriptions = []  # 存储历史剧情
        self.history_choices = []  # 存储历史行动
        self.history_simple_summaries = []
        self.current_description = "游戏开始"

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

        # 动画
        self.anime_loader = AnimeLoader

        # 待显示消息的队列
        self.message_queue = deque()

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
            # 添加换行
            self.current_description = re.sub(
                r"。(?!』)",  # 正则规则：匹配"。"，且其后紧跟的不是"』"
                "。\n",       # 替换成：。+换行符
                self.current_description
            )
            self.current_description = self.current_description.replace(
                "』", "』\n")
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
        init_prompt = self.prompt_managers['start'].get_full_prompt(
            extra_prompts={
                PromptSection.PRE_PROMPT: f"玩家姓名: {self.player_name},玩家背景: {self.custom_config.player_story}" + self.custom_config.custom_prompts['pre'],
                PromptSection.BODY_PROMPT: self.custom_config.custom_prompts['body'],
                PromptSection.USER_INPUT: f"以{st_story if st_story else '一个完全随机的场景'}为故事开头，开始本局沉浸式文字游戏",
                PromptSection.POST_PROMPT: self.custom_config.custom_prompts['post'],
            }
        )
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
            prompt = self.prompt_managers['continue'].get_full_prompt(
                extra_prompts={
                    PromptSection.PRE_PROMPT: f"玩家姓名: {self.player_name},玩家背景: {self.custom_config.player_story}" + self.custom_config.custom_prompts['pre'],
                    PromptSection.BODY_PROMPT: self.custom_config.custom_prompts['body'],
                    PromptSection.POST_PROMPT: self.custom_config.custom_prompts['post'],
                }
            ).replace(
                "{history_story}", self.history_simple_summaries[-1]
            ).replace(
                "{current_scene}", self.current_description
            ).replace(
                "{player_action}", user_ipt
            )

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
            prompt = self.prompt_managers['summary'].get_full_prompt(
                extra_prompts={
                    PromptSection.PRE_PROMPT: f"玩家姓名: {self.player_name},玩家背景: {self.custom_config.player_story}",
                    PromptSection.USER_INPUT: f"历史剧情摘要: {'\n'.join([i for i in self.history_simple_summaries[:-10] if i])}"
                }
            )
            self.anime_loader.stop_animation()
            self.anime_loader.start_animation(
                "dot", message=COLOR_YELLOW+"正在总结历史剧情"+COLOR_RESET)
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
        prompt = self.prompt_managers['summary'].get_full_prompt(
            extra_prompts={
                PromptSection.PRE_PROMPT: f"玩家姓名: {self.player_name}",
                PromptSection.USER_INPUT: f"历史剧情摘要: {'\n'.join(
                    [i for i in self.history_simple_summaries if i and len(i) < self.compressed_summary_textmin])}",
            }
        )
        self.anime_loader.stop_animation()
        self.anime_loader.start_animation(
            "dot", message=COLOR_YELLOW+"正在总结历史剧情"+COLOR_RESET)
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
