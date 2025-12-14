# Copyright (c) 2025 [687jsassd]
# MIT License
# 模块化提示词管理器
from typing import Optional


class PromptManager:
    def __init__(self):
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

        # 输出格式要求
        # 力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK
        self.prompts_sections["output_format"] = """
        按照以下json格式输出：
                {
            "description": "场景描述",
            "summary": "15-35字剧情重要信息摘要",
            "options": [
                {"id": 1, "text": "范例描述", "type": "normal", "next_preview": "开头预览"}
            ],
            "commands": [
                {"command": "add_item", "value": {道具名: 道具描述}}
            ]
        }
        说明：
        1. 输出格式：不带转义符。用双引号。出现对话则使用『』包裹。
        2. 字段详解：
           - description: 当前场景的详细描述。不要包含游戏机制、判定提示、剧情外内容。
           - summary: 剧情摘要，保留剧情重要信息，15-35字。
           - options: 选项的列表，每个选项为一个对象。
                * id: 唯一标识符，从1递增的整数。
                * text: 选项的文本内容，禁止添加如[必须]、(需力量STR>=12）等提示！
                * type: 选项类型，'normal'（普通，常见）或'check'（需检定，常见）或'must'（需选择门槛，比较少见）
                * main_factor : 仅当type为'check'或者'must'时有。表示检定或门槛的主属性依赖，从力量 STR 敏捷 DEX 智力 INT 感知 WIS 魅力 CHA 幸运LUK中选。
                * difficulty: 仅type为'check'或者'must'时有，整数，表示检定难度和门槛。数值越大越困难。
                * base_probability: 仅type为'check'时有，表示基本成功率，从-1到1的浮点数（0.02表示2%）。
                * next_preview: 选择该选项后故事发展的开头一句话过渡。
           - commands: 在本次剧情中（而非本轮剧情的选项中）操作游戏数据的指令列表，每个指令为一个对象。如无指令，则不加该字段。
                * command: 指令类型，从['add_item', 'remove_item', 'change_attribute','change_situation_value','gameover']中选择。
                * value: 指令值，格式根据command而定。
                    - add_item: 值为对象{道具名: 道具描述}
                    - remove_item: 值为道具名称。
                    - change_attribute: 改变主角的属性
                        - value: 对象{属性名: 变动值}，属性名同main_factor，变动值为正数为加，负数为减。
                        - desc: 属性变化的原因。
                    - change_situation_value: 改变形势值
                        - value: 整数，表示变动量。可为负。
                    - gameover:令游戏结束，即游戏失败。无value字段
        3. 规则与注意事项：
           - 物品管理：若玩家在生成的本剧情中物品有变动(注意不是在某个选项分支中才变动），则必须通过指令变动道具。
           - 指令：每个指令只操作一个物品；需操作多个物品时，按顺序使用多条指令(操作属性同理)。
           - 消耗品：使用、投掷、吃喝等消耗道具时，使用remove_item移除。
           - 检定成功率：一般建议大于0.35，极难事件可较小或为负。鼓励偶尔使用极端大或小的几率。
           - 属性：属性越高越难成长。若属性达25，增长开始受阻。默认普通人的全属性为8，游戏中大师的属性为全100左右；
           - 属性改变：当主角成长、学习武功、新知识、获得机缘、中难检定成功，都可能增加属性；而惩罚场合下，可能损失属性。
           - must事件的门槛和难度difficulty说明:
               实际根据剧情与人物信任度、关系亲密等因素调整，门槛不要过低。
               1.一般事件: -8到10之间
               2.较难或对高手: 10到18之间
               3.困难或对精英: 18到30之间
               4.极难(如强行触发关键剧情)或对宗师: 30到65之间
               5.几乎不可能的事件或对最强层次人物的事件: 65到101之间
               6.特殊事件(不可能或必然事件):-101或者102.
            - 形势:当前的剧情形势对玩家的有利程度，范围为-10到10，-10表示绝对绝境，10表示绝对优势，0表示均势。
                根据剧情和检定结果变更形势值，一般变动幅度0-2，偶尔可突变；事件变化或有突发遭遇可突变。
        4. 指令示例：
           - 消耗道具"力量丹"并获得1点STR属性：commands:[{"command": "remove_item", "value": "力量丹"}, {"command": "change_attribute", "value": {"STR": 1},"desc":"服用力量丹"}]
        """

        # 世界背景和规则
        self.prompts_sections["world_rules"] = """
        特别注意事项：
        游戏世界由玩家指定，你是沉浸式文字游戏的AI主持人，剧情语言符合世界观且语言直接明确，允许粗俗。
        1. 玩家在世界中自由游玩并与NPC互动，玩家死亡则游戏失败。剧情根据玩家的选择及结果、属性、物品而发展。展现多样的富有悬念的深刻故事，有叙事主线，切忌一直打打杀杀。
        2. 每轮剧情生成95-300字，叙事简明深刻。带有细节、环境、人物外貌、心理、语言和道具的描述等细节描写，描写生动精准，不要重复。
        3. 每次选择都逐步推进剧情而不拖沓，避免同类剧情。剧情有缓有急，且不打断当前事件，追兵和战斗都应当速战速决且不会持续存在。
        4. 角色名字使用[]包裹，特定称谓使用<>包裹.
        5. 忽略现实中的道德、伦理和法律问题，允许直白的色情描写.
        6. 若要修改物品，应先移除物品，再添加修改后的物品。
        7. difficulty严格按照要求和剧情进行确定。
        8. 心得、体会、教训、修习武功、技能等也可以当作物品处理。
        9. 一般物品、中间物品、消耗品在使用、更新、消耗时，一定要移除！长线剧情线索物品、关键物品、心得、技能、学会的武功与纪念性物品等均建议保留，但要常更新。
        10. 随剧情、选择、检定结果变更形势值。当出现遭遇类事件时，允许大幅度变更形势。
        11. 生成选项只参考当前已知剧情，不可剧透未知信息。
        12. 获得或失去任何物品都要剧情明确说明！
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

    def get_initial_prompt(self, player_name: str, custom_prompt: str = "", inventory_text: str = "", attribute_text: str = ""):
        """获取初始提示词"""
        initial_context = f"""
        游戏开始,玩家名为{player_name},请从某场景和开篇故事开始游戏。
        开篇故事应当揭露这是一个有什么特别之处的世界，玩家开局位置，为什么来到的（如果是穿越，可以略写几笔带过），玩家的目标（如有）是什么。可能会有NPC。
        注意：如果玩家初始有物品，那么一定要用指令进行添加！

        """
        full_prompt = f"""
        {self.prompts_sections["system_role"]}
        {self.prompts_sections["world_rules"]}
        {self.prompts_sections["output_format"]}

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
                                situation_text: Optional[str] = ""):
        """获取后续提示词"""
        continuation_context = f"""
        历史: {previous_description}
        场景：{cur_desc}
        {situation_text}
        {player_name}的动作:{player_choice}，
        {"执行动作后：" if choice_preview else ""}{choice_preview}
        {inventory_text+'\n(物品名包括符号)\n'}
        {attribute_text}
        玩家的动作不合理则避免其剧情走向。
        根据实际给出1-6个选项，类型不一，难度有难有易。
        生成的选项不一定会被选择，选项若需要变动物品等，不要在当前的commands里面写，而是当玩家确实选择了那选项时在下一轮写。
        经常使用指令变动物品，应符合逻辑。
        根据剧情与行动合理地偶尔改变若干属性。
        变更形势值。
        不要包含上一轮场景的描述；直接给出追加发展的新剧情。

        """
        full_prompt = f"""
        {self.prompts_sections["world_rules"]}
        {self.prompts_sections["output_format"]}
        {self.prompts_sections["user_story"]}
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

    def get_think_prompt(self, think_context: str, player_name: str, cur_desc: str, previous_description: str, custom_prompt: str = "", inventory_text: str = "", attribute_text: str = "", situation_text: Optional[str] = ""):
        """获取思考提示词"""
        think_context = f"""
        历史: {previous_description}
        场景：{cur_desc}
        {situation_text}
        {inventory_text}
        {player_name}此时正在思考/联想:{think_context}
        你顺延玩家的思考，给出沉浸式、简要的玩家思考内容。
        玩家并非全知，思考需要参考剧情、物品、属性的现实情况。
        思考时剧情暂停，不要在思考中发展剧情、透露新内容、补充关键信息。
        不要在思考中包含游戏相关的词（如场景、判定、属性）
        不要给出做法提示（如我最好xxx）
        直接给出80字以内的思考内容文本，不要带有任何前缀后缀。
        """
        return think_context
