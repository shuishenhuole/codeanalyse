"""
CodeStat 应用入口

界面与业务逻辑分别位于 codestat.app 和 codestat.ui 包中，
本文件只保留 Flet 启动入口，便于测试与打包。
"""

import flet as ft

from codestat.app import main

if __name__ == "__main__":
    ft.run(main)
