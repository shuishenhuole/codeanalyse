"""
导出器模块

该模块整合了各种导出格式，包括:
    - table: 终端表格输出
    - json: JSON 文件导出
    - csv: CSV 文件导出
    - word: Word 文档导出

使用方式:
    from code.exporters import export_table, export_json
    
    results = scan_directory("./src")
    
    # 终端表格输出
    export_table(results)
    
    # JSON 导出
    export_json(results, "stats.json")
    
    # CSV 导出
    export_csv(results, "stats.csv")
    
    # Word 导出
    export_word("./src", "code.docx")
"""

from typing import Dict, Tuple

from ..core.stats import LineStats


def export_table(results: Dict[str, Tuple[int, LineStats]]) -> None:
    """
    终端表格输出
    
    将统计结果以格式化表格形式输出到终端。
    
    参数:
        results: scan_directory 返回的统计结果
    """
    from .table import print_table
    print_table(results)


def export_json(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    JSON 文件导出
    
    将统计结果导出为 JSON 格式文件。
    
    参数:
        results: scan_directory 返回的统计结果
        output_path: 输出文件路径
    """
    from .json import export_json as _export_json
    _export_json(results, output_path)


def export_csv(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    CSV 文件导出
    
    将统计结果导出为 CSV 格式文件。
    
    参数:
        results: scan_directory 返回的统计结果
        output_path: 输出文件路径
    """
    from .csv import export_csv as _export_csv
    _export_csv(results, output_path)


def export_word(
    directory: str,
    output_path: str,
    extra_excludes: set = None,
) -> None:
    """
    Word 文档导出
    
    将源代码导出为 Word 文档，包含统计概览和完整代码。
    
    参数:
        directory: 项目根目录
        output_path: 输出文件路径
        extra_excludes: 额外的排除项 (可选)
    """
    from .word import export_word as _export_word
    _export_word(directory, output_path, extra_excludes)


__all__ = [
    "export_table",   # 终端表格输出
    "export_json",    # JSON 导出
    "export_csv",     # CSV 导出
    "export_word",    # Word 导出
]