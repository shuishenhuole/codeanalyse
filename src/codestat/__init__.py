"""
CodeStat - 代码量统计工具

一个基于 Flet 的桌面应用，用于统计项目中各编程语言的代码行数。

功能:
    - 支持 40+ 种编程语言和文件格式
    - 区分代码行、注释行、空行
    - 支持 JSON、CSV、Word 三种导出格式
    - 自动排除 .git、node_modules 等常见目录
    - 支持 .codestatignore 文件自定义排除规则

使用方式:
    flet run          # 启动桌面应用
"""

__version__ = "1.0.0"
__author__ = "CodeStat Team"
