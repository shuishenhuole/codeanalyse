//! 轻量 docx（OOXML）生成器
//!
//! Word 导出与 Markdown 转 Word 共用：A4 页面、页眉页脚、标题、表格、
//! 代码卡片与图片。docx 本质是一个 zip 包，这里按 Stored 方式写入各个 XML 部件。

use std::fs::File;
use std::io::Write;
use std::path::Path;

use zip::write::SimpleFileOptions;

const PAGE_W: u32 = 11_906; // A4 宽（twips）
const PAGE_H: u32 = 16_838; // A4 高（twips）
const MARGIN: u32 = 1_440; // 左右上下页边距
const CONTENT_W: u32 = PAGE_W - MARGIN * 2;

const FONT_LATIN: &str = "Microsoft YaHei";
const FONT_EAST_ASIA: &str = "Microsoft YaHei";
const FONT_MONO: &str = "Consolas";

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}

impl Align {
    fn xml(self) -> &'static str {
        match self {
            Self::Left => "left",
            Self::Center => "center",
            Self::Right => "right",
        }
    }
}

/// 段落文本样式
#[derive(Clone, Copy)]
pub struct TextStyle {
    pub bold: bool,
    pub italic: bool,
    pub size_pt: f32,
    pub color: &'static str,
    pub align: Align,
    pub space_before: u32,
    pub space_after: u32,
}

impl Default for TextStyle {
    fn default() -> Self {
        Self {
            bold: false,
            italic: false,
            size_pt: 10.5,
            color: "1F2937",
            align: Align::Left,
            space_before: 0,
            space_after: 0,
        }
    }
}

/// 行内片段（用于 Markdown 的粗体 / 斜体 / 行内代码 / 链接）
#[derive(Clone, Default)]
pub struct InlineRun {
    pub text: String,
    pub bold: bool,
    pub italic: bool,
    pub mono: bool,
    pub underline: bool,
    pub color: Option<&'static str>,
    pub link: Option<String>,
}

impl InlineRun {
    pub fn new(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            ..Default::default()
        }
    }
}

/// 表格样式
#[derive(Clone, Copy)]
pub struct TableStyle {
    pub header_fill: &'static str,
    pub stripe: bool,
    pub bold_last_row: bool,
    pub highlight_last_row: Option<&'static str>,
    pub right_align_from: usize,
}

impl Default for TableStyle {
    fn default() -> Self {
        Self {
            header_fill: "EEF2FB",
            stripe: true,
            bold_last_row: false,
            highlight_last_row: None,
            right_align_from: 1,
        }
    }
}

struct DocxImage {
    file_name: String,
    bytes: Vec<u8>,
    rid: String,
}

/// docx 文档构建器
pub struct Docx {
    body: String,
    images: Vec<DocxImage>,
    links: Vec<(String, String)>,
    header_text: Option<String>,
    footer: bool,
    next_image: usize,
    next_link: usize,
    next_doc_pr: usize,
}

impl Default for Docx {
    fn default() -> Self {
        Self::new()
    }
}

impl Docx {
    pub fn new() -> Self {
        Self {
            body: String::new(),
            images: Vec::new(),
            links: Vec::new(),
            header_text: None,
            footer: false,
            next_image: 1,
            next_link: 1,
            next_doc_pr: 1,
        }
    }

    /// 启用页眉（文字）与页脚（页码）
    pub fn with_header_footer(mut self, header: impl Into<String>) -> Self {
        self.header_text = Some(header.into());
        self.footer = true;
        self
    }

    pub fn heading(&mut self, text: &str, level: u8) {
        let style = match level {
            0 => "Title",
            1 => "Heading1",
            2 => "Heading2",
            _ => "Heading3",
        };
        self.body.push_str(&format!(
            "<w:p><w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr><w:r><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>",
            esc(text)
        ));
    }

    pub fn text(&mut self, text: &str, style: &TextStyle) {
        let runs = [InlineRun::new(text)];
        self.text_runs(&runs, style);
    }

