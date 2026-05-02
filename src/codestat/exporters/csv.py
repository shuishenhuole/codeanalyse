"""CSV导出"""

import csv
from typing import Dict, Tuple

from ..core.stats import LineStats


def export_csv(results: Dict[str, Tuple[int, LineStats]], output_path: str) -> None:
    """导出为CSV"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Language", "Files", "Code", "Comment", "Blank", "Total"])

        total_files = 0
        total_stats = LineStats()

        for name, (count, stats) in sorted(results.items(), key=lambda x: x[1][1].code, reverse=True):
            writer.writerow([name, count, stats.code, stats.comment, stats.blank, stats.total])
            total_files += count
            total_stats += stats

        writer.writerow(["Total", total_files, total_stats.code, total_stats.comment, total_stats.blank, total_stats.total])

    print(f"已导出到 {output_path}")