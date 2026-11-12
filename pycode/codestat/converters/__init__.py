"""
转换器模块

该模块整合了各类文件格式转换功能，目前包括:
    - md2docx: 将 Markdown 文档转换为 Word (.docx)

使用方式:
    from codestat.converters import convert_markdown_to_docx

    convert_markdown_to_docx("README.md", "README.docx")
"""

from .md2docx import convert_markdown_to_docx

__all__ = [
    "convert_markdown_to_docx",  # Markdown 转 Word
]
