"""行统计"""

from dataclasses import dataclass

from .language import LanguageConfig


@dataclass
class LineStats:
    """行统计结果"""
    total: int = 0
    code: int = 0
    comment: int = 0
    blank: int = 0

    def __iadd__(self, other: "LineStats") -> "LineStats":
        self.total += other.total
        self.code += other.code
        self.comment += other.comment
        self.blank += other.blank
        return self


def count_lines(filepath: str, lang: LanguageConfig) -> LineStats:
    """统计单个文件的行数"""
    stats = LineStats()
    in_block_comment = False
    has_block_comment = bool(lang.block_comment_start and lang.block_comment_end)

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stats.total += 1
                stripped = line.strip()

                if not stripped:
                    stats.blank += 1
                    continue

                if has_block_comment:
                    if in_block_comment:
                        stats.comment += 1
                        if lang.block_comment_end in stripped:
                            in_block_comment = False
                        continue

                    if lang.block_comment_start in stripped:
                        stats.comment += 1
                        if lang.block_comment_end not in stripped[len(lang.block_comment_start):]:
                            in_block_comment = True
                        continue

                is_comment = False
                for prefix in lang.line_comments:
                    if stripped.startswith(prefix):
                        is_comment = True
                        break

                if is_comment:
                    stats.comment += 1
                else:
                    stats.code += 1
    except (OSError, UnicodeDecodeError):
        pass

    return stats