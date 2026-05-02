"""
CodeStat 命令行入口

支持通过 python -m code 命令运行 CodeStat 工具。

使用方式:
    python -m code                        # 统计当前目录
    python -m code ./src                  # 统计指定目录
    python -m code . --format json        # JSON 输出
    python -m code . --format word        # Word 导出
"""

from codestat.cli import main

if __name__ == "__main__":
    exit(main())