    pub fn text_runs(&mut self, runs: &[InlineRun], style: &TextStyle) {
        let mut xml = String::from("<w:p><w:pPr>");
        xml.push_str(&format!("<w:jc w:val=\"{}\"/>", style.align.xml()));
        xml.push_str(&format!(
            "<w:spacing w:before=\"{}\" w:after=\"{}\" w:line=\"276\" w:lineRule=\"auto\"/>",
            style.space_before, style.space_after
        ));
        xml.push_str("</w:pPr>");

        for run in runs {
            let link_rid = run
                .link
                .as_deref()
                .filter(|url| !url.is_empty())
                .map(|url| self.add_link(url));
            xml.push_str(&run_xml(run, style, link_rid.as_deref()));
        }
        xml.push_str("</w:p>");
        self.body.push_str(&xml);
    }

    /// 无序 / 有序列表项
    pub fn list_item(&mut self, text: &str, ordered: bool, index: usize) {
        let marker = if ordered {
            format!("{index}. ")
        } else {
            "• ".to_owned()
        };
        self.body.push_str(&format!(
            "<w:p><w:pPr><w:ind w:left=\"720\" w:hanging=\"360\"/><w:spacing w:before=\"40\" w:after=\"40\"/></w:pPr>\
             <w:r><w:rPr><w:rFonts w:ascii=\"{FONT_LATIN}\" w:hAnsi=\"{FONT_LATIN}\" w:eastAsia=\"{FONT_EAST_ASIA}\"/><w:sz w:val=\"21\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r>\
             <w:r><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>",
            esc(&marker),
            esc(text)
        ));
    }

    /// 引用块（左侧竖线 + 灰色文字）
    pub fn quote(&mut self, text: &str) {
        self.body.push_str(&format!(
            "<w:p><w:pPr><w:pBdr><w:left w:val=\"single\" w:sz=\"18\" w:space=\"10\" w:color=\"D1D5DB\"/></w:pBdr>\
             <w:ind w:left=\"360\"/><w:spacing w:before=\"80\" w:after=\"80\"/></w:pPr>\
             <w:r><w:rPr><w:i/><w:color w:val=\"6B7280\"/><w:sz w:val=\"21\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>",
            esc(text)
        ));
    }

    /// 代码卡片：1x1 表格 + 浅灰底色，逐行排版保证换行可见
    pub fn code_block(&mut self, code: &str, lang: Option<&str>) {
        self.body.push_str(
            "<w:tbl><w:tblPr><w:tblW w:w=\"9026\" w:type=\"dxa\"/><w:tblBorders>\
             <w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:insideH w:val=\"nil\"/><w:insideV w:val=\"nil\"/></w:tblBorders>\
             <w:tblCellMar><w:top w:w=\"120\" w:type=\"dxa\"/><w:left w:w=\"160\" w:type=\"dxa\"/>\
             <w:bottom w:w=\"120\" w:type=\"dxa\"/><w:right w:w=\"160\" w:type=\"dxa\"/></w:tblCellMar></w:tblPr>\
             <w:tblGrid><w:gridCol w:w=\"9026\"/></w:tblGrid><w:tr><w:tc>\
             <w:tcPr><w:tcW w:w=\"9026\" w:type=\"dxa\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"F6F8FA\"/></w:tcPr>",
        );

        if let Some(lang) = lang.filter(|l| !l.is_empty()) {
            self.body.push_str(&format!(
                "<w:p><w:pPr><w:spacing w:before=\"0\" w:after=\"60\"/></w:pPr>\
                 <w:r><w:rPr><w:color w:val=\"9CA3AF\"/><w:sz w:val=\"16\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>",
                esc(&lang.to_uppercase())
            ));
        }

        let mut lines: Vec<&str> = code.split('\n').collect();
        if lines.len() > 1 && lines.last().is_some_and(|l| l.is_empty()) {
            lines.pop();
        }
        if lines.is_empty() {
            lines.push("");
        }
        for line in lines {
            self.body.push_str(&format!(
                "<w:p><w:pPr><w:spacing w:before=\"0\" w:after=\"0\" w:line=\"240\" w:lineRule=\"auto\"/></w:pPr>\
                 <w:r><w:rPr><w:rFonts w:ascii=\"{FONT_MONO}\" w:hAnsi=\"{FONT_MONO}\" w:eastAsia=\"{FONT_EAST_ASIA}\"/><w:sz w:val=\"17\"/><w:color w:val=\"1F2937\"/></w:rPr>\
                 <w:t xml:space=\"preserve\">{}</w:t></w:r></w:p>",
                esc(line)
            ));
        }

        self.body.push_str("</w:tc></w:tr></w:tbl>");
        // 相邻表格之间需要段落分隔，避免 Word 将两个表格合并
        self.body
            .push_str("<w:p><w:pPr><w:spacing w:before=\"0\" w:after=\"0\" w:line=\"120\" w:lineRule=\"auto\"/></w:pPr></w:p>");
    }

