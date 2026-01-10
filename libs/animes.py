"""
提供同步加载动画类，用于在AI生成或加载时显示等待动画
"""
# Copyright (c) 2025 [687jsassd]
# MIT License

from typing import Optional, Callable
import threading
import time
from datetime import datetime
import sys
from logging import getLogger
from libs.practical_funcs import TO_ANSI_COLORS, replace_color_code

logger = getLogger(__name__)


class SyncLoadingAnimation:
    """
    同步加载动画类，用于在AI生成或加载时显示等待动画
    完全兼容现有的同步代码环境
    """

    def __init__(self):
        self.is_running = False
        self.animation_thread = None
        self.stop_event = threading.Event()

    def spinner_animation(self,
                          message: str = "等待世界回应",
                          delay: float = 0.1,
                          spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
                          color: str = "\033[94m",  # 蓝色
                          reset_color: str = "\033[0m") -> None:
        """
        旋转动画效果

        Args:
            message: 显示的消息
            delay: 动画帧之间的延迟（秒）
            spinner_chars: 旋转字符序列
            color: 颜色代码
            reset_color: 颜色重置代码
        """
        spinner_idx = 0
        start_time = datetime.now()

        while not self.stop_event.is_set():
            # 计算已等待时间
            elapsed = (datetime.now() - start_time).total_seconds()
            time_str = f" ({elapsed:.1f}s)"

            # 显示当前帧
            spinner = spinner_chars[spinner_idx % len(spinner_chars)]
            sys.stdout.write(
                f"\r{color}{spinner}{reset_color} {message}{time_str}")
            sys.stdout.flush()

            # 更新索引
            spinner_idx += 1
            time.sleep(delay)

    def dot_animation(self,
                      message: str = "等待世界回应",
                      delay: float = 0.3,
                      max_dots: int = 3,
                      color: str = "\033[92m",  # 绿色
                      reset_color: str = "\033[0m") -> None:
        """
        点状动画效果

        Args:
            message: 显示的消息
            delay: 点之间的延迟（秒）
            max_dots: 最大点数
            color: 颜色代码
            reset_color: 颜色重置代码
        """
        dot_count = 0
        start_time = datetime.now()

        while not self.stop_event.is_set():
            # 计算已等待时间
            elapsed = (datetime.now() - start_time).total_seconds()
            time_str = f" ({elapsed:.1f}s)"

            # 显示当前点状态
            dots = "." * (dot_count % (max_dots + 1))
            sys.stdout.write(
                f"\r{color}Wait{reset_color} {message}{time_str}{dots}        ")
            sys.stdout.flush()

            # 更新点数
            dot_count += 1
            time.sleep(delay)

    def progress_bar_animation(self,
                               message: str = "等待世界回应",
                               delay: float = 0.2,
                               bar_length: int = 20,
                               color: str = "\033[93m",  # 黄色
                               reset_color: str = "\033[0m") -> None:
        """
        进度条动画效果

        Args:
            message: 显示的消息
            delay: 动画帧之间的延迟（秒）
            bar_length: 进度条长度
            color: 颜色代码
            reset_color: 颜色重置代码
        """
        progress = 0
        start_time = datetime.now()

        while not self.stop_event.is_set():
            # 计算已等待时间
            elapsed = (datetime.now() - start_time).total_seconds()
            time_str = f" ({elapsed:.1f}s)"

            # 计算进度（循环显示）
            progress = (progress + 1) % (bar_length + 1)
            barr = "█" * progress + "░" * (bar_length - progress)
            percentage = int((progress / bar_length) * 100)

            # 显示进度条
            sys.stdout.write(
                f"\r{color}Wait{reset_color} {message} [{barr}] {percentage}%{time_str}")
            sys.stdout.flush()

            time.sleep(delay)

    def typewriter_loading(self,
                           message: str = "等待世界回应",
                           base_text: str = "请稍候",
                           delay: float = 0.1,
                           color: str = "\033[95m",  # 紫色
                           reset_color: str = "\033[0m") -> None:
        """
        打字机风格的加载动画

        Args:
            message: 主要消息
            base_text: 基础文本
            delay: 字符之间的延迟（秒）
            color: 颜色代码
            reset_color: 颜色重置代码
        """
        suffixes = ["", ".", "..", "..."]
        suffix_idx = 0
        start_time = datetime.now()

        while not self.stop_event.is_set():
            # 计算已等待时间
            elapsed = (datetime.now() - start_time).total_seconds()
            time_str = f" ({elapsed:.1f}s)"

            # 显示当前状态
            current_suffix = suffixes[suffix_idx % len(suffixes)]
            sys.stdout.write(
                # 空格是把之前文字的刷掉
                f"\r{color}Wait{reset_color} {message}: {base_text}{current_suffix}{time_str}        ")
            sys.stdout.flush()

            # 更新后缀
            suffix_idx += 1
            time.sleep(delay)

    def start_animation(self,
                        animation_type: str = "spinner",
                        **kwargs) -> None:
        """
        开始动画

        Args:
            animation_type: 动画类型 (spinner, dots, progress, typewriter)
            **kwargs: 动画参数
        """
        if self.is_running:
            self.stop_animation()

        self.is_running = True
        self.stop_event.clear()

        # 选择动画类型
        animation_func = {
            "spinner": self.spinner_animation,
            "dots": self.dot_animation,
            "progress": self.progress_bar_animation,
            "typewriter": self.typewriter_loading
        }.get(animation_type, self.spinner_animation)

        # 在新线程中运行动画
        self.animation_thread = threading.Thread(
            target=animation_func,
            kwargs=kwargs,
            daemon=True
        )
        self.animation_thread.start()

    def stop_animation(self) -> None:
        """
        停止动画并清理屏幕
        """
        if self.is_running:
            self.stop_event.set()
            self.is_running = False

            # 等待动画线程结束
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join(timeout=1.0)

            # 清理屏幕
            sys.stdout.write("\r" + " " * 100 + "\r")
            sys.stdout.flush()


