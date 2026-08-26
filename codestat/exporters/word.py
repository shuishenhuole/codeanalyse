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
    """
    将源代码导出为 Word 文档
    
    收集目录中所有代码文件的内容，生成包含统计概览和完整代码的 Word 文档。
    
    参数:
        directory: 项目根目录
        output_path: 输出文件路径 (如 "code.docx")
        extra_excludes: 额外的排除项 (可选)
    
    文档格式:
        - 标题: 居中对齐
        - 代码: Courier New 等宽字体，9pt
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
    # 使用等宽字体便于代码阅读
    style = doc.styles["Normal"]
    style.font.name = "Courier New"
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
    lang_stats: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
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

    # 计算行数限制
    current_line_count = 0
    max_lines = MAX_WORD_PAGES * LINES_PER_PAGE

    # 遍历每个代码文件
    for rel_path, content, lang in code_files:
        # 计算文件行数
        file_lines = content.count("\n") + 1
        
        # 检查是否超过行数限制
        if current_line_count + file_lines > max_lines:
            # 计算剩余可用行数
            remaining_lines = max_lines - current_line_count
            if remaining_lines <= 0:
                break
            
            # 截断内容
            lines = content.split("\n")
            content = "\n".join(lines[:remaining_lines])
            content += f"\n\n... [文件内容被截断，已达到{MAX_WORD_PAGES}页限制]"
            file_lines = remaining_lines

        # 添加文件标题 (二级标题)
        file_heading = doc.add_heading(f"{rel_path}", level=2)

        # 添加语言标签 (灰色小字)
        lang_para = doc.add_paragraph()
        run = lang_para.add_run(f"语言: {lang.name}")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(100, 100, 100)

        # 添加代码内容 (等宽字体)
        code_para = doc.add_paragraph()
        code_para.paragraph_format.space_before = Pt(6)
        code_para.paragraph_format.space_after = Pt(12)
        run = code_para.add_run(content)
        run.font.name = "Courier New"
        run.font.size = Pt(9)

        # 累加行数
        current_line_count += file_lines

        # 检查是否达到限制
        if current_line_count >= max_lines:
            # 添加截断提示 (红色加粗)
            note_para = doc.add_paragraph()
            run = note_para.add_run(f"\n[已达到{MAX_WORD_PAGES}页限制，后续文件已省略]")
            run.font.color.rgb = RGBColor(255, 0, 0)
            run.font.bold = True
            break

    # ==================== 保存文档 ====================
    
    doc.save(output_path)
    
    # 输出提示信息
    print(f"已导出到 {output_path}")
    print(f"总行数: {total_lines}")
    if current_line_count < total_lines:
        print(f"提示: 内容已达 {MAX_WORD_PAGES} 页上限，文档中仅写入前 {current_line_count} 行")