    /// 表格（首行表头，可选斑马纹与末行高亮）
    pub fn table(
        &mut self,
        headers: &[String],
        rows: &[Vec<String>],
        widths: &[u32],
        style: &TableStyle,
    ) {
        let widths = normalize_widths(widths, headers.len());
        self.body.push_str(
            "<w:tbl><w:tblPr><w:tblW w:w=\"9026\" w:type=\"dxa\"/><w:tblBorders>\
             <w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/>\
             <w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"E5E7EB\"/></w:tblBorders>\
             <w:tblCellMar><w:top w:w=\"80\" w:type=\"dxa\"/><w:left w:w=\"120\" w:type=\"dxa\"/>\
             <w:bottom w:w=\"80\" w:type=\"dxa\"/><w:right w:w=\"120\" w:type=\"dxa\"/></w:tblCellMar></w:tblPr><w:tblGrid>",
        );
        for width in &widths {
            self.body.push_str(&format!("<w:gridCol w:w=\"{width}\"/>"));
        }
        self.body.push_str("</w:tblGrid>");

        // 表头
        self.body
            .push_str("<w:tr><w:trPr><w:tblHeader/></w:trPr>");
        for (index, header) in headers.iter().enumerate() {
            let align = if index >= style.right_align_from {
                Align::Right
            } else {
                Align::Left
            };
            self.body.push_str(&format!(
                "<w:tc><w:tcPr><w:tcW w:w=\"{}\" w:type=\"dxa\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{}\"/><w:vAlign w:val=\"center\"/></w:tcPr>\
                 <w:p><w:pPr><w:jc w:val=\"{}\"/><w:spacing w:before=\"40\" w:after=\"40\"/></w:pPr>\
                 <w:r><w:rPr><w:b/><w:color w:val=\"374151\"/><w:sz w:val=\"20\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p></w:tc>",
                widths[index],
                style.header_fill,
                align.xml(),
                esc(header)
            ));
        }
        self.body.push_str("</w:tr>");

        let last_index = rows.len().saturating_sub(1);
        for (row_index, row) in rows.iter().enumerate() {
            let is_last = row_index == last_index && style.bold_last_row;
            let fill = if is_last {
                style.highlight_last_row.unwrap_or("FFFFFF").to_owned()
            } else if style.stripe && row_index % 2 == 1 {
                "F8FAFC".to_owned()
            } else {
                "FFFFFF".to_owned()
            };
            self.body.push_str("<w:tr>");
            for (col_index, cell) in row.iter().enumerate() {
                let width = widths.get(col_index).copied().unwrap_or(1500);
                let align = if col_index >= style.right_align_from {
                    Align::Right
                } else {
                    Align::Left
                };
                self.body.push_str(&format!(
                    "<w:tc><w:tcPr><w:tcW w:w=\"{width}\" w:type=\"dxa\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"{fill}\"/><w:vAlign w:val=\"center\"/></w:tcPr>\
                     <w:p><w:pPr><w:jc w:val=\"{}\"/><w:spacing w:before=\"40\" w:after=\"40\"/></w:pPr>\
                     <w:r><w:rPr>{}<w:sz w:val=\"20\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p></w:tc>",
                    align.xml(),
                    if is_last { "<w:b/>" } else { "" },
                    esc(cell)
                ));
            }
            self.body.push_str("</w:tr>");
        }
        self.body.push_str("</w:tbl>");
        self.body
            .push_str("<w:p><w:pPr><w:spacing w:before=\"0\" w:after=\"0\" w:line=\"120\" w:lineRule=\"auto\"/></w:pPr></w:p>");
    }

