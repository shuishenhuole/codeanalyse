"""Markdown 转 Word 功能测试"""

import base64

import pytest
from docx import Document

from codestat.converters import convert_markdown_to_docx
from codestat.converters import md2docx as md2docx_module
from codestat.exceptions import ExportError

# 1x1 透明 PNG，用于验证图片是否真正写入文档
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


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
    assert "[图片未找到: missing.png]" in paragraphs

    styles = [paragraph.style.name for paragraph in doc.paragraphs]
    assert "Heading 1" in styles
    assert "Heading 2" in styles
    assert "List Bullet" in styles
    assert "List Number" in styles

    # 代码块使用单元格卡片渲染，表格使用自定义样式
    assert len(doc.tables) == 2
    assert 'def hello():\n    print("hi")' in doc.tables[0].cell(0, 0).text
    markdown_table = next(
        table for table in doc.tables if table.cell(0, 0).text == "列一"
    )
    assert markdown_table.cell(1, 1).text == "B"

    # 页面与页眉页脚设置生效
    section = doc.sections[0]
    assert round(section.page_width.cm, 2) == 21.0
    assert round(section.left_margin.cm, 2) == 2.4
    assert doc.core_properties.title == "一级标题"
    assert section.header.paragraphs[0].text == "一级标题"
    assert "PAGE" in section.footer.paragraphs[0]._p.xml

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


def test_convert_markdown_to_docx_local_image(tmp_path):
    """本地图片会真正嵌入 Word，并生成居中的说明文字"""
    image_path = tmp_path / "cover.png"
    image_path.write_bytes(PNG_BYTES)
    markdown = tmp_path / "image.md"
    markdown.write_text("# 图片测试\n\n![本地图片](cover.png)\n", encoding="utf-8")

    warnings: list[str] = []
    output = tmp_path / "image.docx"
    convert_markdown_to_docx(markdown, output, warnings=warnings)

    doc = Document(str(output))
    assert len(doc.inline_shapes) == 1
    assert warnings == []
    assert "本地图片" in [paragraph.text for paragraph in doc.paragraphs]
    assert doc.paragraphs[0].text == "图片测试"


def test_convert_markdown_to_docx_html_and_data_uri_images(tmp_path):
    """HTML <img> 与 Data URI 图片都能写入文档"""
    image_path = tmp_path / "inline.png"
    image_path.write_bytes(PNG_BYTES)
    data_uri = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode("ascii")
    markdown = tmp_path / "image.md"
    markdown.write_text(
        "# 图片测试\n\n"
        '<img src="inline.png" alt="HTML 图片" />\n\n'
        f"![Data URI]({data_uri})\n",
        encoding="utf-8",
    )

    warnings: list[str] = []
    output = tmp_path / "image.docx"
    convert_markdown_to_docx(markdown, output, warnings=warnings)

    doc = Document(str(output))
    assert len(doc.inline_shapes) == 2
    assert warnings == []
    captions = [paragraph.text for paragraph in doc.paragraphs]
    assert "HTML 图片" in captions
    assert "Data URI" in captions


def test_convert_markdown_to_docx_remote_image(tmp_path, monkeypatch):
    """网络图片会先下载再嵌入文档"""
    requested: list[str] = []

    class FakeResponse:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def read(self, size: int = -1) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

    def fake_urlopen(request, timeout=None):
        requested.append(request.full_url)
        return FakeResponse(PNG_BYTES)

    monkeypatch.setattr(md2docx_module, "urlopen", fake_urlopen)

    markdown = tmp_path / "remote.md"
    markdown.write_text(
        "# 网络图片\n\n![远程图片](https://example.com/remote.png)\n",
        encoding="utf-8",
    )

    warnings: list[str] = []
    output = tmp_path / "remote.docx"
    convert_markdown_to_docx(markdown, output, warnings=warnings)

    doc = Document(str(output))
    assert len(doc.inline_shapes) == 1
    assert warnings == []
    assert requested == ["https://example.com/remote.png"]
