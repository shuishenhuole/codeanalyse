"""
命令行入口模块

该模块提供命令行接口，处理用户输入并调用相应功能。

核心功能:
    - create_parser(): 创建命令行参数解析器
    - main(): 命令行主入口函数

命令行参数:
    位置参数:
        directory: 要统计的目录路径 (默认: 当前目录)
    
    可选参数:
        --exclude, -e: 排除的目录或文件名 (支持多个)
        --format, -f: 输出格式 (table/json/csv/word)
        --output, -o: 输出文件路径
        --version, -v: 显示版本信息

使用方式:
    # 作为模块运行
    python -m codestat
    
    # 作为函数调用
    from code.cli import main
    main(["./src", "--format", "json", "-o", "stats.json"])
"""

import argparse
import os
from typing import Optional, Set

from ..core import scan_directory
from ..exporters import export_table, export_json, export_csv, export_word


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    配置 argparse 解析器，定义所有支持的命令行参数。
    
    返回:
        argparse.ArgumentParser 对象
    
    参数说明:
        directory: 位置参数，可选
            要统计的目录路径，默认当前目录
        
        --exclude / -e: 可选参数，支持多个值
            排除的目录或文件名，空格分隔
        
        --format / -f: 可选参数
            输出格式: table (默认), json, csv, word
        
        --output / -o: 可选参数
            输出文件路径，默认:
            - json: codestat.json
            - csv: codestat.csv
            - word: codestat.docx
        
        --version / -v: 标志参数
            显示版本信息
    
    示例:
        >>> parser = create_parser()
        >>> args = parser.parse_args(["./src", "--format", "json"])
        >>> args.directory
        './src'
        >>> args.format
        'json'
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

    # 位置参数: 目录路径
    parser.add_argument(
        "directory",
        nargs="?",          # 可选参数
        default=".",
        help="要统计的目录路径 (默认: 当前目录)",
    )

    # 可选参数: 排除项
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",          # 支持多个值
        default=[],
        help="排除的目录或文件名",
    )

    # 可选参数: 输出格式
    parser.add_argument(
        "--format", "-f",
        choices=["table", "json", "csv", "word"],
        default="table",
        help="输出格式 (默认: table)",
    )

    # 可选参数: 输出文件路径
    parser.add_argument(
        "--output", "-o",
        help="输出文件路径",
    )

    # 可选参数: 版本信息
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


def main(args: Optional[list] = None) -> int:
    """
    命令行主入口函数
    
    解析命令行参数，执行统计，输出结果。
    
    参数:
        args: 命令行参数列表
            - None: 从 sys.argv 读取 (默认)
            - 列表: 用于测试或程序调用
    
    返回:
        退出码
            - 0: 成功
            - 1: 失败 (如目录不存在)
    
    执行流程:
        1. 解析命令行参数
        2. 验证目录路径
        3. 构建排除集合
        4. 执行目录扫描
        5. 根据格式输出结果
    
    示例:
        # 正常执行
        >>> exit_code = main(["./src"])
        >>> exit_code
        0
        
        # 目录不存在
        >>> exit_code = main(["/nonexistent"])
        >>> exit_code
        1
        
        # 导出 JSON
        >>> main(["./src", "--format", "json", "-o", "stats.json"])
        已导出到 stats.json
        0
    """
    # 创建解析器并解析参数
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # 转换为绝对路径
    directory = os.path.abspath(parsed_args.directory)

    # 验证目录是否存在
    if not os.path.isdir(directory):
        print(f"错误: '{directory}' 不是有效目录")
        return 1

    # 构建排除集合
    extra_excludes: Optional[Set[str]] = set(parsed_args.exclude) if parsed_args.exclude else None

    # 执行目录扫描
    results = scan_directory(directory, extra_excludes)

    # 根据格式输出结果
    if parsed_args.format == "table":
        # 终端表格输出
        print(f"\n统计目录: {directory}\n")
        export_table(results)
    elif parsed_args.format == "json":
        # JSON 导出
        output = parsed_args.output or "codestat.json"
        export_json(results, output)
    elif parsed_args.format == "csv":
        # CSV 导出
        output = parsed_args.output or "codestat.csv"
        export_csv(results, output)
    elif parsed_args.format == "word":
        # Word 导出
        output = parsed_args.output or "codestat.docx"
        export_word(directory, output, extra_excludes)

    return 0


# ==================== 模块入口 ====================
# 支持 python -m code.cli 或直接运行此文件

if __name__ == "__main__":
    exit(main())