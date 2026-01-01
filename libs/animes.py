"""
提供同步加载动画类，用于在AI生成或加载时显示等待动画
"""
from typing import Optional, Callable
import threading
import time
from datetime import datetime
import sys


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
                f"\r{color}Wait{reset_color} {message}{dots}{time_str}")
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
                f"\r{color}Wait{reset_color} {message}: {base_text}{current_suffix}{time_str}")
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
                print()  # 换行
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

    # 添加颜色
    colored_text = f"{color}{text}{reset_color}" if color else text

    # 使用打字机效果
    interrupted = typewriter_effect(
        colored_text,
        delay=delay,  # 稍快的速度
        newline_delay=0.05,
    )

    if suffix and not interrupted:
        print(suffix)

    return interrupted


def number_growth_animation(target_value: float,
                            duration: float = 1.5,
                            message: str = "检定中",
                            color: str = "\033[93m",  # 黄色
                            reset_color: str = "\033[0m") -> None:
    """
    数字增长动画，显示数字从0增长到目标值

    Args:
        target_value: 目标数值
        duration: 动画持续时间（秒）
        message: 显示的消息
        color: 颜色代码
        reset_color: 颜色重置代码
    """
    current_value = 0.0
    start_time = time.time()
    end_time = start_time + duration

    while time.time() < end_time:
        elapsed = time.time() - start_time
        progress = min(elapsed / duration, 1.0)

        # 非线性增长曲线（缓入缓出效果）
        if progress < 0.8:
            # 前80%快速增长
            current_value = target_value * (progress / 0.8) ** 0.7
        else:
            # 后20%缓慢接近目标值
            remaining_progress = (progress - 0.8) / 0.2
            base_value = target_value * 0.8
            increment = target_value * 0.2 * (remaining_progress ** 2)
            current_value = base_value + increment

        # 确保不超过目标值
        current_value = min(current_value, target_value)

        # 显示当前数值（保留2位小数）
        sys.stdout.write(
            f"\r{color}🎲{reset_color} {message}: {current_value:.2f}/{target_value:.2f}")
        sys.stdout.flush()

        time.sleep(0.05)  # 50ms刷新一次

    # 最终显示目标值
    sys.stdout.write(
        f"\r{color}🎲{reset_color} {message}: {target_value:.2f}/{target_value:.2f}")
    sys.stdout.flush()
    print()  # 换行


def probability_check_animation(success_prob: float,
                                target_prob: float,
                                duration: float = 2.0,
                                color_success: str = "\033[92m",  # 绿色
                                color_fail: str = "\033[91m",     # 红色
                                reset_color: str = "\033[0m") -> None:
    """
    概率检定动画，显示成功概率和实际结果的对比

    Args:
        success_prob: 实际成功概率
        target_prob: 目标成功概率
        duration: 动画持续时间（秒）
        color_success: 成功时的颜色
        color_fail: 失败时的颜色
        reset_color: 颜色重置代码
    """
    is_success = success_prob < target_prob
    result_color = color_success if is_success else color_fail
    result_text = "成功" if is_success else "失败"

    current_prob = 0.0
    start_time = time.time()
    end_time = start_time + duration

    while time.time() < end_time:
        elapsed = time.time() - start_time
        progress = min(elapsed / duration, 1.0)

        # 非线性增长
        if progress < 0.9:
            current_prob = success_prob * (progress / 0.9) ** 0.5
        else:
            current_prob = success_prob

        # 显示当前概率
        sys.stdout.write(f"\r🎯 检定中: {current_prob:.2f}/{target_prob:.2f}")
        sys.stdout.flush()

        time.sleep(0.06)  # 60ms刷新一次

    # 显示最终结果
    sys.stdout.write(
        f"\r{result_color}🎯 检定{result_text}: {success_prob:.2f}/{target_prob:.2f}{reset_color}")
    sys.stdout.flush()
    print()  # 换行


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
    print("\n" + separator)

    paras = narr.split("\n")
    interrupted = False  # 这里关闭中断功能

    for para in paras:
        if para.strip() and not interrupted:
            para_interrupted = typewriter_narrative(
                para.strip(),
                color=color,
                suffix="\n"
            )
            if para_interrupted:
                interrupted = True
                break

    if not interrupted:
        print(separator)

    return interrupted
