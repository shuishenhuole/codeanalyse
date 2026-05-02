"""文件扫描"""

import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..config import DEFAULT_EXCLUDE, IGNORE_FILE_NAME
from .language import LanguageConfig, detect_language
from .stats import LineStats, count_lines


def load_ignore_file(directory: str) -> Set[str]:
    """加载排除规则文件"""
    ignore_file = os.path.join(directory, IGNORE_FILE_NAME)
    excludes = set()
    if os.path.isfile(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    excludes.add(line)
    return excludes


def scan_directory(
    directory: str,
    extra_excludes: Optional[Set[str]] = None,
) -> Dict[str, Tuple[int, LineStats]]:
    """扫描目录，统计代码"""
    excludes = DEFAULT_EXCLUDE | load_ignore_file(directory)
    if extra_excludes:
        excludes |= extra_excludes

    results: Dict[str, Tuple[int, LineStats]] = defaultdict(lambda: (0, LineStats()))

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in excludes]

        for filename in files:
            if filename in excludes:
                continue

            filepath = os.path.join(root, filename)

            lang = detect_language(filepath)
            if lang is None:
                continue

            file_stats = count_lines(filepath, lang)
            count, stats = results[lang.name]
            stats += file_stats
            results[lang.name] = (count + 1, stats)

    return dict(results)


def collect_code_files(
    directory: str,
    extra_excludes: Optional[Set[str]] = None,
) -> List[Tuple[str, str, LanguageConfig]]:
    """收集代码文件内容"""
    excludes = DEFAULT_EXCLUDE | load_ignore_file(directory)
    if extra_excludes:
        excludes |= extra_excludes

    code_files: List[Tuple[str, str, LanguageConfig]] = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in excludes]

        for filename in files:
            if filename in excludes:
                continue

            filepath = os.path.join(root, filename)
            lang = detect_language(filepath)
            if lang is None:
                continue

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                rel_path = os.path.relpath(filepath, directory)
                code_files.append((rel_path, content, lang))
            except (OSError, UnicodeDecodeError):
                pass

    code_files.sort(key=lambda x: (x[2].name, x[0]))
    return code_files