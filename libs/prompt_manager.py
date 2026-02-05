"""
模块化的提示词管理器
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 模块化提示词管理器
# pylint: disable=protected-access
# pylint: disable=dangerous-default-value
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import os
import copy
import json
import logging
from libs.practical_funcs import clear_screen

logger = logging.getLogger(__name__)


class PromptSection(Enum):
    PRE_PROMPT = 1
    BODY_PROMPT = 2
    USER_INPUT = 3
    POST_PROMPT = 4


@dataclass
class PromptFragment:
    module_id: str
    content: str
    is_system: bool = False

# 提示词管理器


class PromptManagerRebuild:
    """提示词管理器 - 支持JSON序列化/反序列化、终端可视化菜单交互"""

    def __init__(self, file_path: Optional[str] = None):
        self._sections: Dict[PromptSection, Dict[str, PromptFragment]] = {
            section: {} for section in PromptSection
        }
        self._section_orders: Dict[PromptSection, List[str]] = {
            section: [] for section in PromptSection
        }
        self.json_prompt_loaded: Dict[str, str] = {}  # 加载了外部json的ID ->DESC
        # 初始化时传入文件地址，则自动加载JSON配置
        if file_path:
            self.load_from_json(file_path)

    def load_init_sections(self, init_contents: Dict[PromptSection, str]) -> None:
        for section, content in init_contents.items():
            if section in self._sections:
                system_fragment = PromptFragment(
                    module_id="system",
                    content=content,
                    is_system=True
                )
                self._sections[section]["system"] = system_fragment
                self._section_orders[section] = ["system"]
        logger.info("初始化提示词部分完成")

    def add_prompt(self, section: PromptSection, module_id: str, content: str,
                   insert_after: Optional[str] = None) -> bool:
        if module_id == "system":
            logger.error(" 错误: 不允许使用'system'作为模块ID")
            return False

        if module_id in self._sections[section]:
            logger.warning(" 警告: 模块 '%s' 在部分 %s 中已存在，将更新内容",
                           module_id, section.name)
            self._sections[section][module_id].content = content
            return True

        fragment = PromptFragment(
            module_id=module_id, content=content, is_system=False)
        self._sections[section][module_id] = fragment
        order_list = self._section_orders[section]

        if insert_after is not None:
            if insert_after not in order_list:
                logger.error(" 错误: 指定的插入位置模块 '%s' 不存在，默认追加到末尾",
                             insert_after)
                order_list.append(module_id)
            else:
                index = order_list.index(insert_after) + 1
                order_list.insert(index, module_id)
        else:
            if len(order_list) > 0 and order_list[0] == "system":
                order_list.insert(1, module_id)
            else:
                order_list.append(module_id)
        return True

    def remove_prompt(self, section: PromptSection, module_id: str) -> bool:
        if module_id == "system":
            logger.error(" 错误: 不允许删除system提供的提示词")
            return False
        if module_id not in self._sections[section]:
            logger.warning(" 警告: 模块 '%s' 在部分 %s 中不存在",
                           module_id, section.name)
            return False
        del self._sections[section][module_id]
        self._section_orders[section].remove(module_id)
        return True

    def remove_json_prompts_by_id(self, id: str) -> bool:
        if id not in self.json_prompt_loaded:
            logger.error(" 错误: ID '%s' 未加载任何JSON文件", id)
            return False
        for section in PromptSection:
            self.remove_prompt(section, id)

        del self.json_prompt_loaded[id]
        return True

    def move_prompt(self, section: PromptSection, module_id: str,
                    target_module_id: str, before: bool = True) -> bool:
        if module_id == "system":
            logger.error(" 错误: 不允许移动system提供的提示词")
            return False
        if target_module_id == "system" and before:
            logger.error(" 错误: 不允许将提示词调整到system提示词之上")
            return False
        if module_id not in self._section_orders[section]:
            logger.error(" 错误: 模块 '%s' 在部分 %s 中不存在",
                         module_id, section.name)
            return False
        if target_module_id not in self._section_orders[section]:
            logger.error(" 错误: 目标模块 '%s' 在部分 %s 中不存在",
                         target_module_id, section.name)
            return False

        order_list = self._section_orders[section]
        order_list.remove(module_id)
        target_index = order_list.index(target_module_id)
        if not before:
            target_index += 1
        order_list.insert(target_index, module_id)
        return True

    def get_section_content(self, section: PromptSection) -> str:
        order_list = self._section_orders[section]
        fragments = []
        for module_id in order_list:
            if module_id in self._sections[section]:
                fragment = self._sections[section][module_id]
                fragments.append(fragment.content)
        return "\n".join(fragments)

    def get_full_prompt(self, extra_prompts: Optional[Dict[PromptSection, str]] = None) -> str:
        full_prompt_parts = []
        for section in PromptSection:
            section_content = self.get_section_content(section)
            if section_content:
                full_prompt_parts.append(section_content)
            if extra_prompts and section in extra_prompts and extra_prompts[section] is not None:
                full_prompt_parts.append(extra_prompts[section])
        return "\n".join(full_prompt_parts)

    def get_section_fragments(self, section: PromptSection) -> List[PromptFragment]:
        order_list = self._section_orders[section]
        fragments = []
        for module_id in order_list:
            if module_id in self._sections[section]:
                fragments.append(self._sections[section][module_id])
        return fragments

    def update_prompt(self, section: PromptSection, module_id: str, content: str) -> bool:
        if module_id not in self._sections[section]:
            logger.error(" 错误: 模块 '%s' 在部分 %s 中不存在",
                         module_id, section.name)
            return False
        if module_id == "system":
            logger.warning("  警告: 更新system系统提示词内容")
        self._sections[section][module_id].content = content
        return True

    def clear_section(self, section: PromptSection) -> None:
        system_fragment = self._sections[section].get("system")
        self._sections[section].clear()
        self._section_orders[section].clear()
        if system_fragment:
            self._sections[section]["system"] = system_fragment
            self._section_orders[section] = ["system"]

    def get_section_order(self, section: PromptSection) -> List[str]:
        return self._section_orders[section].copy()

    def copy_section(self, from_section: PromptSection, to_section: PromptSection) -> None:
        self._sections[to_section] = copy.deepcopy(
            self._sections[from_section])
        self._section_orders[to_section] = copy.deepcopy(
            self._section_orders[from_section])

    def __str__(self) -> str:
        output = []
        for section in PromptSection:
            fragments = self.get_section_fragments(section)
            if fragments:
                output.append(f"=== {section.name} ===")
                for fragment in fragments:
                    marker = "[系统片段🔒]" if fragment.is_system else "[自定义片段]"
                    output.append(
                        f"  {fragment.module_id} {marker}: {fragment.content[:60]}{'...' if len(fragment.content) > 60 else ''}")
        return "\n".join(output)

    def to_dict(self) -> Dict:
        result = {}
        for section in PromptSection:
            section_dict = {}
            fragments = self.get_section_fragments(section)
            for fragment in fragments:
                section_dict[fragment.module_id] = {
                    "content": fragment.content,
                    "is_system": fragment.is_system
                }
            result[section.name] = section_dict
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "PromptManagerRebuild":
        manager = cls()
        for section_name, section_data in data.items():
            try:
                section = PromptSection[section_name]
            except KeyError:
                print(f"⚠️  警告: 未知的提示词部分 '{section_name}'，跳过")
                continue
            manager._sections[section].clear()
            manager._section_orders[section].clear()
            for module_id, fragment_data in section_data.items():
                fragment = PromptFragment(
                    module_id=module_id,
                    content=fragment_data["content"],
                    is_system=fragment_data.get("is_system", False)
                )
                manager._sections[section][module_id] = fragment
                manager._section_orders[section].append(module_id)
        return manager

    def save_to_json(self, file_path: str, id: str, desc: str = "", areas: List[str] = []) -> bool:
        """
        将当前提示词管理器的所有数据保存到JSON文件
        :param file_path: JSON文件保存路径
        :param id : 该提示词集的ID
        :param desc: 描述(写入json中description键)
        :return: 保存成功返回True，失败返回False
        """
        try:
            data = self.to_dict()
            final_data = {
                "id": id,
                "description": desc,
                "data": data,
                "areas": areas,
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            logger.info("提示词管理器-保存到json:成功保存配置到: %s", file_path)
            return True
        except PermissionError:
            logger.error("提示词管理器-保存到json: 错误: 无权限写入文件 %s", file_path)
            return False
        except Exception as e:
            logger.error("提示词管理器-保存到json: 保存JSON失败: %s", str(e))
            return False

    def load_from_json(self, file_path: str) -> bool:
        """
        从指定JSON文件加载配置，覆盖当前管理器的所有数据
        :param file_path: JSON文件读取路径
        :return: 加载成功返回True，失败返回False
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            new_manager = self.from_dict(data["data"])
            self._sections = new_manager._sections
            self._section_orders = new_manager._section_orders
            self.json_prompt_loaded = {
                data["id"]: data["description"]
            }
            return True
        except FileNotFoundError:
            logger.error("提示词管理器-加载json: 错误: 指定的文件 %s 不存在", file_path)
            return False
        except json.JSONDecodeError:
            logger.error("提示词管理器-加载json: 错误: 文件 %s 不是有效的JSON格式", file_path)
            return False
        except PermissionError:
            logger.error("提示词管理器-加载json: 错误: 无权限读取文件 %s", file_path)
            return False
        except Exception as e:
            logger.error("提示词管理器-加载json: 加载JSON失败: %s", str(e))
            return False

    def add_from_json(self, file_path: str) -> bool:
        """
        从指定JSON文件加载配置，将其添加到当前管理器中，而不是覆盖
        :param file_path: JSON文件读取路径
        :return: 加载成功返回True，失败返回False
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            new_manager = self.from_dict(data["data"])
            for section in PromptSection:
                self._sections[section].update(
                    new_manager._sections[section])
                self._section_orders[section].extend(
                    new_manager._section_orders[section])
            self.json_prompt_loaded[data["id"]] = data["description"]
            return True
        except FileNotFoundError:
            logger.error("提示词管理器-添加自定义json: 错误: 指定的文件 %s 不存在", file_path)
            return False
        except json.JSONDecodeError:
            logger.error("提示词管理器-添加自定义json: 错误: 文件 %s 不是有效的JSON格式", file_path)
            return False
        except PermissionError:
            logger.error("提示词管理器-添加自定义json: 错误: 无权限读取文件 %s", file_path)
            return False
        except Exception as e:
            logger.error("提示词管理器-添加自定义json: 加载JSON失败: %s", str(e))
            return False

    def del_from_json(self, file_path: str) -> bool:
        """
        从指定JSON文件加载配置，将其从当前管理器中删除
        :param file_path: JSON文件读取路径
        :return: 加载成功返回True，失败返回False
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                id = data["id"]
                self.remove_json_prompts_by_id(id)
                return True
        except FileNotFoundError:
            logger.error("提示词管理器-删除自定义json: 错误: 指定的文件 %s 不存在", file_path)
            return False
        except json.JSONDecodeError:
            logger.error("提示词管理器-删除自定义json: 错误: 文件 %s 不是有效的JSON格式", file_path)
            return False
        except Exception as e:
            logger.error("提示词管理器-删除自定义json: 卸载JSON失败: %s", str(e))
            return False


