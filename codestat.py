#!/usr/bin/env python3
"""代码量统计工具 - 统计项目中各语言的代码行数"""

import os
import argparse
import json
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ==================== 语言定义 ====================

@dataclass
class LanguageConfig:
    """
    语言配置类

    属性:
        name: 语言名称 (如 "Python", "JavaScript")
        extensions: 关联的文件扩展名列表 (如 [".py", ".pyw"])
        line_comments: 行注释前缀列表 (如 ["#"] 或 ["//"])
        block_comment_start: 块注释开始标记 (如 "/*" 或 "'''")
        block_comment_end: 块注释结束标记 (如 "*/" 或 "'''")
    """
    name: str
    extensions: List[str]
    line_comments: List[str] = field(default_factory=list)
    block_comment_start: str = ""
    block_comment_end: str = ""


# 支持的语言配置列表
# 每种语言定义了: 名称、扩展名、行注释符、块注释起止符
LANGUAGES = [
    # 主流编程语言
    LanguageConfig("Python", [".py", ".pyw"], ["#"], "'''", "'''"),
    LanguageConfig("JavaScript", [".js", ".jsx", ".mjs", ".cjs"], ["//"], "/*", "*/"),
    LanguageConfig("TypeScript", [".ts", ".tsx"], ["//"], "/*", "*/"),
    LanguageConfig("Java", [".java"], ["//"], "/*", "*/"),
    LanguageConfig("C", [".c", ".h"], ["//"], "/*", "*/"),
    LanguageConfig("C++", [".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"], ["//"], "/*", "*/"),
    LanguageConfig("C#", [".cs"], ["//"], "/*", "*/"),
    LanguageConfig("Go", [".go"], ["//"], "/*", "*/"),
    LanguageConfig("Rust", [".rs"], ["//"], "/*", "*/"),
    LanguageConfig("Swift", [".swift"], ["//"], "/*", "*/"),
    LanguageConfig("Kotlin", [".kt", ".kts"], ["//"], "/*", "*/"),
    LanguageConfig("Scala", [".scala"], ["//"], "/*", "*/"),

    # 脚本语言
    LanguageConfig("Ruby", [".rb", ".rake"], ["#"]),
    LanguageConfig("PHP", [".php", ".phtml"], ["//", "#"], "/*", "*/"),
    LanguageConfig("Perl", [".pl", ".pm", ".t"], ["#"]),
    LanguageConfig("Shell", [".sh", ".bash", ".zsh"], ["#"]),
    LanguageConfig("PowerShell", [".ps1", ".psm1"], ["#"], "<#", "#>"),
    LanguageConfig("Lua", [".lua"], ["--"], "--[[", "]]"),
    LanguageConfig("R", [".r", ".R"], ["#"]),
    LanguageConfig("Dart", [".dart"], ["//"], "/*", "*/"),

    # 函数式语言
    LanguageConfig("Elixir", [".ex", ".exs"], ["#"]),
    LanguageConfig("Erlang", [".erl", ".hrl"], ["%"]),
    LanguageConfig("Haskell", [".hs", ".lhs"], ["--"], "{-", "-}"),
    LanguageConfig("Clojure", [".clj", ".cljs"], [";;"]),
    LanguageConfig("Lisp", [".lisp", ".lsp"], [";", "#|", "|#"]),

    # 数据库/查询
    LanguageConfig("SQL", [".sql"], ["--"], "/*", "*/"),
    LanguageConfig("GraphQL", [".graphql", ".gql"], ["#"]),

    # 标记语言
    LanguageConfig("HTML", [".html", ".htm"], [], "<!--", "-->"),
    LanguageConfig("XML", [".xml", ".svg", ".xaml"], [], "<!--", "-->"),
    LanguageConfig("CSS", [".css", ".scss", ".sass", ".less"], ["//"], "/*", "*/"),
    LanguageConfig("Markdown", [".md", ".markdown"], [], "<!--", "-->"),

    # 前端框架
    LanguageConfig("Vue", [".vue"], ["//", "<!--", "-->"], "/*", "*/"),

    # 鸿蒙开发
    LanguageConfig("Harmony", [".ets", ".har"], ["//"], "/*", "*/"),

    # 配置/数据格式 (无注释或仅行注释)
    LanguageConfig("JSON", [".json"]),
    LanguageConfig("YAML", [".yaml", ".yml"], ["#"]),
    LanguageConfig("TOML", [".toml"], ["#"]),
    LanguageConfig("INI", [".ini", ".cfg", ".conf"], ["#", ";"]),

    # 构建/工具
    LanguageConfig("Assembly", [".asm", ".s"], [";", "#", "//"]),
    LanguageConfig("Dockerfile", ["Dockerfile", ".dockerfile"], ["#"]),
    LanguageConfig("Makefile", ["Makefile", "makefile", ".mk"], ["#"]),
    LanguageConfig("CMake", ["CMakeLists.txt", ".cmake"], ["#"]),
    LanguageConfig("Protobuf", [".proto"], ["//"], "/*", "*/"),
    LanguageConfig("YARA", [".yara"], ["//"], "/*", "*/"),
]

