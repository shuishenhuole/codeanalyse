"""导出器模块"""

from typing import Dict, Tuple

from ..core.stats import LineStats


def export_table(results: Dict[str, Tuple[int, LineStats]]) -> None:
    """终端表格输出"""
    from .table import print_table
    print_table(results)


def export_json(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """JSON导出"""
    from .json import export_json as _export_json
    _export_json(results, output_path)


def export_csv(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """CSV导出"""
    from .csv import export_csv as _export_csv
    _export_csv(results, output_path)


def export_word(
    directory: str,
    output_path: str,
    extra_excludes: set = None,
) -> None:
    """Word导出"""
    from .word import export_word as _export_word
    _export_word(directory, output_path, extra_excludes)


__all__ = [
    "export_table",
    "export_json",
    "export_csv",
    "export_word",
]