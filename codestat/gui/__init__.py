"""
GUI 模块

该模块提供基于 PySide6 (Qt) 的图形界面，方便可视化统计代码行数。

主要功能:
    - 选择要统计的目录
    - 配置排除项
    - 以表格形式展示统计结果
    - 导出为 JSON / CSV / Word 格式

使用方式:
    # 通过独立入口脚本启动
    python gui_run.py

    # 作为模块运行
    python -m codestat.gui
"""

from .main import run_app

__all__ = [
    "run_app",  # GUI 主入口
]
