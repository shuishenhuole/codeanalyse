"""JSON导出"""

import json
from typing import Dict, Tuple

from ..core.stats import LineStats


def export_json(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """导出为JSON"""
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

    data.append({
        "language": "Total",
        "files": total_files,
        "code": total_stats.code,
        "comment": total_stats.comment,
        "blank": total_stats.blank,
        "total": total_stats.total,
    })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"已导出到 {output_path}")