# 便捷函数
def show_loading_animation(animation_type: str = "spinner",
                           duration: Optional[float] = None,
                           **kwargs):
    """
    显示加载动画的便捷函数（同步版本）

    Args:
        animation_type: 动画类型
        duration: 动画持续时间（秒），None表示需要手动停止
        **kwargs: 动画参数
    """
    loader = SyncLoadingAnimation()

    try:
        loader.start_animation(animation_type, **kwargs)

        if duration:
            time.sleep(duration)
            loader.stop_animation()
        else:
            # 返回loader对象，需要手动调用stop_animation
            return loader

    except Exception as e:
        loader.stop_animation()
        raise e


def typewriter_effect(text: str,
                      delay: float = 0.02,
                      newline_delay: float = 0.1,
                      on_char_typed: Optional[Callable] = None,
                      on_complete: Optional[Callable] = None) -> bool:
    """
    打字机效果输出文本

    Args:
        text: 要输出的文本
        delay: 每个字符之间的延迟（秒）
        newline_delay: 换行后的额外延迟（秒）
        on_char_typed: 每输入一个字符时的回调函数
        on_complete: 完成时的回调函数

    Returns:
        bool: 是否被用户中断
    """
    skip_event = threading.Event()
    interrupted = False

    try:
        lines = text.split('\n')
        for line_idx, line in enumerate(lines):
            if skip_event.is_set():
                interrupted = True
                break

            # 输出当前行的所有字符
            for char_idx, char in enumerate(line):
                if skip_event.is_set():
                    interrupted = True
                    break

                sys.stdout.write(char)
                sys.stdout.flush()

                # 调用字符输入回调
                if on_char_typed:
                    on_char_typed(char, char_idx, line_idx)

                time.sleep(delay)

            # 如果不是最后一行，添加换行和延迟
            if line_idx < len(lines) - 1:
                if not skip_event.is_set():
                    time.sleep(newline_delay)

        # 调用完成回调
        if on_complete and not interrupted:
            on_complete()

    except KeyboardInterrupt:
        interrupted = True
        print("\n输出被中断")

    return interrupted


