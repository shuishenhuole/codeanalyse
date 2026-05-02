"""表格输出"""

from typing import Dict, Tuple

from ..core.stats import LineStats


def print_table(results: Dict[str, Tuple[int, LineStats]]) -> None:
    """终端表格输出"""
    if not results:
        print("未找到可统计的代码文件。")
        return

    sorted_items = sorted(results.items(), key=lambda x: x[1][1].code, reverse=True)

    name_width = max(len(name) for name, _ in sorted_items)
    name_width = max(name_width, len("Language"))
    col_width = 8

    header = (
        f"| {'Language':<{name_width}} "
        f"| {'Files':>{col_width}} "
        f"| {'Code':>{col_width}} "
        f"| {'Comment':>{col_width}} "
        f"| {'Blank':>{col_width}} "
        f"| {'Total':>{col_width}} |"
    )
    separator = f"+{'-' * (name_width + 2)}" + f"+{'-' * (col_width + 2)}" * 5 + "+"

    print(separator)
    print(header)
    print(separator)

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