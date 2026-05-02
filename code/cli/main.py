"""命令行入口"""

import argparse
import os
from typing import Optional, Set

from ..core import scan_directory
from ..exporters import export_table, export_json, export_csv, export_word


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器

    返回:
        argparse.ArgumentParser 对象
    """
    parser = argparse.ArgumentParser(
        description="代码量统计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               "  codestat                          # 统计当前目录\n"
               "  codestat src/                     # 统计 src 目录\n"
               "  codestat . --exclude test build   # 排除目录\n"
               "  codestat . --format json -o stats.json\n"
               "  codestat . --format csv  -o stats.csv\n"
               "  codestat . --format word -o code.docx\n",
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="要统计的目录路径 (默认: 当前目录)",
    )

    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=[],
        help="排除的目录或文件名",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["table", "json", "csv", "word"],
        default="table",
        help="输出格式 (默认: table)",
    )

    parser.add_argument(
        "--output", "-o",
        help="输出文件路径",
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    命令行主入口函数

    参数:
        args: 命令行参数列表 (用于测试，默认从 sys.argv 读取)

    返回:
        退出码 (0 表示成功，1 表示失败)
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # 转换为绝对路径
    directory = os.path.abspath(parsed_args.directory)

    # 验证目录
    if not os.path.isdir(directory):
        print(f"错误: '{directory}' 不是有效目录")
        return 1

    # 构建排除集合
    extra_excludes: Optional[Set[str]] = set(parsed_args.exclude) if parsed_args.exclude else None

    # 执行扫描
    results = scan_directory(directory, extra_excludes)

    # 根据格式输出
    if parsed_args.format == "table":
        print(f"\n统计目录: {directory}\n")
        export_table(results)
    elif parsed_args.format == "json":
        output = parsed_args.output or "code.json"
        export_json(results, output)
    elif parsed_args.format == "csv":
        output = parsed_args.output or "code.csv"
        export_csv(results, output)
    elif parsed_args.format == "word":
        output = parsed_args.output or "code.docx"
        export_word(directory, output, extra_excludes)

    return 0


if __name__ == "__main__":
    exit(main())