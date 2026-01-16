from libs.prompt_manager import PromptManagerRebuild, PromptSection

# 文件名规则：
# s_开头，只影响start提示词
# c_开头，只影响continue提示词
# sum_开头，只影响summary提示词
# 其他情况，默认影响所有提示词


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
        prompt_manager.add_prompt(section, "custom1", prompt)
    prompt_manager.save_to_json("./customprompt/custom1.json")

    prompt_manager = PromptManagerRebuild("./customprompt/custom1.json")
    print(prompt_manager.get_full_prompt())


create_custom_prompt()