    pub fn page_break(&mut self) {
        self.body
            .push_str("<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>");
    }

    /// 水平分割线（用段落底边框模拟）
    pub fn horizontal_rule(&mut self) {
        self.body.push_str(
            "<w:p><w:pPr><w:pBdr><w:bottom w:val=\"single\" w:sz=\"6\" w:space=\"1\" w:color=\"D1D5DB\"/></w:pBdr>\
             <w:spacing w:before=\"160\" w:after=\"160\"/></w:pPr></w:p>",
        );
    }

    /// 插入图片，返回是否成功
    pub fn image(
        &mut self,
        bytes: Vec<u8>,
        ext: &str,
        caption: Option<&str>,
        max_width_twips: u32,
    ) -> Result<(), String> {
        let (px_w, px_h) = image::ImageReader::new(std::io::Cursor::new(&bytes))
            .with_guessed_format()
            .map_err(|err| err.to_string())?
            .into_dimensions()
            .map_err(|err| err.to_string())?;
        if px_w == 0 || px_h == 0 {
            return Err("图片尺寸无效".to_owned());
        }

        // 96 dpi 下 1px = 15 twips；限制最大宽度
        let max_twips = max_width_twips.min(CONTENT_W);
        let twips_w = (px_w as u64 * 15).min(max_twips as u64) as u32;
        let twips_h = (px_h as u64 * twips_w as u64 / px_w as u64).max(1) as u32;
        let cx = twips_w as u64 * 635;
        let cy = twips_h as u64 * 635;

        let ext = match ext.to_lowercase().as_str() {
            "jpg" | "jpeg" => "jpg",
            "gif" => "gif",
            "bmp" => "bmp",
            _ => "png",
        };
        let index = self.next_image;
        self.next_image += 1;
        let rid = format!("rIdImg{index}");
        let file_name = format!("image{index}.{ext}");
        self.images.push(DocxImage {
            file_name: file_name.clone(),
            bytes,
            rid: rid.clone(),
        });

        let doc_pr = self.next_doc_pr;
        self.next_doc_pr += 1;

        self.body.push_str(&format!(
            "<w:p><w:pPr><w:jc w:val=\"center\"/><w:spacing w:before=\"120\" w:after=\"40\"/></w:pPr><w:r><w:drawing>\
             <wp:inline distT=\"0\" distB=\"0\" distL=\"0\" distR=\"0\">\
             <wp:extent cx=\"{cx}\" cy=\"{cy}\"/><wp:effectExtent l=\"0\" t=\"0\" r=\"0\" b=\"0\"/>\
             <wp:docPr id=\"{doc_pr}\" name=\"Picture {doc_pr}\"/>\
             <wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect=\"1\"/></wp:cNvGraphicFramePr>\
             <a:graphic><a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">\
             <pic:pic><pic:nvPicPr><pic:cNvPr id=\"{doc_pr}\" name=\"{file_name}\"/><pic:cNvPicPr/></pic:nvPicPr>\
             <pic:blipFill><a:blip r:embed=\"{rid}\"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>\
             <pic:spPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"{cx}\" cy=\"{cy}\"/></a:xfrm>\
             <a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>\
             </a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
        ));

        if let Some(caption) = caption.filter(|c| !c.trim().is_empty()) {
            self.text(
                caption,
                &TextStyle {
                    size_pt: 9.0,
                    color: "9CA3AF",
                    align: Align::Center,
                    space_after: 160,
                    ..Default::default()
                },
            );
        }
        Ok(())
    }

