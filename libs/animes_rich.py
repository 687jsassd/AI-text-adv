import threading
import time
import keyboard
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.live import Live


console = Console()


class GameTitle:
    """游戏标题动画类"""

    def __init__(self):
        self.exit_flag = False
        self.color_gradient = [
            "#FF4444", "#FF6666", "#FF8888", "#FFAAAA", "#FFCCCC",
            "#EE88EE", "#CC66CC", "#AA44AA", "#882288",
            "#4488FF", "#66AAFF", "#88CCFF", "#AACCEE"
        ]
        self.color_indices = [0, 5, 9]

    def create_art(self):
        """创建当前颜色的艺术字"""
        c1, c2, c3 = (
            self.color_gradient[self.color_indices[0]],
            self.color_gradient[self.color_indices[1]],
            self.color_gradient[self.color_indices[2]]
        )

        return "\n".join([
            f"   ░███    ░██████   [{c1}] [/{c1}]         [{c2}]        ░██[/{c2}] [{c3}]          [/{c3}] ",
            f"  ░██░██     ░██     [{c1}] [/{c1}]         [{c2}]        ░██[/{c2}] [{c3}]          [/{c3}] ",
            f" ░██  ░██    ░██     [{c1}] ░██████  [/{c1}][{c2}]  ░████████[/{c2}] [{c3}]░██    ░██[/{c3}] ",
            f"░█████████   ░██     [{c1}]      ░██ [/{c1}][{c2}] ░██    ░██[/{c2}] [{c3}]░██    ░██[/{c3}] ",
            f"░██    ░██   ░██     [{c1}] ░███████ [/{c1}][{c2}] ░██    ░██[/{c2}] [{c3}] ░██  ░██ [/{c3}] ",
            f"░██    ░██   ░██     [{c1}]░██   ░██ [/{c1}][{c2}] ░██   ░███[/{c2}] [{c3}]  ░██░██  [/{c3}] ",
            f"░██    ░██ ░██████   [{c1}] ░█████░██[/{c1}][{c2}]  ░█████░██[/{c2}] [{c3}]   ░███   [/{c3}] ",
            " " * 55,
            " " * 55,
            " " * 20 + "按 [bold yellow]回车[/bold yellow] 开始游戏" + " " * 20,
        ])

    def check_keypress(self):
        """检查按键的线程函数"""
        keyboard.read_event()
        self.exit_flag = True

    def show(self):
        """显示标题动画，返回True表示用户按了回车"""
        self.exit_flag = False

        # 启动按键监听线程
        key_thread = threading.Thread(target=self.check_keypress, daemon=True)
        key_thread.start()
        console.clear()
        with Live(console=console, screen=True, auto_refresh=False) as live:
            while not self.exit_flag:
                # 创建面板
                title_art = self.create_art()
                panel = Panel.fit(
                    title_art,
                    border_style="bold cyan",
                    padding=(2, 3),
                    style="bold bright_white on black"
                )
                aligned_panel = Align.center(
                    panel,
                    vertical="middle",  # 垂直居中
                )
                # 更新显示
                live.update(aligned_panel, refresh=True)

                # 短暂延迟
                for _ in range(10):
                    if self.exit_flag:
                        break
                    time.sleep(0.05)

                for i in range(3):
                    self.color_indices[i] = (
                        self.color_indices[i] + 1) % len(self.color_gradient)
        console.clear()
        return True
