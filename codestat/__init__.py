"""
CodeStat - 代码量统计工具

一个轻量级的 Python 命令行工具，用于统计项目中各编程语言的代码行数。

功能:
    - 支持 40+ 种编程语言和文件格式
    - 区分代码行、注释行、空行
    - 支持终端表格、JSON、CSV、Word 四种输出格式
    - 自动排除 .git、node_modules 等常见目录
    - 支持 .codestatignore 文件自定义排除规则

使用方式:
    python -m codestat                    # 统计当前目录
    python -m codestat src/               # 统计指定目录
    python -m codestat . -f json -o stats.json
"""

__version__ = "1.0.0"
__author__ = "CodeStat Team"