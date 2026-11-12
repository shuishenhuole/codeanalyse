"""
核心模块

该模块整合了 CodeStat 的核心功能，包括:
    - 语言检测 (language)
    - 行统计 (stats)
    - 文件扫描 (scanner)

使用方式:
    from code.core import scan_directory, detect_language, LineStats

    # 检测语言
    lang = detect_language("main.py")

    # 扫描目录
    results = scan_directory("./src")

    # 统计单个文件
    from code.core import count_lines
    stats = count_lines("main.py", lang)
"""

from .language import LANGUAGES, LanguageConfig, detect_language
from .scanner import collect_code_files, scan_directory
from .stats import LineStats, count_lines

__all__ = [
    "LanguageConfig",      # 语言配置数据类
    "detect_language",     # 语言检测函数
    "LANGUAGES",           # 支持的语言列表
    "LineStats",           # 行统计数据类
    "count_lines",         # 行统计函数
    "scan_directory",      # 目录扫描函数
    "collect_code_files",  # 收集代码文件函数
]