    fn add_link(&mut self, url: &str) -> String {
        let rid = format!("rIdLink{}", self.next_link);
        self.next_link += 1;
        self.links.push((rid.clone(), url.to_owned()));
        rid
    }

    /// 写出 docx 文件
    pub fn save(&self, path: &Path) -> Result<(), String> {
        let file = File::create(path).map_err(|err| format!("创建文件失败: {err}"))?;
        let mut zip = zip::ZipWriter::new(file);
        let options = || {
            SimpleFileOptions::default()
                .compression_method(zip::CompressionMethod::Stored)
                .unix_permissions(0o644)
        };

        write_zip(&mut zip, "[Content_Types].xml", &self.content_types(), options())?;
        write_zip(&mut zip, "_rels/.rels", PACKAGE_RELS, options())?;
        write_zip(&mut zip, "word/document.xml", &self.document_xml(), options())?;
        write_zip(&mut zip, "word/styles.xml", STYLES_XML, options())?;
        write_zip(
            &mut zip,
            "word/_rels/document.xml.rels",
            &self.document_rels(),
            options(),
        )?;
        if self.header_text.is_some() {
            write_zip(&mut zip, "word/header1.xml", &self.header_xml(), options())?;
        }
        if self.footer {
            write_zip(&mut zip, "word/footer1.xml", &self.footer_xml(), options())?;
        }
        for image in &self.images {
            write_zip(
                &mut zip,
                &format!("word/media/{}", image.file_name),
                &image.bytes,
                options(),
            )?;
        }

        zip.finish().map_err(|err| format!("写入压缩包失败: {err}"))?;
        Ok(())
    }

    fn content_types(&self) -> String {
        let mut xml = String::from(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
             <Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\
             <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\
             <Default Extension=\"xml\" ContentType=\"application/xml\"/>\
             <Default Extension=\"png\" ContentType=\"image/png\"/>\
             <Default Extension=\"jpg\" ContentType=\"image/jpeg\"/>\
             <Default Extension=\"jpeg\" ContentType=\"image/jpeg\"/>\
             <Default Extension=\"gif\" ContentType=\"image/gif\"/>\
             <Default Extension=\"bmp\" ContentType=\"image/bmp\"/>\
             <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>\
             <Override PartName=\"/word/styles.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml\"/>",
        );
        if self.header_text.is_some() {
            xml.push_str("<Override PartName=\"/word/header1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml\"/>");
        }
        if self.footer {
            xml.push_str("<Override PartName=\"/word/footer1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml\"/>");
        }
        xml.push_str("</Types>");
        xml
    }

    fn document_rels(&self) -> String {
        let mut xml = String::from(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
             <Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\
             <Relationship Id=\"rIdStyles\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles\" Target=\"styles.xml\"/>",
        );
        if self.header_text.is_some() {
            xml.push_str("<Relationship Id=\"rIdHeader\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/header\" Target=\"header1.xml\"/>");
        }
        if self.footer {
            xml.push_str("<Relationship Id=\"rIdFooter\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer\" Target=\"footer1.xml\"/>");
        }
        for image in &self.images {
            xml.push_str(&format!(
                "<Relationship Id=\"{}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"media/{}\"/>",
                image.rid, image.file_name
            ));
        }
        for (rid, url) in &self.links {
            xml.push_str(&format!(
                "<Relationship Id=\"{rid}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink\" Target=\"{}\" TargetMode=\"External\"/>",
                esc(url)
            ));
        }
        xml.push_str("</Relationships>");
        xml
    }

