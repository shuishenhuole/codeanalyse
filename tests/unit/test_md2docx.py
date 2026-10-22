"""Markdown 转 Word 功能测试"""

import pytest
from docx import Document

from codestat.converters import convert_markdown_to_docx
from codestat.exceptions import ExportError


def test_convert_markdown_to_docx(tmp_path):
    """标题、列表、表格、代码块与链接都能写入 Word 文档"""
    markdown = tmp_path / "sample.md"
    markdown.write_text(
        """# 一级标题

段落包含 **粗体**、*斜体*、`行内代码` 和 [链接](https://example.com)。

## 列表

- 第一项
  - 嵌套项
1. 有序一

> 引用内容

```python
def hello():
    print("hi")
```

| 列一 | 列二 |
|---|---|
| A | B |

![缺失图片](missing.png)
""",
        encoding="utf-8",
    )
    output = tmp_path / "nested" / "sample.docx"

    result = convert_markdown_to_docx(markdown, output)

    assert result == output
    assert output.is_file()

    doc = Document(str(output))
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]

    assert "一级标题" in paragraphs
    assert "段落包含 粗体、斜体、行内代码 和 链接。" in paragraphs
    assert "第一项" in paragraphs
    assert "嵌套项" in paragraphs
    assert "引用内容" in paragraphs
    assert 'def hello():\n    print("hi")' in paragraphs
    assert "[图片未找到: missing.png]" in paragraphs

    styles = [paragraph.style.name for paragraph in doc.paragraphs]
    assert "Heading 1" in styles
    assert "Heading 2" in styles
    assert "List Bullet" in styles
    assert "List Number" in styles

    assert len(doc.tables) == 1
    assert doc.tables[0].cell(0, 0).text == "列一"
    assert doc.tables[0].cell(1, 1).text == "B"

    # 超链接以 w:hyperlink 元素保存，目标地址写在关系文件中
    document_xml = doc.element.xml
    assert "w:hyperlink" in document_xml
    external_targets = [
        relation.target_ref
        for relation in doc.part.rels.values()
        if "hyperlink" in relation.reltype
    ]
    assert "https://example.com" in external_targets


def test_convert_markdown_to_docx_missing_file(tmp_path):
    """源文件不存在时抛出 ExportError"""
    with pytest.raises(ExportError):
        convert_markdown_to_docx(tmp_path / "missing.md", tmp_path / "out.docx")
