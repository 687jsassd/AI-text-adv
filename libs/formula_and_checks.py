"""
基础组件
游戏引擎中各个公式和检定
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

import random
from libs.animes import probability_check_animation
from libs.animes_rich import console


class GameFormulas:
    """
    各公式
    """

    def __init__(self):
        pass


class GameChecks:
    """
    各检定
    """

    def __init__(self):
        pass

    # 基础-概率判定函数

    def probability_check(self, target: float,
                          is_enable_normal: bool = False,
                          normal_range_factor: float = 0.1,
                          is_enable_double_check: bool = False,
                          first_check_factor: float = 0.65,
                          second_check_factor: float = 1.00,
                          allow_base_first_success: bool = True,
                          big_failure_prob_addon: float = 0.20,
                          is_enable_final_chance: bool = False,
                          final_chance_prob: float = 0.05,
                          final_chance_target: float = 0.05,
                          first_check_anime_duration: float = 2.0,
                          second_check_anime_duration: float = 2.0,
                          final_chance_anime_duration: float = 2.0,
                          ):
        """
        概率判定函数
        target:目标值 0-1
        is_enable_normal: 是否允许"不成功也不失败"的情况
        normal_range_factor: 上述情况所占范围系数(为目标值左右范围)
        is_enable_double_check: 是否启用二次判定,如不启用则只判定一次
            若启用，则返回值分别为3,1,-1或-3，分别表示大成功、小成功、小失败、大失败
            否则，返回2或-2，表示成功、失败
        first_check_factor:二次判定中第一次判定的目标值系数
        second_check_factor二次判定中第二次判定的目标值系数
        allow_base_first_success: 是否允许第一次判定中保底有1%的概率
        big_failure_prob_addon: 大失败当判定中最小值大于目标值多少才会触发
        is_enable_final_chance: 是否启用最后机会
        final_chance_prob: 最后机会触发概率
        final_chance_target: 最后机会的目标值
        """
        result = 0
        if is_enable_double_check:
            first_result, second_result = 0, 0
            first_target = target * first_check_factor
            if allow_base_first_success:
                first_target = max(first_target, 0.01)
            rand_first = random.uniform(0, 1)
            console.rule(
                "第一次检定 - [bold blue]大成功[/bold blue]/[bold yellow]第二次机会[/bold yellow]",
                style="bold green")
            probability_check_animation(
                rand_first,
                target_prob=first_target,
                duration=max(0.1, first_check_anime_duration),
                color_preset=1
            )
            if rand_first < first_target:
                first_result = 1

            if first_result == 1:
                return 3  # 第一次就成功，则大成功

            second_target = target * second_check_factor
            if allow_base_first_success:
                second_target = max(second_target, 0.01)
            rand_second = random.uniform(0, 1)
            console.rule(
                "第二次检定 - [bold green]小成功[/bold green]/[bold red]失败[/bold red]",
                style="bold red")
            probability_check_animation(
                rand_second,
                target_prob=second_target,
                duration=max(0.1, second_check_anime_duration),
                color_preset=2
            )
            if rand_second < second_target:
                second_result = 1

            if second_result == 1:
                return 1  # 第二次才成功，则小成功

            if is_enable_normal and abs(rand_first - target) < normal_range_factor:
                return 0  # 不成功不失败

            if min(rand_first, rand_second) < target + big_failure_prob_addon:
                result = -1  # 小失败

            else:
                result = -3  # 大失败

        else:
            rand = random.uniform(0, 1)
            probability_check_animation(
                rand,
                target_prob=target,
                duration=max(0.1, first_check_anime_duration)
            )
            if rand < target:
                return 2  # 成功

            if is_enable_normal and abs(rand - target) < normal_range_factor:
                return 0  # 不成功不失败

            else:
                result = -2  # 失败

        # 最后机会
        # 随机数决定是否启用
        if not is_enable_final_chance:
            return result

        enable_final_chance_prob = random.uniform(0, 1)
        if enable_final_chance_prob < final_chance_prob:
            console.rule(
                "[bold magenta]最后机会[/bold magenta]",
                style="bold purple")
            final_chance_rand = random.uniform(0, 1)
            probability_check_animation(
                final_chance_rand,
                target_prob=final_chance_target,
                duration=max(0.1, final_chance_anime_duration)
            )
            if final_chance_rand < final_chance_target:
                return 1  # 小成功
        return result