def typewriter_narrative(text: str,
                         prefix: str = "",
                         suffix: str = "",
                         color: str = "",
                         reset_color: str = "\033[0m",
                         delay: float = 0.01) -> bool:
    """
    专门用于游戏叙述的打字机效果

    Args:
        text: 叙述文本
        prefix: 前缀（如分隔线）
        suffix: 后缀
        color: 颜色代码
        reset_color: 颜色重置代码

    Returns:
        bool: 是否被用户中断
    """
    if prefix:
        print(prefix)
    if color and color in TO_ANSI_COLORS:
        color = TO_ANSI_COLORS[color]
    if not color.startswith("\033[") or not reset_color.startswith("\033["):
        logger.warning(
            "[打字机动画]颜色代码 %s 或 %s 不是ANSI颜色代码，已重置为默认值",
            color, reset_color)
        color = ""
        reset_color = ""

    # 添加颜色
    colored_text = f"{color}{text}{reset_color}" if color else text

    # 使用打字机效果
    interrupted = typewriter_effect(
        colored_text,
        delay=delay,
        newline_delay=0.05,
    )

    if suffix and not interrupted:
        print(suffix)

    return interrupted


def display_narrative_with_typewriter(narr: str,
                                      separator: str = "",
                                      color: str = "") -> bool:
    """
    增强版的叙述显示函数，带有打字机效果

    Args:
        narr: 叙述文本
        separator: 分隔线
        color: 颜色代码

    Returns:
        bool: 是否被用户中断
    """
    # 替换文本中的颜色代码为ANSI的
    narr = replace_color_code(narr)

    paras = narr.split("\n")
    interrupted = False  # 这里关闭中断功能

    for para in paras:
        if para.strip() and not interrupted:
            para_interrupted = typewriter_narrative(
                para.strip(),
                color=TO_ANSI_COLORS.get(color, color),
                suffix="\n"
            )
            if para_interrupted:
                interrupted = True
                break

    if not interrupted:
        print(separator)

    return interrupted


