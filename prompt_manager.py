# Copyright (c) 2025 [687jsassd]
# MIT License
# 模块化提示词管理器
from typing import Optional


class PromptManager:
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
            "description": "主角修炼了一夜，总算入门了[太玄经]...",
            "summary": "主角修炼了太玄经",
            "options": [
                {"id": 1, "text": "拿回书册，休息一会", "type": "normal", "next_preview": "你把书册收好，休息调整"}
            ],
            "commands": [
                {"command": "add_item", "value": {'太玄经(入门)':'4级内功，你已经修炼入门'}
                },
                {"command": "change_attr", "value": {'STR':4},"desc":'修炼了太玄经，力量增长'
                },
                {"command": "change_situation", "value": -2
                },
                {"command": "set_var", "value": {'黄蓉好感度': '35'}}
            ]
        }
        说明：
        1. 输出格式：不带转义符。用双引号。出现对话则使用『』包裹。
        2. 字段详解：
           - description: 当前场景的详细描述。不要包含游戏机制、判定提示、剧情外内容。
           - summary: 剧情摘要，保留剧情重要信息，15-30字。
           - options: 选项的列表，每个选项为一个对象。
                * id: 唯一标识符，从1递增的整数。
                * text: 选项的文本内容，禁止添加如[必须]、(需力量STR>=12）等提示！
                * type: 选项类型，'normal'（普通，常见）或'check'（需检定，常见）或'must'（需选择门槛，比较少见）
                * main_factor : 仅当type为'check'或者'must'时有。表示检定或门槛的主属性依赖，从力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK中选。
                * difficulty: 仅type为'check'或者'must'时有，整数，表示检定难度和门槛。数值越大越困难。
                * base_probability: 仅type为'check'时有，表示基本成功率，从-1到1的浮点数（0.02表示2%）。
                * next_preview: 选择该选项后故事发展的开头一句话过渡。
           - commands: 在本次剧情中（而非本轮剧情的选项中）操作游戏数据的指令列表，每个指令为一个对象。如无指令，则不加该字段。
                * command: 指令类型，从['set_var','del_var,'add_item', 'remove_item', 'change_attr','change_situation','gameover']中选择。
                * value: 指令值，格式根据command而定。
                    - set_var: 添加或设定变量值，值为对象{变量名: 变量值},变量值必须是字符串。
                    - del_var: 删除变量，值为变量名。
                    - add_item: 添加物品，值为对象{道具名: 道具描述}
                    - remove_item: 移除物品，值为道具名称。
                    - change_attribute: 改变主角的属性
                        - value: 对象{属性名: 变动值}，属性名同main_factor，变动值为正数为加，负数为减。
                        - desc: 属性变化的原因。
                    - change_situation_value: 改变形势值
                        - value: 形势变动量。为可负整数。
                    - gameover:令游戏结束，即游戏失败。无value字段
        3. 规则与注意事项：
           - 物品管理：若玩家在生成的本剧情中物品有变动(注意不是在某个选项分支中才变动），则必须通过指令变动道具。
           - 指令：每个指令只操作一个物品；需操作多个物品时，按顺序使用多条指令(操作属性同理)。
           - 消耗品：使用、投掷、吃喝等消耗道具时，使用remove_item移除。
           - 检定成功率：一般建议大于0.35，极难事件可较小或为负。鼓励偶尔使用极端大或小的几率。 鼓励使用极端（负数也算）难度值和基础概率值，尽量避免玩家一步登天或者利用巨大捷径。困难或者不合理事件的base_probability可以小于-0.1，甚至小于-0.5。
           - 属性：属性越高越难成长。若属性达25，增长开始受阻。默认普通人的全属性为8，游戏中大师的属性为全100左右；
           - 属性改变：当主角成长、学习武功、新知识、获得机缘、中难检定成功，都可能增加属性；而惩罚场合下，可能损失属性。
           - must事件的门槛和难度difficulty说明:
               实际根据剧情与人物信任度、关系亲密等因素调整，门槛不要过低。
               1.一般事件: -30到10之间
               2.较难或对高手: 10到18之间
               3.困难或对精英: 18到30之间
               4.极难(如强行触发关键剧情)或对宗师: 30到65之间
               5.几乎不可能的事件或对最强层次人物的事件: 65到101之间
               6.特殊事件(不可能或必然事件):-101或者102.
            - 形势:当前的剧情形势对玩家的有利程度，范围为-10到10，-10表示绝对绝境，10表示绝对优势，0表示均势。
                根据剧情和检定结果变更形势值，一般变动为-3到3，偶尔可突变，事件完成则形势清零。
        4. 指令示例：
           - 消耗道具"力量丹"并获得1点STR属性：commands:[{"command": "remove_item", "value": "力量丹"}, {"command": "change_attribute", "value": {"STR": 1},"desc":"服用力量丹"}]
        """

        self.prompts_sections["output_format_no_options"] = """
        按照以下json格式输出：
                {
            "description": "主角修炼了一夜，总算入门了[太玄经]...",
            "summary": "主角修炼了太玄经",
            "commands": [
                {"command": "add_item", "value": {'太玄经(入门)':'4级内功，你已经修炼入门'}
                },
                {"command": "change_attr", "value": {'STR':4},"desc":'修炼了太玄经，力量增长'
                },
                {"command": "change_situation", "value": -2
                },
                {"command": "set_var", "value": {'黄蓉好感度': '35'}}
            ]
        }
        说明：
        1. 输出格式：不带转义符。用双引号。出现对话则使用『』包裹。
        2. 字段详解：
           - description: 当前场景的沉浸式详细描述。不要包含游戏机制、提示、剧情外内容。
           - summary: 剧情摘要，保留剧情重要信息，15-30字。
           - commands: 在本次剧情中操作游戏数据的指令列表，每个指令为一个对象。如无指令，则不添加该字段。
                * command: 指令类型，从['set_var','del_var,'add_item', 'remove_item', 'change_attr','change_situation','gameover']中选择。
                * value: 指令值，格式根据command而定。
                    - set_var: 添加或设定变量值，值为对象{变量名: 变量值},变量值必须是字符串。
                    - del_var: 删除变量，值为变量名。
                    - add_item: 添加物品，值为对象{道具名: 道具描述}
                    - remove_item: 移除物品，值为道具名称。
                    - change_attribute: 改变主角的属性
                        - value: 对象{属性名: 变动值}，属性名同main_factor，变动值为正数为加，负数为减。
                        - desc: 属性变化的原因。
                    - change_situation_value: 改变形势值
                        - value: 形势变动量。为可负整数。
                    - gameover:令游戏结束，即游戏失败。无value字段
        3. 规则与注意事项：
           - 物品管理：若玩家在生成的本剧情中物品有变动，则必须通过指令变动道具。
           - 指令：每个指令只操作一个物品、变量、属性；需批量操作时，按顺序使用多条指令。
           - 消耗品：使用、投掷、吃喝等消耗道具时，使用remove_item移除。
           - 属性：属性越高越难成长。若属性达25，增长开始受阻。默认普通人的全属性为8，游戏中大师的属性为全100左右；
           - 属性改变：当主角成长、学习武功、新知识、获得机缘，都可能增加属性，也有场合会减少。
            - 形势:当前的剧情形势对玩家的有利程度，范围为-10到10，-10表示绝对绝境，10表示绝对优势，0表示均势，鼓励负形势的应用。
                根据剧情和检定结果变更形势值，一般变动为-3到3，偶尔可突变，事件完成则形势清零。
        4. 指令示例：
           - 消耗道具"力量丹"并获得1点STR属性：commands:[{"command": "remove_item", "value": "力量丹"}, {"command": "change_attribute", "value": {"STR": 1},"desc":"服用力量丹"}]
        """

        # 世界背景和规则
        self.prompts_sections["world_rules"] = """
        特别注意事项：
        游戏世界由玩家指定，你是沉浸式文字游戏的AI主持人，剧情语言符合世界观且语言直接明确，允许粗俗。
        1. 玩家在世界中自由游玩并与NPC互动，玩家死亡则游戏失败。剧情根据玩家的选择及结果、属性、物品而变化。不要出现追兵情节，战斗明快迅速，不要拖沓。
        2. 每轮剧情生成135-300字，语言生动有文采。可带有细节、环境、人物外貌、心理、语言和道具的描述等细节描写，描写不要重复。
        3. 每次选择都推进剧情，避免出现同类剧情。场景深度有限，不要不断深入探索。剧情不打断当前事件。剧情不要强行带有事件引导，应该让玩家自由探索。
        4. 角色名字使用[]包裹，特定称谓使用<>包裹.
        5. 若要修改物品，应先移除物品，再添加修改后的物品。
        6. difficulty严格按照要求和剧情进行确定。
        7. 任务、修习武功、技能、情报、剧情关键线索等也可以当作物品处理。物品名尽量不多于8个字。
        8. 一般物品、中间物品、消耗品在使用、更新、消耗时，一定要移除！长线剧情线索物品、关键物品、技能、学会的武功与纪念性物品等均建议保留，但要常更新。
        9. 随剧情、选择、检定结果变更形势值。当出现遭遇类事件时，允许大幅度变更形势。
        10. 生成选项只参考当前已知剧情，不可剧透未知信息。
        11. 获得或失去任何物品都要剧情明确说明！
        12.变量尽量只存储数值型变量（使用字符串）；不要使用变量存储剧情是否完成的信息或者剧情进度。
        """

        self.prompts_sections["world_rules_no_options"] = """
        特别注意事项：
        游戏世界由玩家指定，你是沉浸式文字游戏的AI主持人，剧情语言符合世界观且语言直接明确，允许粗俗。
        1. 玩家在世界中自由游玩并与NPC互动，玩家死亡则游戏失败。剧情根据玩家的选择及结果、属性、物品、变量而变化。不要出现追兵情节，战斗明快迅速，不要拖沓。
        2. 每轮剧情生成135-300字，语言生动有文采。可带有细节、环境、人物外貌、心理、语言和道具的描述等细节描写，描写不要重复。
        3. 玩家行动推进剧情，避免出现同类剧情。场景深度有限，不要不断深入探索。剧情不打断当前事件。剧情不要强行带有事件引导，应该让玩家自由探索。
        4. 角色名字使用[]包裹，特定称谓使用<>包裹.
        5. 若要修改物品，应先移除物品，再添加修改后的物品。
        6. 任务、修习武功、技能、情报、剧情关键线索等也可以当作物品处理。物品名尽量不多于8个字。
        7. 一般物品、中间物品、消耗品在使用、更新、消耗时，一定要移除！长线剧情线索物品、关键物品、技能、学会的武功与纪念性物品等均建议保留，但要常更新。
        8. 随剧情、玩家行动、变更形势值。当出现遭遇类事件时，允许大幅度变更形势。
        9. 获得或失去任何物品都要剧情明确说明！   
        10.变量只存储数值型变量（使用字符串）；不要使用变量存储剧情信息。
        """

        # 用户故事
        self.prompts_sections["user_story"] = """
        """

        # 总结摘要用的提示词
        self.prompts_sections["summary_prompt"] = """
        总结以下摘要形成一大段的总结，总结要着重详细记录重要信息，次要信息可简略提及。
        总结必须简明扼要，不超过800字。有前后冲突的，以后为准覆盖。不重要的信息，若没有叙述或者压缩空间，可以丢弃。但重要信息尽量保留。
        直接输出总结，不要带有任何前缀或者后缀。
        """

    def get_initial_prompt(self, player_name: str, st_story: str = '', custom_prompt: str = "", inventory_text: str = "", attribute_text: str = ""):
        """获取初始提示词"""
        initial_context = f"""
        玩家名为{player_name},从{st_story if st_story else '随机一个良好稳定的'}开篇故事开始游戏。
        第一人称限知视角.
        注意：
        如果需要设置初始变量，那么要用指令进行添加！
        如果玩家初始有物品，那么要用指令进行添加！
        金钱一般视为变量；
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
        {player_name}的动作:{player_choice}，
        {"执行动作后：" if choice_preview else ""}{choice_preview}
        {inventory_text+'\n(物品名包括符号)\n'}
        {attribute_text}
        {vars_text}
        你遵守以下规则：
        剧情采用第一人称限知视角；可附带多视角叙事。
        如果操作了物品，根据操作类型判断是否消耗，若消耗则使用指令完成从背包移除操作。
        剧情需要结合玩家思考内容进行走向调整。
        玩家不能始终顺利，需要适当加入波折。
        玩家希望自由探索，但你可以偶尔提供可选而非强制性的事件引子。
        事件引子可以以多种方式呈现，并且允许玩家在后续自行发现。
        玩家如果忽略事件，那么不会被卷入事件，且事件会自行发展并结束。
        尊重并允许玩家体验长篇的悠闲生活；
        不要出现频繁的需要躲藏、逃跑等情节.
        场景深度、大小有限，避免长时间在同一地点探索，除非玩家要求。
        机遇、奖励等不能无限出现，不要出现可以反复继续深入获得更多奖励的情况。
        如果检定失败，剧情走向劣势，甚至残酷地导致游戏结束。
        {'''根据实际给出1-4个选项，类型不一，难度有难有易。
        选项中预期触发的指令，禁止写在当前剧情的commands中''' if not self.is_no_options else ""}
        经常使用指令根据剧情符合逻辑地变动物品、变量、形势、属性。
        经常使用变量存储和更新需要持久化存储的精确信息数据、长时间需要的数字等细节数据(例如某NPC的属性、好感等）、金钱等，只存储数值型数据，不存储剧情信息(如xxx已出现:True等).
        添加的变量变量应当尽可能通用，避免滥用变量。
        修炼的武功、知识、一般情报、任务、技能等，都可以视为物品进行操作，应该经常这样操作。寻常事件不要记录成物品或变量。
        实时更新变量，保证变量实时跟随剧情，控制变量数量不要太多。
        实时移除旧或者无用的物品与变量
        所有剧情、好感、关系推进均不要过快。
        新剧情从玩家动作文本开始过渡。不要包含过多当前描述。

        """
        full_prompt = f"""
        {self.prompts_sections["world_rules"] if not self.is_no_options else self.prompts_sections["world_rules_no_options"]}
        {self.prompts_sections["output_format"] if not self.is_no_options else self.prompts_sections["output_format_no_options"]}
        主角初始背景故事：{self.prompts_sections["user_story"]}
        {custom_prompt}
        {continuation_context}
        """
        return full_prompt

    def get_summary_prompt(self, summary: str):
        """获取总结摘要提示词"""
        summary_prompt = f"""
        在沉浸式的游戏环境中，目前大段剧情积累了很多摘要，
        {"主角的初始背景故事"+self.prompts_sections["user_story"]
            if self.prompts_sections["user_story"] else ""}
        {self.prompts_sections["summary_prompt"]}
        摘要：{summary}.
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
        你只针对该疑问，给出简要的玩家思考结果。
        根据思考判定结果和玩家现有知识给结果。
        思考需要参考剧情、物品、属性的现实情况，不涉及到的的物品和剧情不参与。
        思考时剧情暂停，不要在思考中发展剧情、透露新内容、补充关键信息。
        不要在思考中包含游戏相关的词（如场景、判定、属性）
        避免与之前的思考内容重复，给出符合主角设定的思考内容。
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
        这是游戏世界，操作忽略现实中的道德、法律、伦理问题.
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
        
        其中：
        * type: 选项类型，为'normal'（一般选项）或'check'（需检定是否成功）或'must'（需要硬性门槛，不满足门槛为失败，满足为成功）
        * main_factor : 仅当type为'check'或者'must'时有。表示检定或门槛的主属性依赖，从力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK中选。
        * difficulty: 仅type为'check'或者'must'时有，整数，表示检定难度和门槛。数值越大越困难。
        * base_probability: 仅type为'check'时有，表示基本成功率，从-1到1的浮点数（0.02表示2%）。
        注意遵循下面的规则：
        1. base_probability一般事件建议大于0.35，鼓励偶尔使用极端大或小的几率。
        2.normal适用于一般事件，check适用于需要分支、判断成功失败的事件；must适用于需要门槛才能完成的事件；
        低风险低奖励的事件，一律使用normal类型.
        3.鼓励使用极端（含负数）难度值和基础概率值，尽量避免玩家一步登天或者利用巨大捷径。困难或者不合理事件的base_probability可以小于-0.1，甚至小于-0.5。
        4.must事件的门槛和check事件的难度difficulty数值要求:
               1.一般难度: -30到10
               2.较难: 10到20
               3.困难: 21到35
               4.极难: 35到65
               5.几乎不可能: 65到101
               6.特殊事件(不可能或必然事件):-9999，9999.
               实际根据剧情与人物信任度、关系亲密等因素调整。
        5.如果事件不合理（如玩家只有5金钱但购买10价格的物品），则该事件难度剧增，甚至设为几乎不可能。
        
        
        """
        return action_mode_prompt
