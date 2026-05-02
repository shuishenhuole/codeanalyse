"""
JSON 导出模块

该模块提供 JSON 格式的统计结果导出功能。

核心功能:
    - export_json(): 将统计结果导出为 JSON 文件

输出格式:
    [
      {
        "language": "Python",
        "files": 12,
        "code": 856,
        "comment": 120,
        "blank": 89,
        "total": 1065
      },
      {
        "language": "Total",
        "files": 50,
        "code": 3000,
        "comment": 500,
        "blank": 300,
        "total": 3800
      }
    ]

使用方式:
    from code.exporters.json import export_json
    
    results = scan_directory("./src")
    export_json(results, "stats.json")
"""

import json
from typing import Dict, Tuple

from ..core.stats import LineStats


def export_json(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """
    将统计结果导出为 JSON 文件
    
    生成包含以下信息的 JSON 数组:
        - 每种语言的详细统计 (按代码行数降序)
        - 最后一项为总计汇总
    
    参数:
        results: scan_directory 返回的统计结果字典
        output_path: 输出文件路径
    
    JSON 字段说明:
        - language: 语言名称
        - files: 文件数量
        - code: 代码行数
        - comment: 注释行数
        - blank: 空行数
        - total: 总行数
    
    注意:
        - ensure_ascii=False 保证中文正常显示
        - indent=2 生成格式化的 JSON
    
    示例:
        >>> results = {"Python": (10, LineStats(code=500))}
        >>> export_json(results, "stats.json")
        已导出到 stats.json
    """
    # 初始化数据列表和总计统计
    data = []
    total_files = 0
    total_stats = LineStats()

    # 按代码行数降序遍历结果
    for name, (count, stats) in sorted(results.items(), key=lambda x: x[1][1].code, reverse=True):
        # 添加语言统计项
        data.append({
            "language": name,
            "files": count,
            "code": stats.code,
            "comment": stats.comment,
            "blank": stats.blank,
            "total": stats.total,
        })
        # 累加总计
        total_files += count
        total_stats += stats

    # 添加总计汇总项
    data.append({
        "language": "Total",
        "files": total_files,
        "code": total_stats.code,
        "comment": total_stats.comment,
        "blank": total_stats.blank,
        "total": total_stats.total,
    })

    # 写入 JSON 文件
    # ensure_ascii=False 保证中文正常显示
    # indent=2 生成格式化的 JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # 输出提示信息
    print(f"已导出到 {output_path}")