def probability_check_animation(success_prob: float,
                                target_prob: float,
                                duration: float = 2.0,
                                color_threshold: str = "\033[93m",  # 黄色
                                color_success: str = "\033[92m",  # 绿色
                                color_fail: str = "\033[91m",     # 红色
                                color_bar: str = "\033[97m",      # 白色
                                reset_color: str = "\033[0m",
                                color_preset: int = 0) -> None:
    """
    概率检定动画，显示成功概率和实际结果的对比

    Args:
        success_prob: 实际成功概率
        target_prob: 目标成功概率
        duration: 动画持续时间（秒）
        color_threshold: 阈值位置的颜色
        color_success: 成功时的颜色
        color_fail: 失败时的颜色
        color_normal: 正常颜色
        color_bar: 进度条颜色
        reset_color: 颜色重置代码
        color_preset: 配色方案编号(1: 成功蓝色，失败黄色；2: 成功绿色，失败红色)
    """
    # 配色方案预设
    for i in [color_threshold, color_success, color_fail, color_bar]:
        if i in TO_ANSI_COLORS:
            i = TO_ANSI_COLORS[i]
    if not all(color.startswith('\033[') or color.startswith('\x1b[') for color in [color_threshold, color_success, color_fail, color_bar]):
        raise ValueError(
            f"颜色代码必须以'\033['开头,这个动画不支持rich的颜色代码 |你的代码:{[i for i in [color_threshold, color_success, color_fail, color_bar] if not i.startswith('\033[') and not i.startswith('\x1b[')]}")
    if color_preset == 1:  # 成功蓝色，失败黄色
        color_success = "\033[94m"  # 蓝色
        color_fail = "\033[93m"  # 黄色
    elif color_preset == 2:  # 成功绿色，失败红色
        color_success = "\033[92m"  # 绿色
        color_fail = "\033[91m"  # 红色

    is_success = success_prob < target_prob
    result_color = color_success if is_success else color_fail
    result_text = "✓ 成功" if is_success else "✗ 失败"

    bar_length = 30
    threshold_pos = int(target_prob * bar_length)

    # 确保位置在合理范围内
    threshold_pos = max(0, min(threshold_pos, bar_length))

    start_time = time.time()
    end_time = start_time + duration

    while time.time() < end_time:
        elapsed = time.time() - start_time
        progress = min(elapsed / duration, 1.0)

        # 使用缓动函数使当前概率从0增长到实际概率
        t = progress
        if t < 0.9:
            # 缓动函数：先快后慢
            current_prob = success_prob * (1 - (1 - (t / 0.9)) ** 3)
        else:
            # 最后10%的时间微调到实际概率
            current_prob = success_prob

        # 根据当前概率计算填充长度
        filled_length = int(bar_length * min(current_prob, 1.0))
        filled_length = min(filled_length, bar_length)

        # 构建进度条
        d_bar = ""
        for i in range(bar_length):
            if i < threshold_pos:
                # 阈值前的格子
                if i < filled_length:
                    # 已填充部分
                    if current_prob <= target_prob:
                        d_bar += f"{color_success}█{reset_color}"
                    else:
                        d_bar += f"{color_fail}█{reset_color}"
                else:
                    # 未填充部分
                    if i == threshold_pos - 1 and threshold_pos < bar_length:
                        d_bar += f"{color_threshold}║{reset_color}"
                    else:
                        d_bar += f"{color_bar}░{reset_color}"
            else:
                # 阈值后的格子
                if i < filled_length:
                    # 已填充部分
                    if current_prob <= target_prob:
                        d_bar += f"{color_success}█{reset_color}"
                    else:
                        d_bar += f"{color_fail}█{reset_color}"
                else:
                    # 未填充部分
                    d_bar += f"{color_bar}░{reset_color}"

        # 概率颜色
        if current_prob <= target_prob:
            prob_color = color_success
        else:
            prob_color = color_fail

        # 清除行并输出
        sys.stdout.write("\033[K")  # 清除当前行
        # 显示当前概率值而不是时间进度
        sys.stdout.write(
            f"\r🎲 检定中: [{d_bar}] {prob_color}{current_prob:.3f}{reset_color}/{target_prob:.3f}")
        sys.stdout.flush()

        time.sleep(0.05)

    # 最终进度条
    final_filled_length = int(bar_length * min(success_prob, 1.0))
    d_bar = ""
    for i in range(bar_length):
        if i < threshold_pos:
            if i < final_filled_length:
                # 已填充部分
                if success_prob <= target_prob:
                    d_bar += f"{color_success}█{reset_color}"
                else:
                    d_bar += f"{color_fail}█{reset_color}"
            else:
                # 未填充部分
                if i == threshold_pos - 1 and threshold_pos < bar_length:
                    d_bar += f"{color_threshold}║{reset_color}"
                else:
                    d_bar += f"{color_bar}░{reset_color}"
        else:
            if i < final_filled_length:
                # 已填充部分
                d_bar += f"{color_fail}█{reset_color}"
            else:
                # 未填充部分
                d_bar += f"{color_bar}░{reset_color}"

    # 最终显示
    sys.stdout.write("\033[K")  # 清除当前行
    sys.stdout.write(f"\r{result_color}{result_text}{reset_color}: ")
    sys.stdout.write(f"[{d_bar}] ")
    sys.stdout.write(f" {result_color}{success_prob:.3f}{reset_color}")
    sys.stdout.write(f"/{target_prob:.3f}     ")  # 空格是把之前文字的刷掉
    sys.stdout.flush()
    print()


if __name__ == "__main__":
    # print("各类动画测试")
    # anime_loader = SyncLoadingAnimation()
    # anime_loader.start_animation("spinner")
    # time.sleep(2)
    # anime_loader.stop_animation()
    # anime_loader.start_animation("progress")
    # time.sleep(2)
    # anime_loader.stop_animation()
    # anime_loader.start_animation("dots")
    # time.sleep(2)
    # anime_loader.stop_animation()
    # anime_loader.start_animation("typewriter")
    # time.sleep(2)
    # anime_loader.stop_animation()

    print("检定动画测试")
    print("测试1：实际值0.48/0.51，目标值0.5")
    probability_check_animation(0.51, 0.5, duration=1, color_preset=1)
    probability_check_animation(0.48, 0.7, duration=1, color_preset=2)

    print("\n测试2：实际值0.6，目标值0.5")
    probability_check_animation(0.9, 0.5, duration=1)

    print("\n测试3：实际值0.3，目标值0.5")
    probability_check_animation(0.2, 0.5, duration=1)

    print("\n测试4：实际值0，目标值0.01")
    probability_check_animation(0, 0.01, duration=2)
