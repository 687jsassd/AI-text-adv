"""
游戏引擎拓展(必须)
物品系统
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from rich import print
from libs.practical_funcs import COLOR_YELLOW, COLOR_RESET, COLOR_RED, clear_screen
from libs.animes_rich import console


class ItemInventory:
    """
    物品库存系统
    """

    def __init__(self):
        self.inventory = {}
        self.item_repository = {}

    def get_item_repository_text(self, need_desc=True):
        """获取物品仓库的文本描述"""
        if not self.item_repository:
            return "物品仓库当前没有道具"
        return f"物品仓库当前道具列表（{len(self.item_repository)}）：\n"+"\n".join([f"{idx+1}.{item}: {desc if need_desc else ''}" for idx, (item, desc) in enumerate(self.item_repository.items())])

    def get_inventory_text(self, need_desc=True):
        """获取当前道具列表的文本描述"""
        if not self.inventory:
            return "当前没有道具"
        nums_text = f"{len(self.inventory)}" if len(
            self.inventory) <= 50 else f"{len(self.inventory)},但其中{len(self.inventory)-50}个道具不会参与剧情。如想，尝试丢弃物品？"
        available_items = self.inventory.items() if len(
            self.inventory) <= 50 else list(self.inventory.items())[-50:]
        no_available_items = list(self.inventory.items())[:-50] if len(
            self.inventory) > 50 else []
        return f"当前道具列表({nums_text}):\n" + "\n".join([f"{idx+1}.{item}: {desc if need_desc else ''}" for idx, (item, desc) in enumerate(available_items)] + [f"{idx+len(available_items)+1}.{COLOR_RED}[✘]{item}{COLOR_RESET}: {desc}" for idx, (item, desc) in enumerate(no_available_items)])

    def get_inventory_text_for_prompt(self):
        """获取当前道具列表的文本描述，更简洁"""
        if not self.inventory:
            return "玩家当前没有道具"
        if len(self.inventory) <= 12:
            return "当前道具列表：\n" + "\n".join(['{'+f"{item}:{desc}"+'}' for item, desc in self.inventory.items()])
        else:
            return "当前持有道具：\n" + "\n".join(['{'+f"{item}:{desc}"+'}' for item, desc in self.inventory.items()][-25:]) + f"\n以及过去的道具:{', '.join([item for item, desc in self.inventory.items()][-35:-12])}"

    def fix_item_name_error(self):
        """
        修复物品名中的错误
        核心逻辑：
        1. 保留非"无描述"的物品项
        2. 对"无描述"的物品，解析原始名称：
        - 按冒号分割名称和描述
        - 过滤引号/大括号等无效字符
        - 无有效名称时，清理描述标点作为名称，描述设为"无描述"
        """
        # 初始化修复后的物品字典
        fixed_inventory = {}

        # 辅助函数：过滤无效字符（引号、大括号）
        def _filter_invalid_chars(char: str) -> bool:
            """过滤掉无效字符（双引号、单引号、大括号）"""
            return char not in ['"', "'", '{', '}']

        # 辅助函数：清理标点符号（逗号、句号）
        def _clean_punctuation(text: str) -> str:
            """清理文本中的中英文逗号、句号"""
            punctuation = (',', '.', '，', '。')
            for p in punctuation:
                text = text.replace(p, '')
            return text

        # 遍历原始物品清单，逐个修复
        for original_item_key, item_desc in self.inventory.items():
            # 1. 非"无描述"的物品直接保留原键值
            if item_desc != "无描述":
                fixed_inventory[original_item_key] = item_desc
                continue

            # 2. 处理"无描述"的物品，解析有效名称和描述
            char_buffer = []  # 临时存储过滤后的字符
            fixed_item_name = ""  # 最终修复后的物品名

            # 遍历原始名称的每个字符，解析名称和描述
            for char in original_item_key:
                # 冒号分割：冒号前为名称，后为描述
                if char == ':':
                    fixed_item_name = ''.join(char_buffer)
                    char_buffer = []  # 清空缓冲区，准备存储描述部分
                    continue
                # 过滤无效字符，仅保留合法字符
                if _filter_invalid_chars(char):
                    char_buffer.append(char)

            # 3. 特殊情况：无有效名称且无描述字符时，清理标点作为名称，描述设为"无描述"
            # （注：原逻辑中`not char_buffer`时拼接为空，此处严格保留原逻辑）
            if fixed_item_name == "" and not char_buffer:
                fixed_item_name = _clean_punctuation(''.join(char_buffer))
                char_buffer = ["无描述"]

            # 4. 将修复后的键值对存入新字典
            fixed_inventory[fixed_item_name] = ''.join(char_buffer)

        # 替换为修复后的物品清单
        self.inventory = fixed_inventory

    def operate_item(self):
        """
        操作物品
        返回:
        是否是使用物品,使用物品文本
        """
        show_desc = True
        while True:
            clear_screen()
            console.rule(
                "物品操作",
                style="bold green")
            print("当前物品:" + self.get_inventory_text(show_desc))
            console.rule(style="bold green")
            print("\n仓库物品:" + self.get_item_repository_text(show_desc))
            console.rule("物品操作指令", style="bold green")
            print(
                "'*use 要操作的物品名(或id) 进行的操作 使用目标' 以操作物品(会推进剧情)")
            print("'*remove 物品名(或id)'以销毁物品;输入多个空格分隔的id以批量操作")
            print("'*put 物品名(或id)' 以存储物品  (只有最后50个物品会参与剧情);输入多个空格分隔的id以批量操作")
            print("'*get 物品名(或id)' 以从存储获得物品;输入多个空格分隔的id以批量操作")
            print("'*add 物品名 物品描述' 以添加物品")
            print("'*rename 物品id 新名称' 以重命名物品")
            print("'*redesc 物品id 新描述' 以改变物品描述")
            print("'**putall' 将所有物品转移到仓库")
            print("'**getall' 获得所有仓库中物品")
            print("'*desc 物品名(或id)' 以查看该物品描述")
            print("'*showdesc' 以切换是否显示描述")
            print("[red] exit. 退出物品操作 [/red]")
            user_input = input("输入操作:\n::")
            if user_input == "exit":
                return False, ('', '', '')
            elif user_input.startswith("*remove"):
                item_names = user_input.split("*remove")[1].strip().split(" ")
                for item_name in item_names:
                    if item_name.isdigit() and int(item_name) <= len(self.inventory):
                        item_name = list(self.inventory.keys())[
                            int(item_name)-1]
                    if item_name in self.inventory:
                        del self.inventory[item_name]
                        input(f"物品 {item_name} 已被销毁")
                    else:
                        input(f"物品 {item_name} 不存在于你的库存中")
            elif user_input.startswith("*put"):
                item_names = user_input.split("*put")[1].strip().split(" ")
                for item_name in item_names:
                    if item_name.isdigit() and int(item_name) <= len(self.inventory):
                        item_name = list(self.inventory.keys())[
                            int(item_name)-1]
                    if item_name in self.inventory:
                        self.item_repository[item_name] = self.inventory[item_name]
                        del self.inventory[item_name]
                        input(f"物品 {item_name} 已被存储")
                    else:
                        input(f"物品 {item_name} 不存在于你的库存中")
            elif user_input.startswith("*get"):
                item_names = user_input.split("*get")[1].strip().split(" ")
                for item_name in item_names:
                    if item_name.isdigit() and int(item_name) <= len(self.item_repository):
                        item_name = list(self.item_repository.keys())[
                            int(item_name)-1]
                    if item_name in self.item_repository:
                        self.inventory[item_name] = self.item_repository[item_name]
                        del self.item_repository[item_name]
                        input(f"物品 {item_name} 已被获得")
                    else:
                        input(f"物品 {item_name} 不存在于物品仓库中")
            elif user_input.startswith("*add"):
                item_name, item_desc = user_input.split(
                    "*add")[1].strip().split(" ", 1)
                self.item_repository[item_name] = item_desc
                input(f"物品 {item_name} 已被添加")
            elif user_input.startswith("*rename"):
                item_id, new_name = user_input.split(
                    "*rename")[1].strip().split(" ", 1)
                if item_id.isdigit() and int(item_id) <= len(self.inventory):
                    item_name = list(self.inventory.keys())[int(item_id)-1]
                if item_name in self.inventory:
                    self.inventory[new_name] = self.inventory[item_name]
                    del self.inventory[item_name]
                    input(f"物品 {item_name} 已被重命名为 {new_name}")
                else:
                    input(f"物品 {item_name} 不存在于你的库存中")
            elif user_input.startswith("*redesc"):
                item_id, new_desc = user_input.split(
                    "*redesc")[1].strip().split(" ", 1)
                if item_id.isdigit() and int(item_id) <= len(self.inventory):
                    item_name = list(self.inventory.keys())[int(item_id)-1]
                if item_name in self.inventory:
                    self.inventory[item_name] = new_desc
                    input(f"物品 {item_name} 已被重描述为 {new_desc}")
                else:
                    input(f"物品 {item_name} 不存在于你的库存中")
            elif user_input == "**putall":
                self.item_repository.update(self.inventory)
                self.inventory.clear()
                input("所有物品已被存储")
            elif user_input == "**getall":
                self.inventory.update(self.item_repository)
                self.item_repository.clear()
                input("所有物品已被获得")
            elif user_input.startswith("*use"):
                itemname, action, target = user_input.split(
                    "*use")[1].strip().split()
                if itemname.isdigit() and int(itemname) <= len(self.inventory):
                    itemname = list(self.inventory.keys())[int(itemname)-1]
                if itemname in self.inventory:
                    return True, (itemname, action, target)
                else:
                    input(f"物品 {itemname} 不存在于你的库存中")
            elif user_input.startswith("*desc"):
                item_name = user_input.split("*desc")[1].strip()
                if item_name.isdigit() and int(item_name) <= len(self.inventory):
                    item_name = list(self.inventory.keys())[int(item_name)-1]
                if item_name in self.inventory:
                    input(f"物品 {item_name} 的描述为: {self.inventory[item_name]}")
                else:
                    input(f"物品 {item_name} 不存在于你的库存中")
            elif user_input == "*showdesc":
                show_desc = not show_desc
            else:
                input("无效输入")
                continue
        return False, ('', '', '')

    def to_dict(self):
        """
        将物品库存转换为字典表示
        """
        return {
            "inventory": self.inventory,
            "item_repository": self.item_repository,
        }

    def from_dict(self, data):
        """
        从字典表示中加载物品库存
        """
        self.inventory = data.get("inventory", {})
        self.item_repository = data.get("item_repository", {})