    fn document_xml(&self) -> String {
        format!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
             <w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" \
             xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" \
             xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" \
             xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" \
             xmlns:pic=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">\
             <w:body>{}{}</w:body></w:document>",
            self.body,
            self.sect_pr()
        )
    }

    fn sect_pr(&self) -> String {
        let mut xml = String::from("<w:sectPr>");
        if self.header_text.is_some() {
            xml.push_str("<w:headerReference w:type=\"default\" r:id=\"rIdHeader\"/>");
        }
        if self.footer {
            xml.push_str("<w:footerReference w:type=\"default\" r:id=\"rIdFooter\"/>");
        }
        xml.push_str(&format!(
            "<w:pgSz w:w=\"{PAGE_W}\" w:h=\"{PAGE_H}\"/>\
             <w:pgMar w:top=\"{MARGIN}\" w:right=\"{MARGIN}\" w:bottom=\"{MARGIN}\" w:left=\"{MARGIN}\" w:header=\"851\" w:footer=\"992\" w:gutter=\"0\"/>\
             <w:cols w:space=\"720\"/><w:docGrid w:linePitch=\"312\"/></w:sectPr>"
        ));
        xml
    }

    fn header_xml(&self) -> String {
        let title = self.header_text.as_deref().unwrap_or_default();
        format!(
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
             <w:hdr xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\
             <w:p><w:pPr><w:pBdr><w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"4\" w:color=\"E5E7EB\"/></w:pBdr><w:jc w:val=\"right\"/></w:pPr>\
             <w:r><w:rPr><w:color w:val=\"9CA3AF\"/><w:sz w:val=\"18\"/></w:rPr><w:t xml:space=\"preserve\">{}</w:t></w:r></w:p></w:hdr>",
            esc(title)
        )
    }

    fn footer_xml(&self) -> String {
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
         <w:ftr xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\
         <w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr>\
         <w:r><w:rPr><w:color w:val=\"9CA3AF\"/><w:sz w:val=\"18\"/></w:rPr><w:t xml:space=\"preserve\">第 </w:t></w:r>\
         <w:r><w:fldChar w:fldCharType=\"begin\"/></w:r>\
         <w:r><w:instrText xml:space=\"preserve\"> PAGE </w:instrText></w:r>\
         <w:r><w:fldChar w:fldCharType=\"separate\"/></w:r>\
         <w:r><w:t>1</w:t></w:r>\
         <w:r><w:fldChar w:fldCharType=\"end\"/></w:r>\
         <w:r><w:rPr><w:color w:val=\"9CA3AF\"/><w:sz w:val=\"18\"/></w:rPr><w:t xml:space=\"preserve\"> 页 / 共 </w:t></w:r>\
         <w:r><w:fldChar w:fldCharType=\"begin\"/></w:r>\
         <w:r><w:instrText xml:space=\"preserve\"> NUMPAGES </w:instrText></w:r>\
         <w:r><w:fldChar w:fldCharType=\"separate\"/></w:r>\
         <w:r><w:t>1</w:t></w:r>\
         <w:r><w:fldChar w:fldCharType=\"end\"/></w:r>\
         <w:r><w:rPr><w:color w:val=\"9CA3AF\"/><w:sz w:val=\"18\"/></w:rPr><w:t xml:space=\"preserve\"> 页</w:t></w:r>\
         </w:p></w:ftr>"
            .to_owned()
    }
}

fn run_xml(run: &InlineRun, style: &TextStyle, link_rid: Option<&str>) -> String {
    let mut rpr = String::from("<w:rPr>");
    if run.bold {
        rpr.push_str("<w:b/>");
    }
    if run.italic {
        rpr.push_str("<w:i/>");
    }
    if run.underline {
        rpr.push_str("<w:u w:val=\"single\"/>");
    }
    let color = run.color.unwrap_or(style.color);
    rpr.push_str(&format!("<w:color w:val=\"{color}\"/>"));
    rpr.push_str(&format!("<w:sz w:val=\"{}\"/>", (style.size_pt * 2.0).round() as u32));
    if run.mono {
        rpr.push_str(&format!(
            "<w:rFonts w:ascii=\"{FONT_MONO}\" w:hAnsi=\"{FONT_MONO}\" w:eastAsia=\"{FONT_EAST_ASIA}\"/>"
        ));
    }
    rpr.push_str("</w:rPr>");

    let text = text_xml(&run.text);
    if let Some(rid) = link_rid {
        return format!("<w:hyperlink r:id=\"{rid}\">{rpr}{text}</w:hyperlink>");
    }
    format!("<w:r>{rpr}{text}</w:r>")
}

