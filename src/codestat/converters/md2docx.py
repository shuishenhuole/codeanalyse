"""
Markdown 转 Word 模块

该模块将 Markdown 文档转换为 Word (.docx) 文件。

支持的元素:
    - 标题 (H1 ~ H6)
    - 普通段落与软换行合并
    - 粗体、斜体、粗斜体、行内代码、超链接
    - 有序列表、无序列表 (支持嵌套缩进)
    - 代码块 (浅色卡片 + 等宽字体)
    - 引用块 (浅色底纹 + 左侧竖线)
    - 表格 (自定义表头、斑马纹与细边框)
    - 页眉标题、页脚页码、标题强调线
    - 水平分割线
    - 本地图片、网络图片、Data URI 图片以及 HTML <img> 标签
    - 图片加载失败时以占位文字提示

使用方式:
    from codestat.converters import convert_markdown_to_docx

    convert_markdown_to_docx("README.md", "README.docx")
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from urllib.parse import unquote, unquote_to_bytes, urlparse
from urllib.request import Request, url2pathname, urlopen

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from ..exceptions import ExportError

# ==================== 字体与配色 ====================

BODY_FONT = "Calibri"
EAST_ASIA_FONT = "微软雅黑"
CODE_FONT = "Consolas"

BODY_COLOR = RGBColor(0x33, 0x33, 0x33)
HEADING_COLORS = {
    1: RGBColor(0x17, 0x36, 0x5D),
    2: RGBColor(0x1F, 0x4E, 0x79),
    3: RGBColor(0x2E, 0x5C, 0x8A),
    4: RGBColor(0x3B, 0x44, 0x52),
    5: RGBColor(0x3B, 0x44, 0x52),
    6: RGBColor(0x3B, 0x44, 0x52),
}
CODE_COLOR = RGBColor(0x24, 0x29, 0x2F)
INLINE_CODE_COLOR = RGBColor(0xC7, 0x25, 0x4E)
LINK_COLOR = "0563C1"
QUOTE_COLOR = RGBColor(0x4B, 0x55, 0x63)
MUTED_TEXT_COLOR = RGBColor(0x6B, 0x72, 0x80)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

CODE_BACKGROUND = "F6F8FA"
HEADER_BACKGROUND = "1F3A5F"
TABLE_STRIPE_BACKGROUND = "F7F9FC"
TABLE_BORDER_COLOR = "D9E2EC"
QUOTE_BACKGROUND = "F7F9FC"
QUOTE_BORDER_COLOR = "5685FF"
DIVIDER_COLOR = "D9E2EC"

# 网络图片下载限制
MAX_IMAGE_BYTES = 25 * 1024 * 1024
IMAGE_TIMEOUT_SECONDS = 20
IMAGE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

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

# 图片：![alt](src "title")，允许路径中包含空格
IMAGE_RE = re.compile(r"^!\[(?P<alt>[^\]]*)\]\((?P<src>.*)\)\s*$")

# HTML 图片：<img src="..." />
HTML_IMAGE_RE = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*(?P<quote>[\"'])(?P<src>.*?)(?P=quote)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)

HTML_ALT_RE = re.compile(
    r"\balt\s*=\s*(?P<quote>[\"'])(?P<alt>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)

# 水平分割线
RULE_RE = re.compile(r"^(?:\*{3,}|-{3,}|_{3,})$")

# 表格分隔行：|---|:---:|---|
TABLE_SEPARATOR_RE = re.compile(r"^:?-{3,}:?$")


# ==================== 对外接口 ====================


def convert_markdown_to_docx(
    source: str | Path,
    target: str | Path,
    *,
    warnings: list[str] | None = None,
) -> Path:
    """
    将 Markdown 文件转换为 Word 文档

    参数:
        source: Markdown 文件路径
        target: 输出 .docx 文件路径 (缺少后缀时自动补全)
        warnings: 可选的警告收集列表；图片下载或插入失败时会追加说明

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

    title = _extract_document_title(text, md_path.stem)

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc = Document()
        doc.core_properties.title = title
        doc.core_properties.subject = "Markdown 转换文档"
        doc.core_properties.comments = "由 CodeStat 从 Markdown 转换生成"
        _setup_styles(doc)
        _setup_page(doc, title)
        _MarkdownRenderer(doc, md_path.parent, text, warnings=warnings).render()
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


