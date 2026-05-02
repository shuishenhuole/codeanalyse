"""
行统计模块

该模块提供代码行数统计功能，区分代码行、注释行和空行。

核心功能:
    - LineStats: 行统计数据类
    - count_lines(): 统计单个文件的行数

统计规则:
    1. 空行: 仅包含空白字符的行
    2. 注释行: 
       - 行注释: 以注释符开头的行 (如 #, //)
       - 块注释: 处于块注释内的行 (如 /* ... */)
    3. 代码行: 不属于以上两种情况的行

使用方式:
    from code.core.stats import LineStats, count_lines
    from code.core.language import detect_language
    
    lang = detect_language("main.py")
    stats = count_lines("main.py", lang)
    print(f"代码: {stats.code}, 注释: {stats.comment}, 空行: {stats.blank}")
"""

from dataclasses import dataclass

from .language import LanguageConfig


@dataclass
class LineStats:
    """
    行统计数据类
    
    存储单个文件或多个文件的行数统计结果。
    
    属性:
        total: 总行数 (代码 + 注释 + 空行)
        code: 代码行数
        comment: 注释行数
        blank: 空行数
    
    运算:
        支持 += 运算符，用于累加多个文件的统计结果
    
    示例:
        >>> stats = LineStats(code=100, comment=20, blank=30)
        >>> stats.total
        150
        
        >>> stats1 = LineStats(code=50)
        >>> stats2 = LineStats(code=30)
        >>> stats1 += stats2
        >>> stats1.code
        80
    """
    total: int = 0
    code: int = 0
    comment: int = 0
    blank: int = 0

    def __iadd__(self, other: "LineStats") -> "LineStats":
        """
        累加运算符实现
        
        用于合并多个文件的统计结果。
        
        参数:
            other: 另一个 LineStats 对象
        
        返回:
            累加后的 LineStats 对象
        
        示例:
            >>> total_stats = LineStats()
            >>> for file_stats in all_stats:
            ...     total_stats += file_stats
        """
        self.total += other.total
        self.code += other.code
        self.comment += other.comment
        self.blank += other.blank
        return self


def count_lines(filepath: str, lang: LanguageConfig) -> LineStats:
    """
    统计单个文件的行数
    
    逐行读取文件内容，根据语言配置判断每行类型。
    
    处理流程:
        1. 读取文件内容 (UTF-8 编码，忽略解码错误)
        2. 对每一行进行分类:
           - 空行检测: strip() 后为空
           - 块注释检测: 检查块注释标记
           - 行注释检测: 检查行注释前缀
           - 代码行: 不满足以上条件的行
        3. 统计各类行数
    
    参数:
        filepath: 文件路径
        lang: 语言配置 (用于确定注释格式)
    
    返回:
        LineStats 对象，包含各类行数统计
    
    注意:
        - 使用 errors="ignore" 忽略解码错误 (适用于二进制文件)
        - 文件无法读取时返回空统计结果
    
    示例:
        >>> from code.core.language import detect_language
        >>> lang = detect_language("main.py")
        >>> stats = count_lines("main.py", lang)
        >>> print(f"代码行: {stats.code}")
    """
    # 初始化统计结果
    stats = LineStats()
    
    # 块注释状态标记
    in_block_comment = False
    
    # 检查是否支持块注释
    has_block_comment = bool(lang.block_comment_start and lang.block_comment_end)

    try:
        # 打开文件，忽略解码错误
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stats.total += 1
                stripped = line.strip()

                # -------------------- 空行检测 --------------------
                if not stripped:
                    stats.blank += 1
                    continue

                # -------------------- 块注释检测 --------------------
                if has_block_comment:
                    # 当前在块注释内
                    if in_block_comment:
                        stats.comment += 1
                        # 检查是否遇到块注释结束标记
                        if lang.block_comment_end in stripped:
                            in_block_comment = False
                        continue

                    # 检查是否遇到块注释开始标记
                    if lang.block_comment_start in stripped:
                        stats.comment += 1
                        # 判断是否在同一行内闭合
                        # 例如: /* 单行注释 */
                        if lang.block_comment_end not in stripped[len(lang.block_comment_start):]:
                            in_block_comment = True
                        continue

                # -------------------- 行注释检测 --------------------
                is_comment = False
                for prefix in lang.line_comments:
                    if stripped.startswith(prefix):
                        is_comment = True
                        break

                # -------------------- 行类型判定 --------------------
                if is_comment:
                    stats.comment += 1
                else:
                    stats.code += 1
                    
    except (OSError, UnicodeDecodeError):
        # 文件无法读取或解码时静默跳过
        pass

    return stats