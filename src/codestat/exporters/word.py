"""Word导出"""

import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..config import MAX_WORD_PAGES, LINES_PER_PAGE
from ..core.language import LanguageConfig
from ..core.scanner import collect_code_files


def export_word(
    directory: str,
    output_path: str,
    extra_excludes: Optional[Set[str]] = None,
) -> None:
    """导出为Word文档"""
    code_files = collect_code_files(directory, extra_excludes)

    if not code_files:
        print("未找到可导出的代码文件。")
        return

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Courier New"
    style.font.size = Pt(9)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.0

    title = doc.add_heading("代码文档", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    info_para = doc.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info_para.add_run(f"项目路径: {os.path.abspath(directory)}")
    run.font.size = Pt(12)

    doc.add_heading("统计概览", level=1)

    lang_stats: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
    for rel_path, content, lang in code_files:
        line_count = content.count("\n") + 1
        file_count, total_lines = lang_stats[lang.name]
        lang_stats[lang.name] = (file_count + 1, total_lines + line_count)

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    header_cells = table.rows[0].cells
    header_cells[0].text = "语言"
    header_cells[1].text = "文件数"
    header_cells[2].text = "总行数"

    for cell in header_cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True

    total_files = 0
    total_lines = 0
    for lang_name, (count, lines) in sorted(lang_stats.items(), key=lambda x: x[1][1], reverse=True):
        row_cells = table.add_row().cells
        row_cells[0].text = lang_name
        row_cells[1].text = str(count)
        row_cells[2].text = str(lines)
        for cell in row_cells[1:]:
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        total_files += count
        total_lines += lines

    row_cells = table.add_row().cells
    row_cells[0].text = "总计"
    row_cells[1].text = str(total_files)
    row_cells[2].text = str(total_lines)
    for cell in row_cells:
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True

    doc.add_page_break()

    doc.add_heading("代码内容", level=1)

    current_line_count = 0
    max_lines = MAX_WORD_PAGES * LINES_PER_PAGE

    for rel_path, content, lang in code_files:
        file_lines = content.count("\n") + 1
        if current_line_count + file_lines > max_lines:
            remaining_lines = max_lines - current_line_count
            if remaining_lines <= 0:
                break
            lines = content.split("\n")
            content = "\n".join(lines[:remaining_lines])
            content += f"\n\n... [文件内容被截断，已达到{MAX_WORD_PAGES}页限制]"
            file_lines = remaining_lines

        file_heading = doc.add_heading(f"{rel_path}", level=2)

        lang_para = doc.add_paragraph()
        run = lang_para.add_run(f"语言: {lang.name}")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(100, 100, 100)

        code_para = doc.add_paragraph()
        code_para.paragraph_format.space_before = Pt(6)
        code_para.paragraph_format.space_after = Pt(12)
        run = code_para.add_run(content)
        run.font.name = "Courier New"
        run.font.size = Pt(9)

        current_line_count += file_lines

        if current_line_count >= max_lines:
            note_para = doc.add_paragraph()
            run = note_para.add_run(f"\n[已达到{MAX_WORD_PAGES}页限制，后续文件已省略]")
            run.font.color.rgb = RGBColor(255, 0, 0)
            run.font.bold = True
            break

    doc.save(output_path)
    print(f"已导出到 {output_path}")
    print(f"总行数: {current_line_count}")