# 自定义提示词总管理
class PromptManager:
    """自定义提示词总管理"""

    def __init__(self, init_prompt_managers: Dict[str, str] = {}):
        self.prompt_managers = {}  # 所有提示词管理器实例
        self.loaded_prompt_jsons = set()  # 已经加载的JSON文件的自定义提示词mod的路径
        if init_prompt_managers:
            for id, path in init_prompt_managers.items():
                self.add_prompt_manager(id, path)

    def get(self, id: str):
        """获取提示词管理器"""
        return self.prompt_managers[id]

    def add_prompt_manager(self, id: str, path: str = "", init_sections: Dict[PromptSection, str] = {}):
        """添加提示词管理器"""
        logger.info("提示词总管理-添加提示词管理器: 添加提示词管理器 %s 开始", id)
        if path:
            self.prompt_managers[id] = PromptManagerRebuild(path)
            logger.info("提示词总管理-添加提示词管理器: 添加提示词管理器 %s 成功", id)
        else:
            new_manager = PromptManagerRebuild()
            new_manager.load_init_sections(init_sections)
            self.prompt_managers[id] = new_manager
            logger.info("提示词总管理-添加提示词管理器: 添加提示词管理器 %s 成功", id)

    def del_prompt_manager(self, id: str):
        """删除提示词管理器"""
        if id in self.prompt_managers:
            del self.prompt_managers[id]
            logger.info("提示词总管理-删除提示词管理器: 删除提示词管理器 %s 成功", id)

    def load_prompt_json(self, path: str):
        """加载自定义提示词JSON文件"""
        # 检查文件是否已加载
        if path in self.loaded_prompt_jsons:
            logger.error("提示词总管理-加载自定义json: 错误: 文件 %s 已加载", path)
            return False
        # 根据path路径寻找并加载JSON文件
        if not os.path.exists(path):
            logger.error("提示词总管理-加载自定义json: 错误: 文件 %s 不存在", path)
            return False
        # 读取json，并查找areas字段
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                id = data.get("id", "")
                if not id:
                    logger.error("提示词总管理-加载自定义json: 错误: 文件 %s 未定义id", path)
                    return False
                areas = data.get("areas", [])
                if not areas:
                    logger.error("提示词总管理-加载自定义json: 错误: 文件 %s 未定义作用域", path)
                    return False
                # 对areas里所有的元素，如果有prompt_manager里的，则让其加载
                for area in areas:
                    if area in self.prompt_managers:
                        self.prompt_managers[area].add_from_json(path)
                logger.info(
                    "提示词总管理-加载自定义json: 加载成功: 文件 %s 作用域 %s", path, areas)
                self.loaded_prompt_jsons.add(path)
                return True
        except json.JSONDecodeError:
            logger.error("提示词总管理-加载自定义json: 错误: 文件 %s 不是有效的JSON格式", path)
            return False
        except Exception as e:
            logger.error(
                "提示词总管理-加载自定义json: 错误: 读取文件 %s 时发生错误: %s", path, str(e))
            return False

    def unload_prompt_json(self, path: str):
        """卸载自定义提示词JSON文件"""
        # 检查文件是否已加载
        if path not in self.loaded_prompt_jsons:
            logger.error("提示词总管理-卸载自定义json: 错误: 文件 %s 未加载", path)
            return False
        # 对areas里所有的元素，如果有prompt_manager里的，则让其卸载
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                areas = data.get("areas", [])
                if not areas:
                    logger.error("提示词总管理-卸载自定义json: 错误: 文件 %s 未定义作用域", path)
                    return False
                # 对areas里所有的元素，如果有prompt_manager里的，则让其卸载
                for area in areas:
                    if area in self.prompt_managers:
                        self.prompt_managers[area].del_from_json(path)
                logger.info(
                    "提示词总管理-卸载自定义json: 卸载成功: 文件 %s 作用域 %s", path, areas)
                self.loaded_prompt_jsons.remove(path)
        except Exception as e:
            logger.error(
                "提示词总管理-卸载自定义json: 错误: 读取文件 %s 时发生错误: %s", path, str(e))
            return False

    def action_menu(self):
        """操作菜单"""

        def check_dir_have_json_available(dir_path: str = './customprompt'):
            """检查目录是否有可用的JSON文件
                返回一个列表，每个元素是一个元组
                (path,id,desc,areas,text_len),后四者均从json读取
            """
            # 检查目录是否存在
            if not os.path.exists(dir_path):
                logger.error(
                    "提示词总管理-操作菜单-检查目录是否有可用的JSON文件: 错误: 目录 %s 不存在", dir_path)
                return False
            # 检查目录是否有JSON文件
            json_files = [f for f in os.listdir(
                dir_path) if f.endswith('.json')]
            if not json_files:
                logger.error(
                    "提示词总管理-操作菜单-检查目录是否有可用的JSON文件: 错误: 目录 %s 无可用JSON文件", dir_path)
                return False
            # 读取每个JSON文件，检查字段
            available_files = []
            for json_file in json_files:
                file_path = os.path.join(dir_path, json_file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        id = data.get("id", "")
                        desc = data.get("description", '无描述')
                        areas = data.get("areas", [])
                        # 找到data字段,遍历其中每一个section，遍历每一个section里面的内容的content字段，统计其字数和
                        text_len = 0
                        for _, section_data in data.get("data", {}).items():
                            for _, part_data in section_data.items():
                                text_len += len(part_data.get("content", ""))
                        if id and desc and areas and text_len > 0:
                            available_files.append(
                                (file_path, id, desc, areas, text_len))
                except Exception as e:
                    logger.error(
                        "提示词总管理-操作菜单-检查目录是否有可用的JSON文件: 错误: 读取文件 %s 时发生错误: %s", file_path, str(e))
                    continue
            return available_files

        while True:
            clear_screen()
            print("自定义提示词管理")
            # 获取可用的JSON文件
            available_files = check_dir_have_json_available()

            # 打印其情况
            if not available_files:
                print("customprompt目录无可用自定义提示词JSON文件")
            else:
                print("可用提示词文件(E代表已启用,<x>代表字数):\n")
                for idx, (path, id, desc, areas, text_len) in enumerate(available_files):
                    print(
                        f"{'\033[92m E \033[0m' if path in self.loaded_prompt_jsons else ''}{idx+1}.{desc}<{text_len}> - (id:{id},作用域:{areas})")
            print("\n输入序号启用/禁用提示词文件，输入exit保存并退出")

            # 读取用户输入
            user_input = input("请输入序号或exit: ")
            if user_input.lower() == 'exit':
                break
            try:
                idx = int(user_input) - 1
                if 0 <= idx < len(available_files):
                    path, id, desc, areas, text_len = available_files[idx]
                    if path in self.loaded_prompt_jsons:
                        self.unload_prompt_json(path)
                    else:
                        self.load_prompt_json(path)
                    input("完成操作，按任意键继续")
                else:
                    print("输入序号错误")
            except ValueError:
                print("输入序号错误")
            self.save_config_to_json()

    def save_config_to_json(self, file_path: str = './config/custom_prompt_mod_config.json'):
        """
        保存当前配置到JSON文件
        当前会保存的:
        - 已加载的提示词JSON文件路径列表
        """
        config = {
            "loaded_prompt_jsons": list(self.loaded_prompt_jsons)
        }
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            logger.info("提示词总管理-保存配置到JSON文件: 成功: 配置已保存到 %s", file_path)
        except Exception as e:
            logger.error(
                "提示词总管理-保存配置到JSON文件: 错误: 保存配置到 %s 时发生错误: %s", file_path, str(e))

    def load_config_from_json(self, file_path: str = './config/custom_prompt_mod_config.json'):
        """
        从JSON文件加载配置
        当前会加载的:
        - 已加载的提示词JSON文件路径列表
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                for path in config.get("loaded_prompt_jsons", []):
                    self.load_prompt_json(path)
            logger.info("提示词总管理-从JSON文件加载配置: 成功: 配置已从 %s 加载", file_path)
        except Exception as e:
            logger.error(
                "提示词总管理-从JSON文件加载配置: 错误: 从 %s 加载配置时发生错误: %s", file_path, str(e))
