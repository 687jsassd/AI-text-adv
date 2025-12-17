# Copyright (c) 2025 [687jsassd]
# MIT License
# 全局配置管理
import os
import json
from datetime import datetime

LOG_DIR = "logs"
CURRENT_TIME = datetime.now().strftime("%Y%m%d_%H%M%S")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# 颜色常量
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

# 配置文件路径
CONFIG_FILE = "config.json"
MODELS_FILE = "models.json"
BASEURLS_FILE = "baseurls.json"
APIKEYS_FILE = "apikeys.json"


class CustomConfig:
    """自定义配置"""

    frequency_reflect = {
        0: "从不出现",
        1: "很少出现",
        2: "略有出现",
        3: "中等频率出现",
        4: "较高频率出现",
        5: "频繁出现"
    }
    preference_reflect = {
        0: "色情和描述性行为的内容",
        1: "特别暴力的内容",
        2: "血腥描写的内容",
        3: "恐怖描写的内容"
    }

    def __init__(self):
        # 从JSON文件加载配置
        self.config_data = self._load_config()

        # 加载模型、baseurl和API配置
        self.models_data = self._load_models()
        self.baseurls_data = self._load_baseurls()
        self.apikeys_data = self._load_apikeys()

        # AI调用相关
        self.max_tokens = self.config_data.get(
            "ai_settings", {}).get("max_tokens", 1024)
        self.temperature = self.config_data.get(
            "ai_settings", {}).get("temperature", 0.9)
        self.frequency_penalty = self.config_data.get(
            "ai_settings", {}).get("frequency_penalty", 0.5)
        self.presence_penalty = self.config_data.get(
            "ai_settings", {}).get("presence_penalty", 0.1)

        # 自定义提示词相关
        self.custom_prompts = self.config_data.get("custom_prompts", "")

        # 偏好相关
        self.porn_value = self.config_data.get(
            "preferences", {}).get("porn_value", 2)  # 色情
        self.violence_value = self.config_data.get(
            "preferences", {}).get("violence_value", 1)  # 暴力
        self.blood_value = self.config_data.get(
            "preferences", {}).get("blood_value", 1)  # 血腥
        self.horror_value = self.config_data.get(
            "preferences", {}).get("horror_value", 0)  # 恐怖

        # 自我设定相关
        self.player_name = self.config_data.get(
            "player_settings", {}).get("player_name", "玩家")
        self.player_story = self.config_data.get(
            "player_settings", {}).get("player_story", "")

        # 模型选择相关 - 从配置文件加载
        self.model_names = self._convert_models_to_dict()
        self.model_names_choice = self.config_data.get(
            "model_settings", {}).get("model_names_choice", 0)

        self.base_urls = self._convert_baseurls_to_dict()
        self.base_urls_choice = self.config_data.get(
            "model_settings", {}).get("base_urls_choice", 0)

        self.api_keys = self._convert_apikeys_to_dict()
        self.api_keys_choice = self.config_data.get(
            "model_settings", {}).get("api_keys_choice", 0)

    def _load_models(self):
        """从JSON文件加载模型配置"""
        try:
            if os.path.exists(MODELS_FILE):
                with open(MODELS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                default_models = {
                    "models": {
                        "0": {
                            "name": "your-model-name",
                            "display_name": "desc"
                        }
                    }
                }
                self._save_json_file(MODELS_FILE, default_models)
                return default_models
        except Exception as e:
            print(f"加载模型配置文件时出错: {e}")
            return {"models": {"0": {
                "name": "your-model-name",
                "display_name": "desc"
            }}}

    def _load_baseurls(self):
        """从JSON文件加载baseurl配置"""
        try:
            if os.path.exists(BASEURLS_FILE):
                with open(BASEURLS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                default_baseurls = {
                    "base_urls": {
                        "0": {
                            "url": "your-base-url",
                            "display_name": "desc"
                        },
                    }
                }
                self._save_json_file(BASEURLS_FILE, default_baseurls)
                return default_baseurls
        except Exception as e:
            print(f"加载baseurl配置文件时出错: {e}")
            return {"base_urls": {"0": {
                "url": "your-base-url",
                "display_name": "desc"
            }}}

    def _load_apikeys(self):
        """从JSON文件加载API密钥配置"""
        try:
            if os.path.exists(APIKEYS_FILE):
                with open(APIKEYS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                default_apikeys = {
                    "api_keys": {
                        "0": {
                            "key": "your-api-key",
                            "display_name": "desc"
                        },
                    }
                }
                self._save_json_file(APIKEYS_FILE, default_apikeys)
                return default_apikeys
        except Exception as e:
            print(f"加载API密钥配置文件时出错: {e}")
            return {"api_keys": {"0": {
                "key": "your-api-key",
                "display_name": "desc"
            }}}

    def _convert_models_to_dict(self):
        """将模型配置转换为字典格式"""
        models_dict = {}
        try:
            for key, model_info in self.models_data.get("models", {}).items():
                models_dict[int(key)] = (model_info["name"],
                                         model_info["display_name"])
        except Exception as e:
            print(f"转换模型配置时出错: {e}")
            return {}
        return models_dict

    def _convert_baseurls_to_dict(self):
        """将baseurl配置转换为字典格式"""
        baseurls_dict = {}
        try:
            for key, baseurl_info in self.baseurls_data.get("base_urls", {}).items():
                baseurls_dict[int(key)] = (baseurl_info["url"],
                                           baseurl_info["display_name"])
        except Exception as e:
            print(f"转换baseurl配置时出错: {e}")
            return {}
        return baseurls_dict

    def _convert_apikeys_to_dict(self):
        """将API密钥配置转换为字典格式"""
        apikeys_dict = {}
        try:
            for key, apikey_info in self.apikeys_data.get("api_keys", {}).items():
                apikeys_dict[int(key)] = (apikey_info["key"],
                                          apikey_info["display_name"])
        except Exception as e:
            print(f"转换API密钥配置时出错: {e}")
            return {}
        return apikeys_dict

    def _load_config(self):
        """从JSON文件加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 如果配置文件不存在，先创建默认配置
                default_config = {
                    "ai_settings": {
                        "max_tokens": 1024,
                        "temperature": 0.9,
                        "frequency_penalty": 0.5,
                        "presence_penalty": 0.1
                    },
                    "preferences": {
                        "porn_value": 2,
                        "violence_value": 1,
                        "blood_value": 1,
                        "horror_value": 0
                    },
                    "player_settings": {
                        "player_name": "玩家",
                        "player_story": ""
                    },
                    "model_settings": {
                        "base_urls_choice": 0,
                        "model_names_choice": 0,
                        "api_keys_choice": 0
                    },
                    "custom_prompts": ""
                }
                self._save_json_file(CONFIG_FILE, default_config)
                return default_config
        except Exception as e:
            print(f"加载配置文件时出错: {e}")
            return {}

    def _save_json_file(self, file_path, data):
        """保存JSON数据到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存文件 {file_path} 时出错: {e}")

    def save_to_file(self):
        """将当前配置保存到文件"""
        config_data = {
            "ai_settings": {
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty
            },
            "preferences": {
                "porn_value": self.porn_value,
                "violence_value": self.violence_value,
                "blood_value": self.blood_value,
                "horror_value": self.horror_value
            },
            "player_settings": {
                "player_name": self.player_name,
                "player_story": self.player_story
            },
            "model_settings": {
                "base_urls_choice": self.base_urls_choice,
                "model_names_choice": self.model_names_choice,
                "api_keys_choice": self.api_keys_choice
            },
            "custom_prompts": self.custom_prompts
        }
        self._save_json_file(CONFIG_FILE, config_data)

    def get_preference_prompt(self):
        """获取偏好提示词(根据偏好的四个属性和对应的程度映射组成句子)"""
        preference_prompt = "\n 玩家的偏好："
        # 色情(0)
        preference_prompt += f"{self.preference_reflect[0]}的程度为{self.frequency_reflect[self.porn_value]}"

        # 暴力(1)
        preference_prompt += f"{self.preference_reflect[1]}的程度为{self.frequency_reflect[self.violence_value]}"

        # 血腥(2)
        preference_prompt += f"{self.preference_reflect[2]}的程度为{self.frequency_reflect[self.blood_value]}"

        # 恐怖(3)
        preference_prompt += f"{self.preference_reflect[3]}的程度为{self.frequency_reflect[self.horror_value]}"

        return preference_prompt

    def get_custom_prompt(self):
        """获取自定义提示词"""
        return "下面是用户的自定义提示词,你应该严格遵守:\n"+self.custom_prompts+self.get_preference_prompt()
