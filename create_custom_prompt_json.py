import os
from libs.prompt_manager import PromptManagerRebuild, PromptSection
# 作用域AREA
# 'start' :首轮对话
# 'continue' :后续对话
# 'summary' :总结

# 下为一示例

AREA = ['start', 'continue']
ID = "MultiWords"  # 影响提示词ID和文件名
DESC = "语言多样化"  # 该自定义提示词集描述


def create_custom_prompt():
    # 自定义提示词创建
    prompt_manager = PromptManagerRebuild()
    init_prompt = {
        PromptSection.PRE_PROMPT: """
        """,
        PromptSection.BODY_PROMPT: """
        """,
        PromptSection.POST_PROMPT: """
        【剧情语言风格的多样化要求】
        玩家输入的话语可能是诙谐幽默、搞怪等，具有不同的气氛，
        需要合理地纠正NPC的反应，以加强剧情的丰富性和趣味性。
        允许NPC因为对玩家态度的改变或者受玩家语言、行动的影响而改变其行为或语言。
        
        【世界与NPC演变】
        玩家的语言、行动、决策等可能会影响到NPC的行为和世界，进而获得不同反馈。
        完成动态的世界变化，例如NPC的情感状态、行为模式等，保证剧情的连贯性和吸引力。
        """
    }
    for section, prompt in init_prompt.items():
        prompt_manager.add_prompt(section, ID, prompt)

    os.makedirs("./customprompt", exist_ok=True)

    prompt_manager.save_to_json(
        f"./customprompt/{ID}.json", id=ID, desc=DESC, areas=AREA)

    prompt_manager = PromptManagerRebuild(f"./customprompt/{ID}.json")
    print(prompt_manager.get_full_prompt())


create_custom_prompt()
