"""
Word 文档导出模块

该模块提供 Word 文档格式的代码导出功能。

核心功能:
    - export_word(): 将源代码导出为 Word 文档

文档结构:
    1. 标题页
       - 文档标题: "代码文档"
       - 项目路径信息
    
    2. 统计概览
       - 按语言汇总的表格 (语言、文件数、总行数)
       - 总计行
    
    3. 代码内容
       - 每个文件的完整代码
       - 文件路径作为二级标题
       - 语言标签
       - 使用等宽字体格式化代码
    
    4. 页数限制
       - 默认最多 60 页
       - 超出部分自动截断并提示

使用方式:
    from code.exporters.word import export_word
    
    export_word("./src", "code.docx")
    
    # 排除特定目录
    export_word("./src", "code.docx", extra_excludes={"test", "docs"})
"""

import os
from collections import defaultdict

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from ..config import LINES_PER_PAGE, MAX_WORD_PAGES
from ..core.language import LanguageConfig
from ..core.scanner import collect_code_files

# Word 文档使用的中文字体
# 同时设置东亚字体，确保中文正确渲染
WORD_FONT_NAME = "Noto Sans SC"


def export_word(
    directory: str,
    output_path: str,
    extra_excludes: set[str] | None = None,
) -> None:
    """
    将源代码导出为 Word 文档
    
    收集目录中所有代码文件的内容，生成包含统计概览和完整代码的 Word 文档。
    
    参数:
        directory: 项目根目录
        output_path: 输出文件路径 (如 "code.docx")
        extra_excludes: 额外的排除项 (可选)
    
    文档格式:
        - 标题: 居中对齐
        - 代码: Noto Sans SC 字体，9pt
        - 表格: Table Grid 样式
        - 语言标签: 灰色小字
    
    页数限制:
        - 根据 MAX_WORD_PAGES (默认 60) 和 LINES_PER_PAGE (默认 30) 计算
        - 超出部分自动截断
        - 末尾添加红色提示
    
    示例:
        >>> export_word("./src", "code.docx")
        已导出到 code.docx
        总行数: 1800
        
        >>> export_word("./project", "output.docx", extra_excludes={"test"})
        已导出到 output.docx
        总行数: 1500
    """
    # 收集所有代码文件
    code_files = collect_code_files(directory, extra_excludes)

    # 检查是否有文件
    if not code_files:
        print("未找到可导出的代码文件。")
        return

    # ==================== 创建 Word 文档 ====================

    doc = Document()

    # 设置默认样式
    # 使用指定字体便于代码阅读
    style = doc.styles["Normal"]
    style.font.name = WORD_FONT_NAME
    _set_east_asia_font(style, WORD_FONT_NAME)
    style.font.size = Pt(9)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0

    # ==================== 添加标题页 ====================

    # 主标题
    title = doc.add_heading("代码文档", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 项目路径信息
    info_para = doc.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info_para.add_run(f"项目路径: {os.path.abspath(directory)}")
    run.font.size = Pt(12)

    # ==================== 添加统计概览 ====================

    doc.add_heading("统计概览", level=1)

    # 按语言统计文件数和行数
    lang_stats: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
    for rel_path, content, lang in code_files:
        line_count = content.count("\n") + 1
        file_count, total_lines = lang_stats[lang.name]
        lang_stats[lang.name] = (file_count + 1, total_lines + line_count)

    # 创建概览表格
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"

    # 设置表头
    header_cells = table.rows[0].cells
    header_cells[0].text = "语言"
    header_cells[1].text = "文件数"
    header_cells[2].text = "总行数"

    # 格式化表头 (加粗居中)
    for cell in header_cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True

    # 添加语言统计行
    total_files = 0
    total_lines = 0
    for lang_name, (count, lines) in sorted(lang_stats.items(), key=lambda x: x[1][1], reverse=True):
        row_cells = table.add_row().cells
        row_cells[0].text = lang_name
        row_cells[1].text = str(count)
        row_cells[2].text = str(lines)

        # 数值列居中对齐
        for cell in row_cells[1:]:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 累加总计
        total_files += count
        total_lines += lines

    # 添加总计行
    row_cells = table.add_row().cells
    row_cells[0].text = "总计"
    row_cells[1].text = str(total_files)
    row_cells[2].text = str(total_lines)

    # 总计行加粗居中
    for cell in row_cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True

    # 分页
    doc.add_page_break()

    # ==================== 添加代码内容 ====================

    doc.add_heading("代码内容", level=1)

    # 计算单侧行数限制 (前/后各 MAX_WORD_PAGES 页)
    max_lines = MAX_WORD_PAGES * LINES_PER_PAGE

    # 拆分文件为: 头部保留 / 中间省略 / 尾部保留
    head_entries, middle_entries, tail_entries = _split_head_tail(code_files, max_lines)

    # 写入头部保留的文件
    current_line_count = 0
    for rel_path, content, lang, line_count in head_entries:
        _write_code_file(doc, rel_path, content, lang)
        current_line_count += line_count

    # 中间内容省略提示
    if middle_entries:
        omitted_files = len(middle_entries)
        omitted_lines = sum(entry[3] for entry in middle_entries)
        note_para = doc.add_paragraph()
        run = note_para.add_run(
            f"\n[中间省略 {omitted_files} 个文件共 {omitted_lines} 行代码，"
            f"仅保留前后各 {MAX_WORD_PAGES} 页]"
        )
        run.font.color.rgb = RGBColor(255, 0, 0)
        run.font.bold = True
        doc.add_page_break()

    # 写入尾部保留的文件
    for rel_path, content, lang, line_count in tail_entries:
        _write_code_file(doc, rel_path, content, lang)
        current_line_count += line_count

    # ==================== 保存文档 ====================

    doc.save(output_path)

    # 输出提示信息
    print(f"已导出到 {output_path}")
    print(f"总行数: {total_lines}")
    print(f"写入行数: {current_line_count}")
    if current_line_count < total_lines:
        print(
            f"提示: 代码超过 {MAX_WORD_PAGES * 2} 页，"
            f"文档仅保留前后各 {MAX_WORD_PAGES} 页"
        )


def _split_head_tail(
    code_files: list[tuple[str, str, LanguageConfig]],
    max_lines: int,
) -> tuple[list[tuple[str, str, LanguageConfig, int]], list[tuple[str, str, LanguageConfig, int]], list[tuple[str, str, LanguageConfig, int]]]:
    """
    将文件列表拆分为头部保留、中间省略、尾部保留三部分

    每个条目为 (相对路径, 内容, 语言配置, 行数)。

    规则:
        - 总行数不超过 max_lines * 2 时全部保留 (head 含全部, 其余为空)
        - 超出时 head 保留最前 max_lines 行, tail 保留最后 max_lines 行
        - 单文件跨越边界时按行数截断内容

    参数:
        code_files: (相对路径, 内容, 语言配置) 元组列表
        max_lines: 单侧最大行数

    返回:
        (head_entries, middle_entries, tail_entries) 三元组
    """
    # 计算每个文件的行数
    entries = [
        (rel_path, content, lang, content.count("\n") + 1)
        for rel_path, content, lang in code_files
    ]
    total_lines = sum(entry[3] for entry in entries)

    # 未超出限制: 全部保留
    if total_lines <= max_lines * 2:
        return entries, [], []

    # ==================== 头部保留 ====================
    head_entries: list[tuple[str, str, LanguageConfig, int]] = []
    head_remaining = max_lines
    for rel_path, content, lang, line_count in entries:
        if head_remaining <= 0:
            break
        if line_count <= head_remaining:
            head_entries.append((rel_path, content, lang, line_count))
            head_remaining -= line_count
        else:
            # 单个文件部分截断
            lines = content.split("\n")
            head_entries.append(
                (rel_path, "\n".join(lines[:head_remaining]), lang, head_remaining)
            )
            head_remaining = 0

    # ==================== 尾部保留 ====================
    tail_entries: list[tuple[str, str, LanguageConfig, int]] = []
    tail_remaining = max_lines
    for rel_path, content, lang, line_count in reversed(entries):
        if tail_remaining <= 0:
            break
        if line_count <= tail_remaining:
            tail_entries.append((rel_path, content, lang, line_count))
            tail_remaining -= line_count
        else:
            # 单个文件部分截断
            lines = content.split("\n")
            tail_entries.append(
                (rel_path, "\n".join(lines[-tail_remaining:]), lang, tail_remaining)
            )
            tail_remaining = 0
    tail_entries.reverse()

    # ==================== 中间省略 ====================
    head_count = len(head_entries)
    tail_count = len(tail_entries)
    middle_entries = entries[head_count : len(entries) - tail_count]

    return head_entries, middle_entries, tail_entries


def _set_east_asia_font(element, font_name: str) -> None:
    """
    设置 Word 元素的东亚字体

    python-docx 的 font.name 只设置西文字体，中文需要单独设置
    w:eastAsia 属性才能正确渲染。

    参数:
        element: 样式或 run 对象
        font_name: 字体名称
    """
    rpr = element._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), font_name)


def _write_code_file(doc: Document, rel_path: str, content: str, lang: LanguageConfig) -> None:
    """
    将单个代码文件写入 Word 文档

    包含文件标题、语言标签和等宽字体代码内容。

    参数:
        doc: Word 文档对象
        rel_path: 文件相对路径
        content: 文件内容
        lang: 语言配置
    """
    # 添加文件标题 (二级标题)
    doc.add_heading(f"{rel_path}", level=2)

    # 添加语言标签 (灰色小字)
    lang_para = doc.add_paragraph()
    run = lang_para.add_run(f"语言: {lang.name}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(100, 100, 100)

    # 添加代码内容 (指定字体)
    code_para = doc.add_paragraph()
    code_para.paragraph_format.space_before = Pt(6)
    code_para.paragraph_format.space_after = Pt(12)
    run = code_para.add_run(content)
    run.font.name = WORD_FONT_NAME
    _set_east_asia_font(run, WORD_FONT_NAME)
    run.font.size = Pt(9)
