"""
模块化的提示词管理器
"""
# Copyright (c) 2025 [687jsassd]
# MIT License
# 模块化提示词管理器
from typing import Optional


class PromptManager:
    """提示词管理器"""

    def __init__(self):
        self.is_no_options = False
        self.prompts_sections = {}
        self.load_prompt_sections()

    def load_prompt_sections(self):
        """定义各部分提示词片段"""

        # 系统角色设定
        self.prompts_sections["system_role"] = """
        你是一个文字冒险游戏的AI主持人。你需要：
        1. 创建沉浸式的文字世界和剧情。
        2. 每次回复包含剧情描述和1-6个选项,根据玩家的选择推进剧情
        3. 保持故事连贯性和角色一致性
        4. NPC介绍应当包含穿着、年龄、个性、外貌、语言、名字.
        """
        self.prompts_sections["system_role_no_options"] = """
        你是一个文字冒险游戏的AI主持人。你需要：
        1. 创建沉浸式的文字世界和剧情。
        2. 根据玩家的行动描述推进剧情
        3. 保持故事连贯性和角色一致性
        4. NPC介绍应当包含穿着、年龄、个性、外貌、语言、名字.
        """

        # 输出格式要求
        # 力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK
        self.prompts_sections["output_format"] = """
        按照以下json格式输出：
                {
            "description": "主角推开黄蓉，自己挨了一刀",
            "summary": "主角为黄蓉挡刀",
            "options": [
                {"id": 1, "text": "休息", "type": "normal", "next_preview": "你休息"}
            ],
            "commands": [
                {"command": "change_situation", "value": -1},
                {"command": "set_var", "value": {'变量名': '35'}},
                {"command": "remove_item", "value": "道具名"},
                {"command": "change_attr", "value": {"STR": 1}}
            ]
        }
        说明：
        1. 输出格式：不带转义符。用双引号。对话使用『』包裹。
        2. 字段详解：
           - description: 当前场景的详细描述，完整且符合逻辑和发展方向。不要包含游戏机制、判定提示、剧情外内容。
           - summary: 剧情摘要，保留重要信息、潜在分支、NPC等信息，如描述了方位或剧情细节则详细记录。不超过85字。
                注意：摘要中的信息必须是剧情描述description中已有的信息，不能凭空捏造。
                    剧情描述若没有出现人物名称，摘要中也不能包含人物名称。
           - options: 选项的列表，每个选项为一个对象。
                * id: 唯一标识符，从1递增的整数。
                * text: 选项的文本内容，禁止添加如[必须]、(需力量STR>=12）等提示！
                * type: 选项类型，'normal'（常见）或'check'（需检定）或'must'（需门槛）
                * main_factor : 仅当type为'check'或者'must'时有。表示检定或门槛的主属性依赖，从力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK中选。
                * difficulty: 仅type为'check'或者'must'时有，整数，表示检定难度和门槛。数值越大越困难。
                * base_probability: 仅type为'check'时有，表示基本成功率，从-1到1的浮点数（0.32表示32%）。
                * next_preview: 选择该选项后故事发展的开头一句话过渡。
           - commands: 在本剧情中操作游戏数据的指令列表，每个指令为一个对象。如无指令，则不加该字段。
                * command: 指令类型，从['set_var','del_var,'add_item', 'remove_item', 'change_attr','change_situation','gameover']中选择。
                * value: 指令值，格式根据command而定。
                    - set_var: 添加或设定变量值，值为对象{变量名: 变量值},变量值必须是字符串，多个变量以逗号分隔。
                    - del_var: 删除变量，值为变量名。
                    - add_item: 添加物品，值为对象{道具名: 道具描述}
                    - remove_item: 移除物品，值为道具名称。
                    - change_attribute: 改变属性
                        - value: 对象{属性名: 变动值}，属性名同main_factor，可负。
                        - desc: 变化原因。
                    - change_situation: 改变形势值
                        - value: 变动量。为可负整数。
                    - gameover:令游戏失败。无value字段
        3. 规则与注意事项：
           - 指令：每个指令只操作一个物品、属性；批量操作则按顺序使用多条指令。
           - 消耗品：使用、投掷、吃喝等消耗道具时，使用remove_item移除。
           - 检定成功率：一般建议大于0.35。鼓励偶尔使用极端大或小(或负数)的难度值和基础概率值。
           - 属性：属性越高越难成长。若属性达50，增长开始受阻。默认普通人的全属性为10，游戏中最强者属性规定为全200左右；
           - 属性改变：根据剧情(如获得奖励、受伤)增减玩家属性。
           - 属性分布参考(全属性，均为成长完全的属性参考):
              1.不入流、三流人物: 5-13
              2.二流人物: 14-24
              3.一流人物: 25-49
              4. 豪侠: 50-99
              5. 宗师: 100-150
              6. 传奇: 151-200
           - 形势:当前的剧情形势对玩家的有利程度，范围为-10到10，-10表示绝境，10表示绝对优势，0表示均势。
                根据剧情变更形势值，一般幅度为-3到3，偶尔可突变，事件完成则形势清零。
        """
        self.prompts_sections["output_format_no_options"] = """
        按照以下json格式输出：
                {
            "description": "主角推开黄蓉，自己挨了一刀",
            "summary": "主角为黄蓉挡刀",
            "commands": [
                {"command": "change_situation", "value": -1},
                {"command": "set_var", "value": {'变量名': '35'}},
                {"command": "remove_item", "value": "道具名"},
                {"command": "change_attr", "value": {"STR": 1}}
            ]
        }
        说明：
        1. 输出格式：不带转义符。用双引号。出现对话则使用『』包裹。
        2. 字段详解：
           - description: 当前场景的沉浸式详细描述，完整且符合逻辑和发展方向。不要包含游戏机制、提示、剧情外内容。
           - summary: 剧情摘要，保留重要信息、潜在分支、NPC等信息，如描述了方位或剧情细节则详细记录。不超过85字。
                注意：摘要中的信息必须是剧情描述description中已有的信息，不能凭空捏造。
                    剧情描述若没有出现人物名称，摘要中也不能包含人物名称。
           - commands: 在本剧情中操作游戏数据的指令列表，每个指令为一个对象。如无指令，则不添加该字段。
                * command: 指令类型，从['set_var','del_var,'add_item', 'remove_item', 'change_attr','change_situation','gameover']中选择。
                * value: 指令值，格式根据command而定。
                    - set_var: 添加或设定变量值，值为对象{变量名: 变量值},变量值必须是字符串，多个变量以逗号分隔。
                    - del_var: 删除变量，值为变量名。
                    - add_item: 添加物品，值为对象{道具名: 道具描述}
                    - remove_item: 移除物品，值为道具名称。
                    - change_attribute: 改变属性
                        - value: 对象{属性名: 变动值}，属性名同main_factor，可负。
                        - desc: 变化原因。
                    - change_situation: 改变形势值
                        - value: 为可负整数。
                    - gameover:令游戏失败。无value字段
        3. 规则与注意事项：
           - 物品管理：若玩家在生成的本剧情中物品有变动，则必须通过指令变动道具。
           - 指令：每个指令只操作一个物品、属性；批量操作则按顺序使用多条指令。
           - 消耗品：使用、投掷、吃喝等消耗道具时，使用remove_item移除。
           - 属性：属性越高越难成长。若属性达50，增长开始受阻。默认普通人的全属性为10，游戏中大师的属性为全200左右；
           - 属性改变：根据剧情(如获得奖励、受伤)增减玩家属性。
            - 形势:当前的剧情形势对玩家的有利程度，范围为-10到10，-10表示绝境，10表示绝对优势，0表示均势，鼓励负形势的应用。
                根据剧情变更形势值，一般变动为-3到3，偶尔可突变，事件完成则形势清零。
        """

        # 世界背景和规则
        self.prompts_sections["world_rules"] = """
        规则：
        沉浸式文字游戏世界由玩家指定，你是AI主持人，剧情语言符合世界观.
        1. 玩家在世界中自由游玩或与NPC互动，玩家死亡则游戏失败。剧情根据玩家的选择及结果、属性、物品、变量而流畅变化。不出现追兵情节，战斗迅速不拖沓。
        2. 每轮生成135-250字新剧情，剧情多拓展，语言可带有细节、环境、人物外貌、心理、语言和道具的描述等描写，描写不重复。
        3. 不出现同类剧情。剧情不打断当前事件。剧情不强行带有事件引导，应该让玩家自由探索选择。
        4. 角色名字用[]包裹，特定称谓用<>包裹.
        5. 若要修改物品，应先移除物品，再添加修改后的物品。
        6. 任务、修习武功、技能、情报、剧情关键线索等也可以当作物品处理。寻常事件不记录成物品或变量。
        7. 一般物品、中间物品、消耗品在使用、更新、消耗时，一定要移除物品！长线剧情线索物品、关键物品、技能、学会的武功与纪念性物品等均建议保留。要常更新。
        8. 随剧情、选择、检定结果变更形势值。当出现遭遇类事件时，允许大幅度变更形势。
        9. 生成选项只参考当前已知剧情，不可剧透未知信息。
        10.变量尽量只存储数值（字符串）；不存储剧情信息、开关等。
        """
        self.prompts_sections["world_rules_no_options"] = """
        规则：
        沉浸式文字游戏世界由玩家指定，你是AI主持人，剧情语言符合世界观。
        1. 玩家在世界中自由游玩或与NPC互动，玩家死亡则游戏失败。剧情根据玩家的选择及结果、属性、物品、变量而流畅变化。不出现追兵情节，战斗迅速不拖沓。
        2. 每轮生成135-250字新剧情，剧情多拓展，语言可带有细节、环境、人物外貌、心理、语言和道具的描述等描写，描写不重复。
        3. 不出现同类剧情。剧情不打断当前事件。剧情不强行带有事件引导，应该让玩家自由探索选择。
        4. 角色名字用[]包裹，特定称谓用<>包裹.
        5. 若要修改物品，应先移除物品，再添加修改后的物品。
        6. 任务、修习武功、技能、情报、剧情关键线索等也可以当作物品处理。寻常事件不记录成物品或变量。
        7. 一般物品、中间物品、消耗品在使用、更新、消耗时，一定要移除物品！长线剧情线索物品、关键物品、技能、学会的武功与纪念性物品等均建议保留，但要常更新。
        8. 随剧情、玩家行动、变更形势值。当出现遭遇类事件时，允许大幅度变更形势。
        9.变量只存储数值（字符串）；不变量存储剧情信息、开关等。
        """

        # 用户故事
        self.prompts_sections["user_story"] = """
        """

        # 总结摘要用的提示词
        self.prompts_sections["summary_prompt"] = """
        总结下面的摘要形成一段简明扼要的摘要总结，着重详细记录重要信息(含可能重要的人物、地图、剧情细节或潜在分支、线索等)
        次要信息可简略提及或酌情丢弃。
        总结一般不超过350字，最坏不超过600字。有前后冲突的，以后为准覆盖。
        
        另外，根据剧情内容，筛选出不重要、旧的、无用的物品和变量，一并输出其名称
        (特别注意！如果出现相似的多个变量或物品名，那么只保留一个，可优先选择保留后出现的那个。
        比如"A好感度"和"A好感"，保留后出现的"A好感"，而前面那个就是无用变量。)
        
        以下面的json格式输出结果:
        {{
            "summary": "摘要总结",
            "useless_items": ["物品1名称", "物品2名称"],
            "useless_vars": ["变量1名称", "变量2名称"]
        }}
        """

    def iset_user_story(self, user_story: str):
        """设置用户故事"""
        self.prompts_sections["user_story"] = user_story

    def get_initial_prompt(self, player_name: str, st_story: str = '', custom_prompt: str = "", inventory_text: str = "", attribute_text: str = ""):
        """获取初始提示词"""
        initial_context = f"""
        玩家名为{player_name},从[{st_story if st_story else '地点、危险度、环境、NPC、身份、物品等完全随机'}]的开篇故事开始游戏。
        第一人称限知视角.
        注意：
        如果需要设置初始变量或者添加初始物品，那么要用指令实现！
        金钱一般视为变量而不是物品；
        """
        full_prompt = f"""
        {self.prompts_sections["system_role"] if not self.is_no_options else self.prompts_sections["system_role_no_options"]}
        {self.prompts_sections["world_rules"] if not self.is_no_options else self.prompts_sections["world_rules_no_options"]}
        {self.prompts_sections["output_format"] if not self.is_no_options else self.prompts_sections["output_format_no_options"]}

        {"主角的初始背景故事"+self.prompts_sections["user_story"]
            if self.prompts_sections["user_story"] else ""}
        {inventory_text+' 注意,物品名包括所有标点符号'}
        {attribute_text}
        {custom_prompt}
        {initial_context}
        """
        return full_prompt

    def get_continuation_prompt(self,
                                player_name: str,
                                cur_desc: str,
                                previous_description: str,
                                player_choice: str,
                                choice_preview: str = "",
                                custom_prompt: str = "",
                                inventory_text: str = "",
                                attribute_text: str = "",
                                situation_text: Optional[str] = "",
                                vars_text: str = ""):
        """获取后续提示词"""
        continuation_context = f"""
        历史: {previous_description}
        场景：{cur_desc}
        {situation_text}
        {player_name}的动作/话/指令是[{player_choice}]，
        {"执行动作后：" if choice_preview else ""}{choice_preview}
        {inventory_text+'\n(物品名包括符号)\n'}
        {attribute_text}
        {vars_text}
        注意：
        保证一定信息密度，避免描述太短，但不要进展太快，应该补充细节来丰富剧情。
        玩家行动可能导致游戏结束，根据剧情判断是否结束。
        鼓励适时引入新内容，避免只与重复的NPC做重复的事。
        不要总是或者过于频繁地引入新内容，玩家应有机会主动探索。
        {'剧情需结合思考内容进行走向调整。' if '[思考:' in cur_desc else ''}
        玩家希望自由探索，但可以偶尔出现非强制性的事件引子。
        玩家若忽略事件，则不被卷入事件，且事件会自行发展直到结束。
        不出现不情愿的躲藏、逃跑、被追杀、被监视等被动情节.
        场景深度、大小有限，鼓励转换场景，避免长时间在同一地点探索。
        机遇、奖励等不反复出现，不出现持续深入获得更多奖励的情况。
        {'''根据剧情与逻辑合理地给出1-5个选项，对应不同分支(可含退出剧情的)，选项类型和难度不同。
        选项中预期触发的指令，禁止写在当前剧情的commands中,比如 某选项是捡起地上的钱，那么选择之后会
        添加对应道具，这时不应该在当前剧情写指令，而是玩家选择了那个选项后才在下一轮剧情中写指令。''' if not self.is_no_options else ""}
        金钱一般视为变量而不是物品；
        实时进行：
        用指令根据剧情符合逻辑地变动物品、变量、形势、属性。
        用变量存储和更新需持久化的通用数据(如金钱、某NPC属性、好感度)，只存储数值型数据，不存储剧情信息.
        更新变量，保证变量实时跟随剧情，控制变量数量不太多。
        确保变量名严格匹配，禁止出现多个相似变量。
        移除旧或者无用的物品与变量，避免滥用或冗余。
        
        直接给出严格从玩家动作或话(话原封不动保留)开始的新剧情，不要重复任何当前描述的内容。

        """
        full_prompt = f"""
        {self.prompts_sections["world_rules"] if not self.is_no_options else self.prompts_sections["world_rules_no_options"]}
        {self.prompts_sections["output_format"] if not self.is_no_options else self.prompts_sections["output_format_no_options"]}
        主角初始背景故事：{self.prompts_sections["user_story"]}
        {custom_prompt}
        {continuation_context}
        """
        return full_prompt

    def get_summary_prompt(self, summary: str, inventory_text: str, vars_text: str):
        """获取总结摘要提示词"""
        summary_prompt = f"""
        在沉浸式的游戏环境中，目前大段剧情积累了很多摘要，
        {"主角的初始背景故事"+self.prompts_sections["user_story"]
            if self.prompts_sections["user_story"] else ""}
        {self.prompts_sections["summary_prompt"]}
        摘要：{summary}.
        \n{inventory_text}
        {vars_text}
        """
        return summary_prompt

    def get_think_prompt(self, think_context: str, player_name: str, cur_desc: str, previous_description: str, inventory_text: str = "", situation_text: Optional[str] = ""):
        """获取思考提示词"""
        think_context = f"""
        历史: {previous_description}
        场景：{cur_desc}
        {situation_text}
        {inventory_text}
        玩家{player_name}此时正在思考:{think_context}。
        你只针对该疑问，根据思考判定成功与否和玩家现有知识给出简要的玩家思考结果。
        若思考为小失败或大失败，则只获得模糊的结果。
        思考需要参考剧情、物品、属性的现实情况，不涉及到的的物品和剧情不参与。
        思考时剧情暂停，不要在思考中发展剧情、透露新内容、补充关键信息。
        不要在思考中包含游戏相关的词（如场景、判定、属性）。
        避免与之前的思考内容重复，给出符合主角设定的思考内容。
        思考内容中不出现其他问句，用陈述句描述。
        直接给出150字以内的思考内容文本，不要带有任何前缀后缀。
        """
        return think_context

    def get_use_item_prompt(self, player_name: str, cur_desc: str, player_move: str, focus_item: str, focus_item_desc: str, target: str = ""):
        """获取验证玩家动作是否合理的提示词"""
        use_item_prompt = f"""
        判断在当前场景中，玩家{player_name}对物品的操作是否合理。
        当前场景:{cur_desc}
        玩家{player_name}对物品{focus_item}的操作是：{player_move}, {"目标是"+target if target else ""}
        物品{focus_item}的描述是：{focus_item_desc}
        只按照逻辑判断，忽略现实中的道德、法律、伦理问题.
        用下面的json格式输出玩家操作是否合理(1表示合理，0表示不合理)
        {{
            "is_valid": 1/0
        }}
        """
        return use_item_prompt

    def get_action_mode_prompt(self, player_name: str, cur_desc: str, short_history_desc: str, player_move: str, inventory_text: str = "", attribute_text: str = "", situation_text: Optional[str] = "", custom_prompt: str = "", vars_text: str = ""):
        """获取自定义动作的类型等修饰后选项的提示词"""
        action_mode_prompt = f"""
        玩家{player_name}在当前场景中，计划进行动作:{player_move}。
        当前场景:{cur_desc}
        历史摘要:{short_history_desc}
        {situation_text}
        {inventory_text}
        {attribute_text}
        {vars_text}
        {custom_prompt}
        
        要求：
        你综合玩家的场景、物品、属性、变量等信息，为该动作选择一个客观合理符合逻辑和世界观的修饰，要求:
        使用下面的json格式输出,下为一示例，实际根据剧情决定各个字段:
        {{
            "type": "check或normal或must，根据剧情确定",
            "main_factor": "LUK等",
            "difficulty": 15,
            "base_probability": 0.5
        }}
        json说明：
        * type: 选项类型，为'normal'或'check'或'must'
        * main_factor : 仅当type为'check'或者'must'时有。表示检定或门槛的主属性依赖，从力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK中选。
        * difficulty: 仅type为'check'或者'must'时有，整数，表示检定难度和门槛。数值越大越困难。
        * base_probability: 仅type为'check'时有，表示基本成功率，从-1到1的浮点数（0.32表示32%）。
        规则说明：
        1.normal适用于一般事件，check适用于需进一步判断动作成功失败的事件；must适用于需要门槛才能完成的事件；
        2. base_probability一般事件建议大于0.35，鼓励偶尔使用极端（含负数）难度值和基础概率值。
        3.属性分布参考(全属性，均为成长完全的属性参考):
              1.不入流、三流人物: 5-13
              2.二流人物: 14-24
              3.一流人物: 25-49
              4. 豪侠: 50-99
              5. 宗师: 100-150
              6. 传奇: 151-200
        """
        return action_mode_prompt