# 构建 扩展名 -> 语言配置 的快速查找映射表
# 例如: {".py": LanguageConfig("Python", ...), ".js": LanguageConfig("JavaScript", ...)}
EXTENSION_MAP: Dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        EXTENSION_MAP[ext.lower()] = lang

# 特殊文件名映射 (如 Dockerfile, Makefile 等无扩展名的文件)
SPECIAL_FILES: Dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        if not ext.startswith("."):
            SPECIAL_FILES[ext.lower()] = lang


# ==================== 行统计 ====================

@dataclass
class LineStats:
    """
    行统计结果数据类

    属性:
        total: 总行数
        code: 代码行数
        comment: 注释行数
        blank: 空行数
    """
    total: int = 0
    code: int = 0
    comment: int = 0
    blank: int = 0

    def __iadd__(self, other: "LineStats") -> "LineStats":
        """支持 += 运算符，用于累加多个文件的统计结果"""
        self.total += other.total
        self.code += other.code
        self.comment += other.comment
        self.blank += other.blank
        return self


def count_lines(filepath: str, lang: LanguageConfig) -> LineStats:
    """
    统计单个文件的行数

    实现逻辑:
    1. 逐行读取文件 (避免一次性加载大文件)
    2. 空行 -> blank
    3. 块注释内 -> comment (支持多行块注释 /* ... */)
    4. 行注释开头 -> comment (如 #, //, --)
    5. 其余 -> code

    参数:
        filepath: 文件路径
        lang: 语言配置，用于判断注释格式

    返回:
        LineStats 对象，包含各类行数统计
    """
    stats = LineStats()
    in_block_comment = False  # 标记当前是否处于块注释内部
    has_block_comment = bool(lang.block_comment_start and lang.block_comment_end)

    try:
        # errors="ignore" 跳过无法解码的字符 (如二进制文件)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stats.total += 1
                stripped = line.strip()

                # 空行判断
                if not stripped:
                    stats.blank += 1
                    continue

                # 块注释处理 (如 /* ... */ 或 ''' ... ''')
                if has_block_comment:
                    # 已在块注释内，检查是否遇到结束标记
                    if in_block_comment:
                        stats.comment += 1
                        if lang.block_comment_end in stripped:
                            in_block_comment = False
                        continue

                    # 检查是否遇到块注释开始标记
                    if lang.block_comment_start in stripped:
                        stats.comment += 1
                        # 判断是否在同一行内闭合 (如 /* comment */)
                        if lang.block_comment_end not in stripped[len(lang.block_comment_start):]:
                            in_block_comment = True
                        continue

                # 行注释判断 (如 #, //, --)
                is_comment = False
                for prefix in lang.line_comments:
                    if stripped.startswith(prefix):
                        is_comment = True
                        break

                if is_comment:
                    stats.comment += 1
                else:
                    stats.code += 1
    except (OSError, UnicodeDecodeError):
        # 文件无法读取或解码时静默跳过
        pass

    return stats


# ==================== 文件扫描 ====================

# 默认排除的目录集合
# 包含版本控制、依赖管理、IDE 配置、编译产物等常见无需统计的目录
DEFAULT_EXCLUDE = {
    # 版本控制
    ".git", ".svn", ".hg",
    # Node.js / JavaScript
    "node_modules",
    # Python
    "__pycache__", ".pytest_cache", "venv", "env", ".env", ".venv", ".tox", ".eggs",
    # IDE / 编辑器
    ".idea", ".vscode", ".vs",
    # 编译产物
    "dist", "build", "out", "target",
    # Java 构建工具
    ".gradle", ".maven",
    # 其他依赖
    "vendor", "Pods",
    # 测试覆盖率
    "coverage", ".nyc_output",
}


