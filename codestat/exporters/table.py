"""
表格输出模块

该模块提供终端表格格式的统计结果输出。

核心功能:
    - print_table(): 将统计结果以表格形式输出到终端

表格格式:
    +----------+--------+--------+---------+-------+-------+
    | Language |  Files |   Code | Comment | Blank | Total |
    +----------+--------+--------+---------+-------+-------+
    | Python   |     12 |    856 |     120 |    89 |  1065 |
    | Total    |     12 |    856 |     120 |    89 |  1065 |
    +----------+--------+--------+---------+-------+-------+

使用方式:
    from code.exporters.table import print_table
    
    results = scan_directory("./src")
    print_table(results)
"""

from typing import Dict, Tuple

from ..core.stats import LineStats


def print_table(results: Dict[str, Tuple[int, LineStats]]) -> None:
    """
    以表格形式输出统计结果
    
    生成格式化的终端表格，包含:
        - 每种语言的统计行 (按代码行数降序排列)
        - 总计汇总行
    
    参数:
        results: scan_directory 返回的统计结果字典
                 格式: {语言名: (文件数, LineStats)}
    
    输出格式:
        - 语言名称列: 左对齐
        - 数值列: 右对齐
        - 列宽自动适应内容长度
    
    示例:
        >>> results = {"Python": (10, LineStats(code=500))}
        >>> print_table(results)
        +----------+--------+--------+
        | Language |  Files |   Code |
        +----------+--------+--------+
        | Python   |     10 |    500 |
        +----------+--------+--------+
    """
    # 检查是否有结果
    if not results:
        print("未找到可统计的代码文件。")
        return

    # 按代码行数降序排列 (代码量多的语言排在前面)
    sorted_items = sorted(results.items(), key=lambda x: x[1][1].code, reverse=True)

    # ==================== 计算列宽 ====================
    
    # 语言名称列宽度
    # 取最长语言名和表头 "Language" 中的较大值
    name_width = max(len(name) for name, _ in sorted_items)
    name_width = max(name_width, len("Language"))
    
    # 数值列固定宽度
    col_width = 8

    # ==================== 构建表格 ====================
    
    # 表头行
    header = (
        f"| {'Language':<{name_width}} "
        f"| {'Files':>{col_width}} "
        f"| {'Code':>{col_width}} "
        f"| {'Comment':>{col_width}} "
        f"| {'Blank':>{col_width}} "
        f"| {'Total':>{col_width}} |"
    )
    
    # 分隔线
    separator = f"+{'-' * (name_width + 2)}" + f"+{'-' * (col_width + 2)}" * 5 + "+"

    # ==================== 输出表格 ====================
    
    # 输出表头
    print(separator)
    print(header)
    print(separator)

    # 初始化总计统计
    total_files = 0
    total_stats = LineStats()

    # 输出每种语言的统计行
    for name, (count, stats) in sorted_items:
        print(
            f"| {name:<{name_width}} "
            f"| {count:>{col_width}} "
            f"| {stats.code:>{col_width}} "
            f"| {stats.comment:>{col_width}} "
            f"| {stats.blank:>{col_width}} "
            f"| {stats.total:>{col_width}} |"
        )
        # 累加总计
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