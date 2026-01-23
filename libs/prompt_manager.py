"""
模块化的提示词管理器 - 新增终端可视化菜单交互版
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 模块化提示词管理器
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import copy
import json


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
        self.id_disabled = set()  # 禁用的json的ID
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

    def add_prompt(self, section: PromptSection, module_id: str, content: str,
                   insert_after: Optional[str] = None) -> bool:
        if module_id == "system":
            print("❌ 错误: 不允许使用'system'作为模块ID")
            return False

        if module_id in self._sections[section]:
            print(f"⚠️  警告: 模块 '{module_id}' 在部分 {section.name} 中已存在，将更新内容")
            self._sections[section][module_id].content = content
            return True

        fragment = PromptFragment(
            module_id=module_id, content=content, is_system=False)
        self._sections[section][module_id] = fragment
        order_list = self._section_orders[section]

        if insert_after is not None:
            if insert_after not in order_list:
                print(f"❌ 错误: 指定的插入位置模块 '{insert_after}' 不存在，默认追加到末尾")
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
            print("❌ 错误: 不允许删除system提供的提示词")
            return False
        if module_id not in self._sections[section]:
            print(f"❌ 错误: 模块 '{module_id}' 在部分 {section.name} 中不存在")
            return False
        del self._sections[section][module_id]
        self._section_orders[section].remove(module_id)
        return True

    def remove_json_prompts_by_id(self, id: str) -> bool:
        if id not in self.json_prompt_loaded:
            print(f"❌ 错误: ID '{id}' 未加载任何JSON文件")
            return False
        for section in PromptSection:
            self.remove_prompt(section, id)

        del self.json_prompt_loaded[id]
        return True

    def move_prompt(self, section: PromptSection, module_id: str,
                    target_module_id: str, before: bool = True) -> bool:
        if module_id == "system":
            print("❌ 错误: 不允许移动system提供的提示词")
            return False
        if target_module_id == "system" and before:
            print("❌ 错误: 不允许将提示词调整到system提示词之上")
            return False
        if module_id not in self._section_orders[section]:
            print(f"❌ 错误: 模块 '{module_id}' 在部分 {section.name} 中不存在")
            return False
        if target_module_id not in self._section_orders[section]:
            print(f"❌ 错误: 目标模块 '{target_module_id}' 在部分 {section.name} 中不存在")
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
            if module_id in self._sections[section] and module_id not in self.id_disabled:
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
            print(f"❌ 错误: 模块 '{module_id}' 在部分 {section.name} 中不存在")
            return False
        if module_id == "system":
            print("⚠️  警告: 更新system系统提示词内容")
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

    def save_to_json(self, file_path: str, id: str, desc: str = "") -> bool:
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
                "disabled": list(self.id_disabled)
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=4)
            print(f"✅ 成功保存配置到: {file_path}")
            return True
        except PermissionError:
            print(f"❌ 错误: 无权限写入文件 {file_path}")
            return False
        except Exception as e:
            print(f"❌ 保存JSON失败: {str(e)}")
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
            self.id_disabled = set(data["disabled"])
            return True
        except FileNotFoundError:
            print(f"❌ 错误: 指定的文件 {file_path} 不存在")
            return False
        except json.JSONDecodeError:
            print(f"❌ 错误: 文件 {file_path} 不是有效的JSON格式")
            return False
        except PermissionError:
            print(f"❌ 错误: 无权限读取文件 {file_path}")
            return False
        except Exception as e:
            print(f"❌ 加载JSON失败: {str(e)}")
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
            self.id_disabled.update(data["disabled"])
            return True
        except FileNotFoundError:
            print(f"❌ 错误: 指定的文件 {file_path} 不存在")
            return False
        except json.JSONDecodeError:
            print(f"❌ 错误: 文件 {file_path} 不是有效的JSON格式")
            return False
        except PermissionError:
            print(f"❌ 错误: 无权限读取文件 {file_path}")
            return False
        except Exception as e:
            print(f"❌ 加载JSON失败: {str(e)}")
            return False