def load_ignore_file(directory: str) -> Set[str]:
    """
    加载 .codestatignore 文件中的排除规则

    文件格式: 每行一个目录名或文件名，# 开头为注释，空行忽略

    参数:
        directory: 项目根目录

    返回:
        排除项集合
    """
    ignore_file = os.path.join(directory, ".codestatignore")
    excludes = set()
    if os.path.isfile(ignore_file):
        with open(ignore_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith("#"):
                    excludes.add(line)
    return excludes


def detect_language(filepath: str) -> Optional[LanguageConfig]:
    """
    根据文件名或扩展名检测语言类型

    检测顺序:
    1. 先检查特殊文件名 (如 Dockerfile, Makefile)
    2. 再检查扩展名 (如 .py, .js)

    参数:
        filepath: 文件路径

    返回:
        语言配置对象，未识别则返回 None
    """
    basename = os.path.basename(filepath).lower()

    # 优先匹配特殊文件名
    if basename in SPECIAL_FILES:
        return SPECIAL_FILES[basename]

    # 通过扩展名匹配
    _, ext = os.path.splitext(basename)
    return EXTENSION_MAP.get(ext)


def scan_directory(
    directory: str,
    extra_excludes: Optional[Set[str]] = None,
) -> Dict[str, Tuple[int, LineStats]]:
    """
    递归扫描目录，统计所有代码文件

    参数:
        directory: 要扫描的目录路径
        extra_excludes: 额外的排除项 (来自命令行 --exclude 参数)

    返回:
        字典，键为语言名，值为 (文件数, LineStats) 元组
        例如: {"Python": (10, LineStats(code=500, ...)), "JavaScript": (5, ...)}
    """
    # 合并排除规则: 默认排除 + .codestatignore 文件 + 命令行参数
    excludes = DEFAULT_EXCLUDE | load_ignore_file(directory)
    if extra_excludes:
        excludes |= extra_excludes

    results: Dict[str, Tuple[int, LineStats]] = defaultdict(lambda: (0, LineStats()))

    for root, dirs, files in os.walk(directory):
        # 原地修改 dirs 列表，跳过排除的目录 (os.walk 不会进入这些目录)
        dirs[:] = [d for d in dirs if d not in excludes]

        for filename in files:
            # 跳过排除的文件
            if filename in excludes:
                continue

            filepath = os.path.join(root, filename)

            # 检测文件语言类型
            lang = detect_language(filepath)
            if lang is None:
                continue  # 不支持的语言类型，跳过

            # 统计该文件的行数
            file_stats = count_lines(filepath, lang)

            # 累加到对应语言的统计结果中
            count, stats = results[lang.name]
            stats += file_stats
            results[lang.name] = (count + 1, stats)

    return dict(results)


# ==================== 报告输出 ====================

def print_table(results: Dict[str, Tuple[int, LineStats]]) -> None:
    """
    以表格形式在终端输出统计结果

    输出示例:
    +------------+--------+--------+---------+-------+-------+
    | Language   |  Files |   Code | Comment | Blank | Total |
    +------------+--------+--------+---------+-------+-------+
    | Python     |     12 |    856 |     120 |    89 |  1065 |
    +------------+--------+--------+---------+-------+-------+
    | Total      |     12 |    856 |     120 |    89 |  1065 |
    +------------+--------+--------+---------+-------+-------+

    参数:
        results: scan_directory 返回的统计结果字典
    """
    if not results:
        print("未找到可统计的代码文件。")
        return

    # 按代码行数降序排列，代码量多的语言排在前面
    sorted_items = sorted(results.items(), key=lambda x: x[1][1].code, reverse=True)

    # 计算语言名称列的宽度 (取最长语言名和表头 "Language" 中的较大值)
    name_width = max(len(name) for name, _ in sorted_items)
    name_width = max(name_width, len("Language"))
    col_width = 8  # 数值列的固定宽度

    # 构建表头行
    header = (
        f"| {'Language':<{name_width}} "
        f"| {'Files':>{col_width}} "
        f"| {'Code':>{col_width}} "
        f"| {'Comment':>{col_width}} "
        f"| {'Blank':>{col_width}} "
        f"| {'Total':>{col_width}} |"
    )
    # 构建分隔线
    separator = f"+{'-' * (name_width + 2)}" + f"+{'-' * (col_width + 2)}" * 5 + "+"

    # 输出表头
    print(separator)
    print(header)
    print(separator)

    # 输出每种语言的统计行
    total_files = 0
    total_stats = LineStats()

    for name, (count, stats) in sorted_items:
        print(
            f"| {name:<{name_width}} "
            f"| {count:>{col_width}} "
            f"| {stats.code:>{col_width}} "
            f"| {stats.comment:>{col_width}} "
            f"| {stats.blank:>{col_width}} "
            f"| {stats.total:>{col_width}} |"
        )
        total_files += count
        total_stats += stats

    # 输出汇总行
    print(separator)
    print(
        f"| {'Total':<{name_width}} "
        f"| {total_files:>{col_width}} "
        f"| {total_stats.code:>{col_width}} "
        f"| {total_stats.comment:>{col_width}} "
        f"| {total_stats.blank:>{col_width}} "
        f"| {total_stats.total:>{col_width}} |"
    )
    print(separator)


def export_json(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    将统计结果导出为 JSON 文件

    输出格式:
    [
      {"language": "Python", "files": 12, "code": 856, "comment": 120, "blank": 89, "total": 1065},
      ...
      {"language": "Total", "files": 50, "code": 3000, "comment": 500, "blank": 300, "total": 3800}
    ]

    参数:
        results: scan_directory 返回的统计结果字典
        output_path: 输出文件路径
    """
    data = []
    total_files = 0
    total_stats = LineStats()

    for name, (count, stats) in sorted(results.items(), key=lambda x: x[1][1].code, reverse=True):
        data.append({
            "language": name,
            "files": count,
            "code": stats.code,
            "comment": stats.comment,
            "blank": stats.blank,
            "total": stats.total,
        })
        total_files += count
        total_stats += stats

    # 追加汇总行
    data.append({
        "language": "Total",
        "files": total_files,
        "code": total_stats.code,
        "comment": total_stats.comment,
        "blank": total_stats.blank,
        "total": total_stats.total,
    })

    # ensure_ascii=False 保证中文正常显示
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"已导出到 {output_path}")


def export_csv(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    将统计结果导出为 CSV 文件

    参数:
        results: scan_directory 返回的统计结果字典
        output_path: 输出文件路径
    """
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(["Language", "Files", "Code", "Comment", "Blank", "Total"])

        total_files = 0
        total_stats = LineStats()

        for name, (count, stats) in sorted(results.items(), key=lambda x: x[1][1].code, reverse=True):
            writer.writerow([name, count, stats.code, stats.comment, stats.blank, stats.total])
            total_files += count
            total_stats += stats

        # 写入汇总行
        writer.writerow(["Total", total_files, total_stats.code, total_stats.comment, total_stats.blank, total_stats.total])

    print(f"已导出到 {output_path}")


# ==================== CLI ====================

def main():
    """命令行入口函数"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        description="代码量统计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  python codestat.py                # 统计当前目录\n"
               "  python codestat.py src/           # 统计 src 目录\n"
               "  python codestat.py . --exclude test build\n"
               "  python codestat.py . --format json -o stats.json\n"
               "  python codestat.py . --format csv  -o stats.csv\n",
    )

    # 位置参数: 要统计的目录 (可选，默认当前目录)
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="要统计的目录路径 (默认: 当前目录)",
    )

    # 可选参数: 排除的目录/文件名
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=[],
        help="排除的目录或文件名",
    )

    # 可选参数: 输出格式
    parser.add_argument(
        "--format", "-f",
        choices=["table", "json", "csv"],
        default="table",
        help="输出格式 (默认: table)",
    )

    # 可选参数: 输出文件路径
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径 (仅 json/csv 格式需要)",
    )

    args = parser.parse_args()

    # 将目录路径转为绝对路径
    directory = os.path.abspath(args.directory)

    # 验证目录是否存在
    if not os.path.isdir(directory):
        print(f"错误: '{directory}' 不是有效目录")
        return 1

    # 构建排除集合并执行扫描
    extra_excludes = set(args.exclude) if args.exclude else None
    results = scan_directory(directory, extra_excludes)

    # 根据输出格式生成报告
    if args.format == "table":
        print(f"\n统计目录: {directory}\n")
        print_table(results)
    elif args.format == "json":
        output = args.output or "codestat.json"
        export_json(results, output)
    elif args.format == "csv":
        output = args.output or "codestat.csv"
        export_csv(results, output)

    return 0


if __name__ == "__main__":
    exit(main())
