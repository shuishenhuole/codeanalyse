"""
CodeStat GUI 独立入口脚本

使用方式:
    python gui_run.py

功能:
    - 选择统计目录
    - 配置排除项
    - 表格展示统计结果
    - 导出 JSON / CSV / Word
"""

from codestat.gui import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
