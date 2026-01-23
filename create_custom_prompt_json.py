from libs.prompt_manager import PromptManagerRebuild, PromptSection
import os
# 文件名规则：
# s_开头，只影响start提示词
# c_开头，只影响continue提示词
# sum_开头，只影响summary提示词
# 其他情况，默认影响所有提示词

AREA = "s_"  # s_或c_或sum_或其他
ID = "custom1"  # 影响提示词ID和文件名
DESC = "测试用"  # 该自定义提示词集描述


def create_custom_prompt():
    # 自定义提示词创建
    prompt_manager = PromptManagerRebuild()
    init_prompt = {
        PromptSection.PRE_PROMPT: """
        """,
        PromptSection.BODY_PROMPT: """
        123456
        """,
        PromptSection.POST_PROMPT: """
        """
    }
    for section, prompt in init_prompt.items():
        prompt_manager.add_prompt(section, ID, prompt)

    # 创建目录
    os.makedirs("./customprompt", exist_ok=True)

    prompt_manager.save_to_json(
        f"./customprompt/{AREA}{ID}.json", id=ID, desc=DESC)

    prompt_manager = PromptManagerRebuild(f"./customprompt/{AREA}{ID}.json")
    print(prompt_manager.get_full_prompt())


create_custom_prompt()
