"""
Markdown 转 Word 模块

该模块将 Markdown 文档转换为 Word (.docx) 文件。

支持的元素:
    - 标题 (H1 ~ H6)
    - 普通段落与软换行合并
    - 粗体、斜体、粗斜体、行内代码、超链接
    - 有序列表、无序列表 (支持嵌套缩进)
    - 代码块 (等宽字体 + 浅灰底纹)
    - 引用块 (左侧竖线)
    - 表格 (Table Grid 样式)
    - 水平分割线
    - 本地图片 (相对 Markdown 文件所在目录)
    - 网络图片 (以占位文字提示)

使用方式:
    from codestat.converters import convert_markdown_to_docx

    convert_markdown_to_docx("README.md", "README.docx")
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from ..exceptions import ExportError

# ==================== 字体与配色 ====================

BODY_FONT = "Calibri"
EAST_ASIA_FONT = "微软雅黑"
CODE_FONT = "Consolas"

HEADING_COLOR = RGBColor(0x1F, 0x3A, 0x5F)
CODE_COLOR = RGBColor(0x33, 0x33, 0x33)
INLINE_CODE_COLOR = RGBColor(0xC7, 0x25, 0x4E)
LINK_COLOR = "0563C1"
QUOTE_COLOR = RGBColor(0x66, 0x66, 0x66)
QUOTE_BORDER_COLOR = "999999"

CODE_BACKGROUND = "F2F2F2"
HEADER_BACKGROUND = "F2F5FA"

# ==================== 正则表达式 ====================

# 行内格式：粗斜体 / 粗体 / 斜体 / 行内代码 / 链接
INLINE_TOKEN = re.compile(
    r"(?P<bold_italic>\*\*\*(?P<bold_italic_text>.+?)\*\*\*)"
    r"|(?P<bold>\*\*(?P<bold_text>.+?)\*\*)"
    r"|(?P<italic>\*(?P<italic_text>.+?)\*)"
    r"|(?P<code>`(?P<code_text>[^`]+)`)"
    r"|(?P<link>\[(?P<link_text>[^\]]+)\]\((?P<link_url>[^)]+)\))",
    re.DOTALL,
)

# 列表：允许 -, *, + 以及 1. / 1)
LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[-*+]|\d+[.)])\s+(?P<content>.*)$")

# 标题：# ~ ######
HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<text>.*?)\s*#*\s*$")

# 图片：![alt](src "title")
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)(?:\s+\"[^\"]*\")?\)$")

# 水平分割线
RULE_RE = re.compile(r"^(?:\*{3,}|-{3,}|_{3,})$")

# 表格分隔行：|---|:---:|---|
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


# ==================== 对外接口 ====================


def convert_markdown_to_docx(
    source: str | Path,
    target: str | Path,
) -> Path:
    """
    将 Markdown 文件转换为 Word 文档

    参数:
        source: Markdown 文件路径
        target: 输出 .docx 文件路径 (缺少后缀时自动补全)

    返回:
        实际写入的 Word 文件路径

    异常:
        ExportError: 文件不存在、读取失败或保存失败时抛出

    示例:
        >>> convert_markdown_to_docx("docs/guide.md", "docs/guide.docx")
        PosixPath('docs/guide.docx')
    """
    md_path = Path(source)
    if not md_path.is_file():
        raise ExportError(f"找不到 Markdown 文件: {md_path}")

    text = _read_markdown(md_path)

    out_path = Path(target)
    if out_path.suffix.lower() != ".docx":
        out_path = out_path.with_suffix(".docx")

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc = Document()
        _setup_styles(doc)
        _MarkdownRenderer(doc, md_path.parent, text).render()
        doc.save(str(out_path))
    except OSError as exc:
        raise ExportError(f"保存 Word 文件失败: {exc}") from exc

    return out_path


def _read_markdown(path: Path) -> str:
    """
    读取 Markdown 文本

    优先使用 UTF-8，兼容带 BOM 的文件；失败时回退到 GB18030，
    以便处理中文 Windows 下常见的旧编码文档。
    """
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        pass

    try:
        return path.read_text(encoding="gb18030")
    except UnicodeDecodeError as exc:
        raise ExportError("Markdown 文件编码无法识别，请使用 UTF-8 编码") from exc


# ==================== 样式与底层工具 ====================


def _setup_styles(doc: Document) -> None:
    """设置正文与标题的默认字体、字号和颜色"""
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(11)
    _set_east_asia_font(normal, EAST_ASIA_FONT)

    sizes = {1: 20, 2: 16, 3: 14, 4: 13, 5: 12, 6: 12}
    for level, size in sizes.items():
        heading = doc.styles[f"Heading {level}"]
        heading.font.name = BODY_FONT
        heading.font.size = Pt(size)
        heading.font.color.rgb = HEADING_COLOR
        _set_east_asia_font(heading, EAST_ASIA_FONT)


def _set_east_asia_font(element, font_name: str) -> None:
    """
    设置元素的中文字体

    python-docx 的 font.name 只设置西文字体，中文需要单独设置
    w:eastAsia 属性才能正确渲染。
    """
    rpr = element._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), font_name)


# pPr 中位于 w:shd 之后的元素 (按 OOXML 架构顺序)
_PPR_AFTER_SHD = (
    "w:tabs",
    "w:suppressAutoHyphens",
    "w:kinsoku",
    "w:wordWrap",
    "w:overflowPunct",
    "w:topLinePunct",
    "w:autoSpaceDE",
    "w:autoSpaceDN",
    "w:bidi",
    "w:adjustRightInd",
    "w:snapToGrid",
    "w:spacing",
    "w:ind",
    "w:contextualSpacing",
    "w:mirrorIndents",
    "w:suppressOverlap",
    "w:jc",
    "w:textDirection",
    "w:textAlignment",
    "w:textboxTightWrap",
    "w:outlineLvl",
    "w:divId",
    "w:cnfStyle",
    "w:rPr",
    "w:sectPr",
    "w:pPrChange",
)

# pPr 中位于 w:pBdr 之后的元素 (w:shd 及后续元素)
_PPR_AFTER_BDR = ("w:shd", *_PPR_AFTER_SHD)


def _add_paragraph_shading(paragraph, fill: str) -> None:
    """为段落添加纯色底纹，并按架构顺序插入"""
    ppr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)
    ppr.insert_element_before(shading, *_PPR_AFTER_SHD)


def _add_cell_shading(cell, fill: str) -> None:
    """为表格单元格添加纯色底纹"""
    tcpr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)
    tcpr.append(shading)


def _add_border(paragraph, side: str, color: str, size: str) -> None:
    """为段落添加单侧边框 (用于引用块和分割线)"""
    ppr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), size)
    border.set(qn("w:space"), "6" if side == "left" else "1")
    border.set(qn("w:color"), color)
    borders.append(border)
    ppr.insert_element_before(borders, *_PPR_AFTER_BDR)


def _add_hyperlink(paragraph, text: str, url: str) -> None:
    """在段落末尾追加真正的 Word 超链接"""
    relation_id = paragraph.part.relate_to(
        url,
        RELATIONSHIP_TYPE.HYPERLINK,
        is_external=True,
    )

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relation_id)

    run = OxmlElement("w:r")
    run_properties = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), LINK_COLOR)
    run_properties.append(color)

    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    run_properties.append(underline)

    run.append(run_properties)

    text_element = OxmlElement("w:t")
    text_element.set(qn("xml:space"), "preserve")
    text_element.text = text
    run.append(text_element)

    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _add_runs(paragraph, text: str) -> None:
    """把一行 Markdown 文本按行内格式拆成多个 run 写入段落"""
    position = 0
    for match in INLINE_TOKEN.finditer(text):
        if match.start() > position:
            paragraph.add_run(text[position : match.start()])

        if match.group("bold_italic_text") is not None:
            run = paragraph.add_run(match.group("bold_italic_text"))
            run.bold = True
            run.italic = True
        elif match.group("bold_text") is not None:
            run = paragraph.add_run(match.group("bold_text"))
            run.bold = True
        elif match.group("italic_text") is not None:
            run = paragraph.add_run(match.group("italic_text"))
            run.italic = True
        elif match.group("code_text") is not None:
            run = paragraph.add_run(match.group("code_text"))
            run.font.name = CODE_FONT
            _set_east_asia_font(run, EAST_ASIA_FONT)
            run.font.color.rgb = INLINE_CODE_COLOR
        elif match.group("link_text") is not None:
            _add_hyperlink(paragraph, match.group("link_text"), match.group("link_url"))

        position = match.end()

    if position < len(text):
        paragraph.add_run(text[position:])


# ==================== Markdown 渲染器 ====================


class _MarkdownRenderer:
    """按行解析 Markdown，并写入 python-docx 文档"""

    def __init__(self, doc: Document, base_dir: Path, text: str) -> None:
        self.doc = doc
        self.base_dir = base_dir
        self.lines = text.splitlines()

        self.in_code = False
        self.code_fence = "```"
        self.code_buf: list[str] = []

        self.table_buf: list[str] = []
        self.para_buf: list[str] = []

    def render(self) -> None:
        """逐行解析并写入文档"""
        for line in self.lines:
            self._consume(line)

        # 处理文末未闭合的代码块、表格和段落
        if self.in_code:
            self._add_code_block(self.code_buf)
            self.in_code = False
        self._flush_table()
        self._flush_paragraph()

    # -------------------- 行处理 --------------------

    def _consume(self, line: str) -> None:
        stripped = line.strip()

        # ----- 代码块内容 -----
        if self.in_code:
            if stripped.startswith(self.code_fence):
                self.in_code = False
                self._add_code_block(self.code_buf)
                self.code_buf = []
            else:
                self.code_buf.append(line)
            return

        # ----- 代码块开始 -----
        if stripped.startswith("```") or stripped.startswith("~~~"):
            self._flush_paragraph()
            self._flush_table()
            self.in_code = True
            self.code_fence = stripped[:3]
            self.code_buf = []
            return

        # ----- 表格 -----
        if stripped.startswith("|") and stripped.endswith("|"):
            self._flush_paragraph()
            self.table_buf.append(stripped)
            return
        self._flush_table()

        # ----- 标题 -----
        match = HEADING_RE.match(stripped)
        if match:
            self._flush_paragraph()
            level = len(match.group("marks"))
            heading = self.doc.add_heading("", level=level)
            _add_runs(heading, match.group("text").strip())
            return

        # ----- 水平分割线 -----
        if RULE_RE.match(stripped):
            self._flush_paragraph()
            self._add_horizontal_rule()
            return

        # ----- 引用块 -----
        if stripped.startswith(">"):
            self._flush_paragraph()
            self._add_quote(stripped.lstrip(">").strip())
            return

        # ----- 列表 -----
        match = LIST_RE.match(line)
        if match:
            self._flush_paragraph()
            self._add_list_item(match)
            return

        # ----- 图片 -----
        match = IMAGE_RE.match(stripped)
        if match:
            self._flush_paragraph()
            self._add_image(match.group("src"))
            return

        # ----- 空行 -----
        if not stripped:
            self._flush_paragraph()
            return

        # ----- 普通段落：合并连续行 -----
        self.para_buf.append(stripped)

    # -------------------- 块级元素 --------------------

    def _flush_paragraph(self) -> None:
        """把累积的普通段落写入文档"""
        if not self.para_buf:
            return
        paragraph = self.doc.add_paragraph()
        _add_runs(paragraph, " ".join(self.para_buf))
        self.para_buf = []

    def _flush_table(self) -> None:
        """把累积的表格行写入文档"""
        rows = self.table_buf
        self.table_buf = []
        if not rows:
            return

        body = [row for row in rows if not _is_table_separator(row)]
        if not body:
            return

        cells = [
            [cell.strip() for cell in row.strip().strip("|").split("|")]
            for row in body
        ]
        column_count = max(len(row) for row in cells)

        table = self.doc.add_table(rows=len(cells), cols=column_count)
        table.style = "Table Grid"

        for row_index, row in enumerate(cells):
            for column_index in range(column_count):
                cell = table.cell(row_index, column_index)
                cell.text = ""
                paragraph = cell.paragraphs[0]
                text = row[column_index] if column_index < len(row) else ""
                _add_runs(paragraph, text)

                if row_index == 0:
                    for run in paragraph.runs:
                        run.bold = True
                    _add_cell_shading(cell, HEADER_BACKGROUND)

        # 表格后补一个空段落，避免后续内容紧贴表格
        self.doc.add_paragraph()

    def _add_code_block(self, lines: list[str]) -> None:
        """写入代码块 (等宽字体 + 浅灰底纹)"""
        if not lines:
            return

        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Pt(12)
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(6)

        run = paragraph.add_run("\n".join(lines))
        run.font.name = CODE_FONT
        _set_east_asia_font(run, EAST_ASIA_FONT)
        run.font.size = Pt(9.5)
        run.font.color.rgb = CODE_COLOR

        _add_paragraph_shading(paragraph, CODE_BACKGROUND)

    def _add_horizontal_rule(self) -> None:
        """写入水平分割线 (使用段落下边框模拟)"""
        paragraph = self.doc.add_paragraph()
        _add_border(paragraph, "bottom", "AAAAAA", "6")

    def _add_quote(self, text: str) -> None:
        """写入引用块 (缩进 + 左侧灰色竖线)"""
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Pt(18)
        _add_runs(paragraph, text)

        for run in paragraph.runs:
            run.italic = True
            run.font.color.rgb = QUOTE_COLOR

        _add_border(paragraph, "left", QUOTE_BORDER_COLOR, "12")

    def _add_list_item(self, match: re.Match) -> None:
        """写入列表项，按缩进深度设置层级"""
        indent = match.group("indent").expandtabs(2)
        depth = len(indent) // 2
        marker = match.group("marker")
        content = match.group("content")

        style = "List Number" if marker[0].isdigit() else "List Bullet"
        try:
            paragraph = self.doc.add_paragraph(style=style)
        except KeyError:
            paragraph = self.doc.add_paragraph(style="List Bullet")

        if depth > 0:
            paragraph.paragraph_format.left_indent = Pt(18 * depth)

        _add_runs(paragraph, content)

    def _add_image(self, source: str) -> None:
        """写入图片；网络图片或缺失图片以占位文字提示"""
        if source.startswith(("http://", "https://")):
            self._add_placeholder(f"[网络图片: {source}]")
            return

        candidate = (self.base_dir / unquote(source)).expanduser()
        if not candidate.is_file():
            self._add_placeholder(f"[图片未找到: {source}]")
            return

        try:
            self.doc.add_picture(str(candidate))
        except Exception:
            # 图片格式不受 Word 支持时降级为占位文字
            self._add_placeholder(f"[图片无法插入: {source}]")

    def _add_placeholder(self, text: str) -> None:
        """写入灰色占位说明"""
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run(text)
        run.font.color.rgb = QUOTE_COLOR


def _is_table_separator(row: str) -> bool:
    """判断表格行是否为 |---|---| 形式的分隔行"""
    cells = row.strip().strip("|").split("|")
    return bool(cells) and all(
        TABLE_SEPARATOR_RE.match(cell.strip()) for cell in cells
    )
