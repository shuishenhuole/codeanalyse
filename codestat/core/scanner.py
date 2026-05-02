"""
文件扫描模块

该模块提供目录扫描功能，用于收集和统计代码文件。

核心功能:
    - load_ignore_file(): 加载排除规则文件
    - scan_directory(): 扫描目录并统计代码
    - collect_code_files(): 收集代码文件内容 (用于 Word 导出)

扫描流程:
    1. 合并排除规则: 默认排除 + .codestatignore + 命令行参数
    2. 递归遍历目录，跳过排除的目录和文件
    3. 检测文件语言类型
    4. 统计行数或收集文件内容

使用方式:
    from code.core.scanner import scan_directory
    
    # 统计目录
    results = scan_directory("./src")
    for lang_name, (count, stats) in results.items():
        print(f"{lang_name}: {count} 个文件, {stats.code} 行代码")
"""

import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..config import DEFAULT_EXCLUDE, IGNORE_FILE_NAME
from .language import LanguageConfig, detect_language
from .stats import LineStats, count_lines


def load_ignore_file(directory: str) -> Set[str]:
    """
    加载排除规则文件
    
    从项目根目录的 .codestatignore 文件读取排除规则。
    
    文件格式:
        - 每行一个排除项 (目录名或文件名)
        - # 开头为注释行
        - 空行自动跳过
    
    参数:
        directory: 项目根目录路径
    
    返回:
        排除项集合
    
    示例:
        # .codestatignore 文件内容:
        # 这是注释
        test
        fixtures
        
        >>> excludes = load_ignore_file("./project")
        >>> "test" in excludes
        True
    """
    # 构建排除规则文件路径
    ignore_file = os.path.join(directory, IGNORE_FILE_NAME)
    
    # 初始化排除集合
    excludes = set()
    
    # 检查文件是否存在
    if os.path.isfile(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith("#"):
                    excludes.add(line)
    
    return excludes


def scan_directory(
    directory: str,
    extra_excludes: Optional[Set[str]] = None,
) -> Dict[str, Tuple[int, LineStats]]:
    """
    扫描目录并统计代码
    
    递归遍历目录，统计所有代码文件的行数，按语言分类汇总。
    
    参数:
        directory: 要扫描的目录路径
        extra_excludes: 额外的排除项 (来自命令行 --exclude 参数)
    
    返回:
        字典，键为语言名，值为 (文件数, LineStats) 元组
        例如: {"Python": (10, LineStats(code=500, ...))}
    
    排除规则合并顺序:
        1. DEFAULT_EXCLUDE: 默认排除的目录
        2. .codestatignore: 用户自定义排除规则
        3. extra_excludes: 命令行参数指定的排除项
    
    示例:
        >>> results = scan_directory("./src")
        >>> for lang, (count, stats) in results.items():
        ...     print(f"{lang}: {count} 文件, {stats.code} 行代码")
        Python: 15 文件, 856 行代码
        JavaScript: 8 文件, 432 行代码
    """
    # 合并排除规则
    excludes = DEFAULT_EXCLUDE | load_ignore_file(directory)
    if extra_excludes:
        excludes |= extra_excludes

    # 初始化结果字典
    # 使用 defaultdict 自动创建初始统计对象
    results: Dict[str, Tuple[int, LineStats]] = defaultdict(lambda: (0, LineStats()))

    # 递归遍历目录
    for root, dirs, files in os.walk(directory):
        # 原地修改 dirs 列表，跳过排除的目录
        # os.walk 不会进入被排除的目录
        dirs[:] = [d for d in dirs if d not in excludes]

        # 遍历当前目录的文件
        for filename in files:
            # 跳过排除的文件
            if filename in excludes:
                continue

            # 构建完整文件路径
            filepath = os.path.join(root, filename)

            # 检测文件语言类型
            lang = detect_language(filepath)
            if lang is None:
                # 不支持的语言类型，跳过
                continue

            # 统计该文件的行数
            file_stats = count_lines(filepath, lang)

            # 累加到对应语言的统计结果
            count, stats = results[lang.name]
            stats += file_stats
            results[lang.name] = (count + 1, stats)

    return dict(results)


def collect_code_files(
    directory: str,
    extra_excludes: Optional[Set[str]] = None,
) -> List[Tuple[str, str, LanguageConfig]]:
    """
    收集代码文件内容
    
    递归遍历目录，读取所有代码文件的内容，用于 Word 导出。
    
    参数:
        directory: 要扫描的目录路径
        extra_excludes: 额外的排除项
    
    返回:
        列表，每个元素为 (相对路径, 文件内容, 语言配置) 元组
        按语言名称和文件路径排序
    
    与 scan_directory 的区别:
        - scan_directory: 只统计行数，不读取内容
        - collect_code_files: 读取完整文件内容
    
    使用场景:
        - Word 文档导出: 需要包含完整的代码内容
    
    示例:
        >>> files = collect_code_files("./src")
        >>> for path, content, lang in files:
        ...     print(f"{path}: {len(content)} 字符, {lang.name}")
        main.py: 1234 字符, Python
        utils.js: 567 字符, JavaScript
    """
    # 合并排除规则
    excludes = DEFAULT_EXCLUDE | load_ignore_file(directory)
    if extra_excludes:
        excludes |= extra_excludes

    # 初始化结果列表
    code_files: List[Tuple[str, str, LanguageConfig]] = []

    # 递归遍历目录
    for root, dirs, files in os.walk(directory):
        # 跳过排除的目录
        dirs[:] = [d for d in dirs if d not in excludes]

        # 遍历当前目录的文件
        for filename in files:
            # 跳过排除的文件
            if filename in excludes:
                continue

            # 构建完整文件路径
            filepath = os.path.join(root, filename)
            
            # 检测文件语言类型
            lang = detect_language(filepath)
            if lang is None:
                continue

            # 读取文件内容
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # 计算相对路径
                rel_path = os.path.relpath(filepath, directory)
                
                # 添加到结果列表
                code_files.append((rel_path, content, lang))
            except (OSError, UnicodeDecodeError):
                # 文件无法读取时跳过
                pass

    # 按语言名称和文件路径排序
    code_files.sort(key=lambda x: (x[2].name, x[0]))
    
    return code_files