fn text_xml(text: &str) -> String {
    let mut xml = String::new();
    for (index, line) in text.split('\n').enumerate() {
        if index > 0 {
            xml.push_str("<w:br/>");
        }
        xml.push_str(&format!(
            "<w:t xml:space=\"preserve\">{}</w:t>",
            esc(line)
        ));
    }
    xml
}

fn esc(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for ch in text.chars() {
        match ch {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&apos;"),
            '\t' => out.push_str("    "),
            c if (c as u32) < 0x20 && c != '\n' && c != '\r' => {}
            c => out.push(c),
        }
    }
    out
}

fn normalize_widths(widths: &[u32], columns: usize) -> Vec<u32> {
    if widths.len() == columns {
        return widths.to_vec();
    }
    let base = CONTENT_W / columns.max(1) as u32;
    vec![base; columns]
}

fn write_zip(
    zip: &mut zip::ZipWriter<File>,
    name: &str,
    data: impl AsRef<[u8]>,
    options: SimpleFileOptions,
) -> Result<(), String> {
    zip.start_file(name, options)
        .map_err(|err| format!("写入 {name} 失败: {err}"))?;
    zip.write_all(data.as_ref())
        .map_err(|err| format!("写入 {name} 失败: {err}"))
}

const PACKAGE_RELS: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">\
<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>\
</Relationships>";

const STYLES_XML: &str = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\
<w:styles xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">\
<w:docDefaults>\
<w:rPrDefault><w:rPr><w:rFonts w:ascii=\"Microsoft YaHei\" w:eastAsia=\"Microsoft YaHei\" w:hAnsi=\"Microsoft YaHei\" w:cs=\"Microsoft YaHei\"/><w:sz w:val=\"21\"/><w:szCs w:val=\"21\"/><w:lang w:val=\"en-US\" w:eastAsia=\"zh-CN\"/></w:rPr></w:rPrDefault>\
<w:pPrDefault><w:pPr><w:spacing w:after=\"0\" w:line=\"276\" w:lineRule=\"auto\"/></w:pPr></w:pPrDefault>\
</w:docDefaults>\
<w:style w:type=\"paragraph\" w:default=\"1\" w:styleId=\"Normal\"><w:name w:val=\"Normal\"/><w:qFormat/></w:style>\
<w:style w:type=\"paragraph\" w:styleId=\"Title\"><w:name w:val=\"Title\"/><w:basedOn w:val=\"Normal\"/><w:qFormat/><w:pPr><w:jc w:val=\"center\"/><w:spacing w:before=\"240\" w:after=\"240\"/></w:pPr><w:rPr><w:b/><w:sz w:val=\"52\"/><w:color w:val=\"111827\"/></w:rPr></w:style>\
<w:style w:type=\"paragraph\" w:styleId=\"Heading1\"><w:name w:val=\"heading 1\"/><w:basedOn w:val=\"Normal\"/><w:next w:val=\"Normal\"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before=\"360\" w:after=\"160\"/><w:outlineLvl w:val=\"0\"/></w:pPr><w:rPr><w:b/><w:sz w:val=\"32\"/><w:color w:val=\"111827\"/></w:rPr></w:style>\
<w:style w:type=\"paragraph\" w:styleId=\"Heading2\"><w:name w:val=\"heading 2\"/><w:basedOn w:val=\"Normal\"/><w:next w:val=\"Normal\"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before=\"300\" w:after=\"120\"/><w:outlineLvl w:val=\"1\"/></w:pPr><w:rPr><w:b/><w:sz w:val=\"28\"/><w:color w:val=\"1F2937\"/></w:rPr></w:style>\
<w:style w:type=\"paragraph\" w:styleId=\"Heading3\"><w:name w:val=\"heading 3\"/><w:basedOn w:val=\"Normal\"/><w:next w:val=\"Normal\"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before=\"240\" w:after=\"100\"/><w:outlineLvl w:val=\"2\"/></w:pPr><w:rPr><w:b/><w:sz w:val=\"24\"/><w:color w:val=\"374151\"/></w:rPr></w:style>\
</w:styles>";