def _extract_document_title(text: str, fallback: str) -> str:
    """从第一个一级标题提取文档标题，没有则使用文件名"""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = HEADING_RE.match(stripped)
        if match and len(match.group("marks")) == 1:
            title = _plain_text(match.group("text"))
            if title:
                return title[:80]
    return fallback


def _plain_text(text: str) -> str:
    """去掉行内 Markdown 标记，得到纯文本"""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`#>]", "", text)
    return text.strip()


def _setup_styles(doc: Document) -> None:
    """设置正文、标题的字体、字号、间距与强调色"""
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(11)
    normal.font.color.rgb = BODY_COLOR
    _set_east_asia_font(normal, EAST_ASIA_FONT)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True

    # (字号, 段前, 段后, 与下段同页)
    heading_specs = {
        1: (24, 24, 12, True),
        2: (17, 18, 8, True),
        3: (14.5, 14, 6, True),
        4: (12.5, 12, 4, True),
        5: (11.5, 10, 4, False),
        6: (11.5, 10, 4, False),
    }
    for level, (size, before, after, keep_with_next) in heading_specs.items():
        heading = doc.styles[f"Heading {level}"]
        heading.font.name = BODY_FONT
        heading.font.size = Pt(size)
        heading.font.bold = True
        heading.font.italic = False
        heading.font.color.rgb = HEADING_COLORS[level]
        _set_east_asia_font(heading, EAST_ASIA_FONT)
        heading.paragraph_format.space_before = Pt(before)
        heading.paragraph_format.space_after = Pt(after)
        heading.paragraph_format.line_spacing = 1.2
        heading.paragraph_format.keep_with_next = keep_with_next
        heading.paragraph_format.widow_control = True

    # 一级标题加一条淡色分隔线，二级标题加蓝色竖线
    _add_style_border(doc.styles["Heading 1"], "bottom", DIVIDER_COLOR, "8", "6")
    _add_style_border(doc.styles["Heading 2"], "left", QUOTE_BORDER_COLOR, "18", "8")
    doc.styles["Heading 2"].paragraph_format.left_indent = Pt(10)


def _setup_page(doc: Document, title: str) -> None:
    """设置 A4 页面、页边距、页眉标题和页脚页码"""
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.4)
    section.right_margin = Cm(2.4)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(1.0)
    section.different_first_page_header_footer = True

    if title:
        header = section.header.paragraphs[0]
        header.text = title
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header.paragraph_format.space_after = Pt(2)
        for run in header.runs:
            _format_muted_run(run, size=8.5)
        _add_border(header, "bottom", DIVIDER_COLOR, "4")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(0)
    footer.paragraph_format.space_after = Pt(0)
    _format_muted_run(footer.add_run("第 "), size=8.5)
    _add_page_number_field(footer)
    _format_muted_run(footer.add_run(" 页"), size=8.5)


def _format_muted_run(run, size: float = 8.5) -> None:
    """设置页眉页脚等弱化文字的格式"""
    run.font.name = BODY_FONT
    run.font.size = Pt(size)
    run.font.color.rgb = MUTED_TEXT_COLOR
    _set_east_asia_font(run, EAST_ASIA_FONT)


def _add_page_number_field(paragraph) -> None:
    """在段落中插入 Word PAGE 域，打开文档后自动显示页码"""
    begin_run = paragraph.add_run()
    _format_muted_run(begin_run)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin_run._r.append(begin)

    instruction_run = paragraph.add_run()
    _format_muted_run(instruction_run)
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    instruction_run._r.append(instruction)

    separate_run = paragraph.add_run()
    _format_muted_run(separate_run)
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separate_run._r.append(separate)

    _format_muted_run(paragraph.add_run("1"))

    end_run = paragraph.add_run()
    _format_muted_run(end_run)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)


def _add_style_border(style, side: str, color: str, size: str, space: str) -> None:
    """为样式添加段落边框 (用于标题下划线或左侧强调线)"""
    ppr = style._element.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), size)
    border.set(qn("w:space"), space)
    border.set(qn("w:color"), color)
    borders.append(border)
    ppr.insert_element_before(borders, *_PPR_AFTER_BDR)


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
    """为表格单元格添加纯色底纹，并按架构顺序插入"""
    tcpr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)
    tcpr.insert_element_before(
        shading,
        "w:noWrap",
        "w:tcMar",
        "w:textDirection",
        "w:tcFitText",
        "w:vAlign",
        "w:hideMark",
        "w:headers",
        "w:cellIns",
        "w:cellDel",
        "w:cellMerge",
        "w:tcPrChange",
    )


# rPr 中位于 w:shd 之后的元素 (按 OOXML 架构顺序)
_RPR_AFTER_SHD = (
    "w:fitText",
    "w:vertAlign",
    "w:rtl",
    "w:cs",
    "w:em",
    "w:lang",
    "w:eastAsianLayout",
    "w:specVanish",
    "w:oMath",
)


def _add_run_shading(run, fill: str) -> None:
    """为行内文字添加浅色底纹"""
    rpr = run._element.get_or_add_rPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)
    rpr.insert_element_before(shading, *_RPR_AFTER_SHD)


def _set_table_borders(table, color: str = TABLE_BORDER_COLOR, size: str = "4") -> None:
    """设置表格细边框"""
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), size)
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), color)
        borders.append(border)
    tbl_pr.insert_element_before(
        borders,
        "w:shd",
        "w:tblLayout",
        "w:tblCellMar",
        "w:tblLook",
        "w:tblCaption",
        "w:tblDescription",
    )


def _set_cell_border(cell, side: str, color: str, size: str) -> None:
    """设置单元格单侧边框"""
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.insert_element_before(
            borders,
            "w:shd",
            "w:noWrap",
            "w:tcMar",
            "w:textDirection",
            "w:tcFitText",
            "w:vAlign",
            "w:hideMark",
            "w:headers",
            "w:cellIns",
            "w:cellDel",
            "w:cellMerge",
            "w:tcPrChange",
        )

    border = OxmlElement(f"w:{side}")
    border.set(qn("w:val"), "single")
    border.set(qn("w:sz"), size)
    border.set(qn("w:space"), "0")
    border.set(qn("w:color"), color)
    borders.append(border)


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
            run.font.size = Pt(10)
            _set_east_asia_font(run, EAST_ASIA_FONT)
            run.font.color.rgb = INLINE_CODE_COLOR
            _add_run_shading(run, "F2F4F7")
        elif match.group("link_text") is not None:
            _add_hyperlink(paragraph, match.group("link_text"), match.group("link_url"))

        position = match.end()

    if position < len(text):
        paragraph.add_run(text[position:])


# ==================== 图片加载 ====================


def _clean_image_source(raw_source: str) -> str:
    """去掉图片路径两端的尖括号与可选标题"""
    source = raw_source.strip()

    # ![alt](path "title") -> path
    title_match = re.match(
        r'^(?P<src>.+?)\s+(?P<quote>["\']).*?(?P=quote)\s*$',
        source,
        re.DOTALL,
    )
    if title_match:
        source = title_match.group("src").strip()

    # ![alt](<path with spaces>) -> path with spaces
    if source.startswith("<") and source.endswith(">"):
        source = source[1:-1].strip()

    return source


def _resolve_local_image(base_dir: Path, source: str) -> Path:
    """解析本地图片路径，兼容相对路径、绝对路径与站点根路径"""
    path_text = unquote(source)
    if path_text.lower().startswith("file://"):
        parsed = urlparse(path_text)
        path_text = url2pathname(unquote(parsed.path))

    candidate = Path(path_text).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    if candidate.is_file():
        return candidate

    # 兼容 /images/a.png 这类以斜杠开头的路径：优先按 Markdown 所在目录解析
    if source.startswith(("/", "\\")):
        fallback = base_dir / unquote(source).lstrip("/\\")
        if fallback.is_file():
            return fallback

    return candidate


def _download_image(url: str) -> bytes:
    """下载网络图片，限制大小与超时时间"""
    request = Request(
        url,
        headers={
            "User-Agent": IMAGE_USER_AGENT,
            "Accept": "image/*,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=IMAGE_TIMEOUT_SECONDS) as response:
        data = response.read(MAX_IMAGE_BYTES + 1)

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"图片超过 {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    if not data:
        raise ValueError("图片内容为空")

    return data


def _decode_data_uri(uri: str) -> io.BytesIO:
    """解析 data:image/...;base64,... 形式的图片"""
    header, separator, payload = uri.partition(",")
    if not separator:
        raise ValueError("无效的 Data URI")

    if ";base64" in header.lower():
        data = base64.b64decode(payload, validate=False)
    else:
        data = unquote_to_bytes(payload)

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"图片超过 {MAX_IMAGE_BYTES // (1024 * 1024)} MB")
    if not data:
        raise ValueError("图片内容为空")

    return io.BytesIO(data)


def _load_image(base_dir: Path, source: str) -> Path | io.BytesIO | None:
    """
    加载图片

    返回本地文件路径或内存中的图片数据；本地文件不存在时返回 None。
    网络图片与 Data URI 会在内存中处理。
    """
    if source.lower().startswith("data:"):
        return _decode_data_uri(source)

    if source.lower().startswith(("http://", "https://")):
        return io.BytesIO(_download_image(source))

    candidate = _resolve_local_image(base_dir, source)
    return candidate if candidate.is_file() else None


# ==================== Markdown 渲染器 ====================


class _MarkdownRenderer:
    """按行解析 Markdown，并写入 python-docx 文档"""

    def __init__(
        self,
        doc: Document,
        base_dir: Path,
        text: str,
        warnings: list[str] | None = None,
    ) -> None:
        self.doc = doc
        self.base_dir = base_dir
        self.lines = text.splitlines()
        self.warnings = warnings if warnings is not None else []

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
            self._add_image(match.group("src"), match.group("alt"))
            return

        # ----- HTML 图片 -----
        if stripped.lower().startswith("<img"):
            match = HTML_IMAGE_RE.search(stripped)
            if match:
                self._flush_paragraph()
                alt_match = HTML_ALT_RE.search(stripped)
                alt = alt_match.group("alt") if alt_match else ""
                self._add_image(match.group("src"), alt)
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
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _add_runs(paragraph, " ".join(self.para_buf))
        self.para_buf = []

    def _flush_table(self) -> None:
        """把累积的表格行写入文档，并应用表头、斑马纹与细边框"""
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
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        _set_table_borders(table)

        for row_index, row in enumerate(cells):
            table_row = table.rows[row_index]
            tr_pr = table_row._tr.get_or_add_trPr()
            cant_split = OxmlElement("w:cantSplit")
            tr_pr.append(cant_split)
            if row_index == 0:
                # 表头在跨页时自动重复
                tbl_header = OxmlElement("w:tblHeader")
                tr_pr.append(tbl_header)

            for column_index in range(column_count):
                cell = table.cell(row_index, column_index)
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                cell.text = ""
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_before = Pt(3)
                paragraph.paragraph_format.space_after = Pt(3)
                paragraph.paragraph_format.line_spacing = 1.15
                text = row[column_index] if column_index < len(row) else ""
                _add_runs(paragraph, text)

                if row_index == 0:
                    _add_cell_shading(cell, HEADER_BACKGROUND)
                    for run in paragraph.runs:
                        run.bold = True
                        run.font.size = Pt(10.5)
                        run.font.color.rgb = WHITE
                else:
                    if row_index % 2 == 0:
                        _add_cell_shading(cell, TABLE_STRIPE_BACKGROUND)
                    for run in paragraph.runs:
                        run.font.size = Pt(10)
                        run.font.color.rgb = BODY_COLOR

        self._add_spacer(Pt(8))

    def _add_code_block(self, lines: list[str]) -> None:
        """写入代码块 (浅色卡片 + 左侧蓝色强调线 + 等宽字体)"""
        if not lines:
            return

        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        _set_table_borders(table)

        cell = table.cell(0, 0)
        section = self.doc.sections[0]
        cell.width = section.page_width - section.left_margin - section.right_margin
        _set_cell_border(cell, "left", QUOTE_BORDER_COLOR, "24")
        _add_cell_shading(cell, CODE_BACKGROUND)
        cell.text = ""

        paragraph = cell.paragraphs[0]
        paragraph.paragraph_format.space_before = Pt(5)
        paragraph.paragraph_format.space_after = Pt(5)
        paragraph.paragraph_format.line_spacing = 1.15

        run = paragraph.add_run("\n".join(lines))
        run.font.name = CODE_FONT
        _set_east_asia_font(run, EAST_ASIA_FONT)
        run.font.size = Pt(9.5)
        run.font.color.rgb = CODE_COLOR

        self._add_spacer(Pt(8))

    def _add_horizontal_rule(self) -> None:
        """写入水平分割线 (使用段落下边框模拟)"""
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(8)
        paragraph.paragraph_format.space_after = Pt(8)
        _add_border(paragraph, "bottom", DIVIDER_COLOR, "8")

    def _add_quote(self, text: str) -> None:
        """写入引用块 (浅色底纹 + 左侧蓝色竖线)"""
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Pt(16)
        paragraph.paragraph_format.right_indent = Pt(8)
        paragraph.paragraph_format.space_before = Pt(6)
        paragraph.paragraph_format.space_after = Pt(10)
        _add_runs(paragraph, text)

        for run in paragraph.runs:
            run.font.color.rgb = QUOTE_COLOR

        _add_paragraph_shading(paragraph, QUOTE_BACKGROUND)
        _add_border(paragraph, "left", QUOTE_BORDER_COLOR, "18")

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

        paragraph.paragraph_format.space_after = Pt(3)
        if depth > 0:
            paragraph.paragraph_format.left_indent = Pt(18 * (depth + 1))

        _add_runs(paragraph, content)

    def _add_image(self, raw_source: str, alt: str = "") -> None:
        """写入图片；网络图片会先下载，加载失败时以占位文字提示"""
        source = _clean_image_source(raw_source)
        if not source:
            self._warn("图片路径为空")
            self._add_placeholder("[图片路径为空]")
            return

        try:
            image = _load_image(self.base_dir, source)
        except Exception as exc:
            self._warn(f"图片加载失败: {source} ({exc})")
            self._add_placeholder(f"[图片加载失败: {source}]")
            return

        if image is None:
            self._warn(f"图片未找到: {source}")
            self._add_placeholder(f"[图片未找到: {source}]")
            return

        try:
            if isinstance(image, Path):
                self.doc.add_picture(str(image))
            else:
                self.doc.add_picture(image)
        except Exception as exc:
            self._warn(f"图片格式不支持: {source} ({exc})")
            self._add_placeholder(f"[图片无法插入: {source}]")
            return

        picture_paragraph = self.doc.paragraphs[-1]
        picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        picture_paragraph.paragraph_format.space_before = Pt(6)

        caption = alt.strip()
        has_caption = bool(caption) and caption.lower() not in {"image", "img", "图片"}
        picture_paragraph.paragraph_format.space_after = Pt(2 if has_caption else 8)
        self._scale_picture(self.doc.inline_shapes[-1])

        if has_caption:
            self._add_caption(caption)

    def _scale_picture(self, shape) -> None:
        """把过宽的图片等比缩放到页面可用宽度"""
        section = self.doc.sections[0]
        max_width = section.page_width - section.left_margin - section.right_margin
        if shape.width > max_width:
            ratio = max_width / shape.width
            shape.width = int(shape.width * ratio)
            shape.height = int(shape.height * ratio)

    def _add_caption(self, text: str) -> None:
        """在图片下方写入灰色说明文字"""
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(10)
        run = paragraph.add_run(text)
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = MUTED_TEXT_COLOR

    def _add_spacer(self, height) -> None:
        """插入一个固定高度的空段落，控制块级元素之间的留白"""
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = height

    def _warn(self, message: str) -> None:
        """记录一条转换警告，供界面提示用户"""
        self.warnings.append(message)

    def _add_placeholder(self, text: str) -> None:
        """写入灰色占位说明"""
        paragraph = self.doc.add_paragraph()
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(text)
        run.font.size = Pt(9.5)
        run.font.italic = True
        run.font.color.rgb = MUTED_TEXT_COLOR


def _is_table_separator(row: str) -> bool:
    """判断表格行是否为 |---|---| 形式的分隔行"""
    cells = row.strip().strip("|").split("|")
    return bool(cells) and all(
        TABLE_SEPARATOR_RE.match(cell.strip()) for cell in cells
    )
