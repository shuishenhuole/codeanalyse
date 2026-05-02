"""
CSV 导出模块

该模块提供 CSV 格式的统计结果导出功能。

核心功能:
    - export_csv(): 将统计结果导出为 CSV 文件

输出格式:
    Language,Files,Code,Comment,Blank,Total
    Python,12,856,120,89,1065
    JavaScript,8,432,56,45,533
    Total,20,1288,176,134,1598

使用方式:
    from code.exporters.csv import export_csv
    
    results = scan_directory("./src")
    export_csv(results, "stats.csv")
"""

import csv
from typing import Dict, Tuple

from ..core.stats import LineStats


def export_csv(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    将统计结果导出为 CSV 文件
    
    生成包含以下信息的 CSV 文件:
        - 表头行: Language, Files, Code, Comment, Blank, Total
        - 数据行: 每种语言的详细统计 (按代码行数降序)
        - 最后一行: 总计汇总
    
    参数:
        results: scan_directory 返回的统计结果字典
        output_path: 输出文件路径
    
    CSV 列说明:
        - Language: 语言名称
        - Files: 文件数量
        - Code: 代码行数
        - Comment: 注释行数
        - Blank: 空行数
        - Total: 总行数
    
    注意:
        - newline="" 防止 Windows 下出现空行
        - encoding="utf-8" 支持中文
    
    示例:
        >>> results = {"Python": (10, LineStats(code=500))}
        >>> export_csv(results, "stats.csv")
        已导出到 stats.csv
    """
    # 打开 CSV 文件
    # newline="" 防止 Windows 下出现额外空行
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # 创建 CSV writer
        writer = csv.writer(f)
        
        # 写入表头
        writer.writerow(["Language", "Files", "Code", "Comment", "Blank", "Total"])

        # 初始化总计统计
        total_files = 0
        total_stats = LineStats()

        # 按代码行数降序遍历结果
        for name, (count, stats) in sorted(results.items(), key=lambda x: x[1][1].code, reverse=True):
            # 写入语言统计行
            writer.writerow([name, count, stats.code, stats.comment, stats.blank, stats.total])
            # 累加总计
            total_files += count
            total_stats += stats

        # 写入总计汇总行
        writer.writerow([
            "Total",
            total_files,
            total_stats.code,
            total_stats.comment,
            total_stats.blank,
            total_stats.total,
        ])

    # 输出提示信息
    print(f"已导出到 {output_path}")