//! Markdown 转 Word
//!
//! 覆盖常用 Markdown 语法：标题、段落（粗体/斜体/行内代码/链接）、
//! 有序/无序列表、引用、代码块、表格、水平线、本地图片与 Data URI 图片。
//!
//! 说明：网络图片（http/https）不会自动下载，转为占位提示并记入 warnings，
//! 与 Python 版「图片未插入时保留占位」的行为一致。

use std::path::{Path, PathBuf};

use base64::Engine as _;

use crate::docx::{Align, Docx, InlineRun, TableStyle, TextStyle};

/// 图片最大宽度：A4 可用宽度（9026 twips）的 70%
const IMAGE_MAX_WIDTH_TWIPS: u32 = 6_300;

/// 转换结果
pub struct ConvertResult {
    /// 实际写出的 docx 路径
    pub output: PathBuf,
    /// 图片缺失等非致命问题
    pub warnings: Vec<String>,
}

/// Markdown 转 Word 主入口
pub fn convert_markdown_to_docx(input: &Path, output: &Path) -> Result<ConvertResult, String> {
    let text = std::fs::read_to_string(input)
        .map_err(|err| format!("读取 Markdown 文件失败: {err}"))?;
    let base_dir = input
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .to_path_buf();
    let title = input
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("Markdown 文档")
        .to_owned();

    let docx = Docx::new().with_header_footer(format!("Markdown 文档 · {title}"));
    let mut parser = MarkdownParser {
        lines: text.lines().map(str::to_owned).collect(),
        pos: 0,
        docx,
        base_dir,
        warnings: Vec::new(),
    };
    parser.parse();
    parser.docx.save(output)?;

    Ok(ConvertResult {
        output: output.to_path_buf(),
        warnings: parser.warnings,
    })
}

struct MarkdownParser {
    lines: Vec<String>,
    pos: usize,
    docx: Docx,
    base_dir: PathBuf,
    warnings: Vec<String>,
}

impl MarkdownParser {
    /// 逐行扫描并分派到各块级解析器
    fn parse(&mut self) {
        self.skip_front_matter();
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].trim().to_owned();
            if line.is_empty() {
                self.pos += 1;
                continue;
            }
            if is_fence(&line) {
                self.parse_code_fence();
            } else if let Some((level, text)) = parse_heading(&line) {
                self.docx.heading(&text, level);
                self.pos += 1;
            } else if is_hr(&line) {
                self.docx.horizontal_rule();
                self.pos += 1;
            } else if line.starts_with('>') {
                self.parse_quote();
            } else if self.is_table_start() {
                self.parse_table();
            } else if self.try_parse_image() {
                // try_parse_image 内部推进 pos
            } else if is_list_item(&line) {
                self.parse_list_item();
            } else if line.starts_with('<') && line.ends_with('>') {
                // 其他 HTML 块（如 <div>、<p>）直接忽略
                self.pos += 1;
            } else {
                self.parse_paragraph();
            }
        }
    }

    /// 跳过文件头部的 YAML front matter（--- ... ---）
    fn skip_front_matter(&mut self) {
        if !self.lines.first().is_some_and(|l| l.trim() == "---") {
            return;
        }
        if let Some(offset) = self.lines.iter().skip(1).position(|l| l.trim() == "---") {
            self.pos = offset + 2;
        }
    }

    fn parse_code_fence(&mut self) {
        let fence = self.lines[self.pos].trim_start().to_owned();
        let marker = if fence.starts_with("```") { "```" } else { "~~~" };
        let lang = fence
            .trim_start_matches(marker)
            .trim()
            .trim_matches(|c| c == '{' || c == '}')
            .to_owned();
        self.pos += 1;

        let mut code_lines = Vec::new();
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].clone();
            if line.trim_start().starts_with(marker) {
                self.pos += 1;
                break;
            }
            code_lines.push(line);
            self.pos += 1;
        }

        let lang = if lang.is_empty() { None } else { Some(lang.as_str()) };
        self.docx.code_block(&code_lines.join("\n"), lang);
    }

    fn parse_quote(&mut self) {
        let mut parts = Vec::new();
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].trim().to_owned();
            let Some(rest) = line.strip_prefix('>') else {
                break;
            };
            parts.push(rest.trim().to_owned());
            self.pos += 1;
        }
        self.docx.quote(&join_lines(&parts));
    }

    fn parse_list_item(&mut self) {
        let line = self.lines[self.pos].trim().to_owned();
        if let Some(item) = line
            .strip_prefix("- ")
            .or_else(|| line.strip_prefix("* "))
            .or_else(|| line.strip_prefix("+ "))
        {
            self.docx.list_item(&plain_text(item), false, 0);
        } else if let Some((number, text)) = parse_ordered_item(&line) {
            self.docx.list_item(&plain_text(text), true, number);
        }
        self.pos += 1;
    }

    /// 当前行是否为表格起始（本行含 |，下一行为分隔行）
    fn is_table_start(&self) -> bool {
        if self.pos + 1 >= self.lines.len() {
            return false;
        }
        let line = self.lines[self.pos].trim();
        line.contains('|') && is_table_separator(self.lines[self.pos + 1].trim())
    }

    fn parse_table(&mut self) {
        let header: Vec<String> = split_table_row(&self.lines[self.pos])
            .iter()
            .map(|cell| plain_text(cell))
            .collect();
        self.pos += 2; // 跳过表头与 |---| 分隔行

        let mut rows = Vec::new();
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].trim().to_owned();
            if line.is_empty() || !line.contains('|') {
                break;
            }
            rows.push(
                split_table_row(&line)
                    .iter()
                    .map(|cell| plain_text(cell))
                    .collect(),
            );
            self.pos += 1;
        }

        // 表格内容以文本为主，默认全部左对齐
        let style = TableStyle {
            header_fill: "EEF2FB",
            stripe: true,
            right_align_from: usize::MAX,
            ..Default::default()
        };
        self.docx.table(&header, &rows, &[], &style);
    }

    /// 尝试把当前行解析为图片，成功返回 true
    fn try_parse_image(&mut self) -> bool {
        let line = self.lines[self.pos].trim().to_owned();
        let Some((alt, src)) = parse_markdown_image(&line).or_else(|| parse_html_image(&line)) else {
            return false;
        };

        // 图注优先取 HTML 的 <em>/<figcaption>，其次取下一行的斜体文字
        let mut caption = extract_html_tag(&line, "em")
            .or_else(|| extract_html_tag(&line, "figcaption"))
            .filter(|text| !text.trim().is_empty());
        if caption.is_none() {
            if let Some(next) = self.lines.get(self.pos + 1).map(|l| l.trim().to_owned()) {
                if let Some(text) = italic_caption(&next) {
                    caption = Some(text);
                    self.pos += 1;
                }
            }
        }
        if caption.is_none() && !alt.trim().is_empty() {
            caption = Some(alt);
        }

        self.insert_image(&src, caption.as_deref());
        self.pos += 1;
        true
    }

    /// 读取图片并写入文档，失败时写入占位提示
    fn insert_image(&mut self, src: &str, caption: Option<&str>) {
        match self.load_image(src) {
            Ok((bytes, ext)) => {
                if let Err(err) = self.docx.image(bytes, &ext, caption, IMAGE_MAX_WIDTH_TWIPS) {
                    self.warnings.push(format!("图片插入失败: {src}（{err}）"));
                    self.placeholder(src);
                }
            }
            Err(reason) => {
                self.warnings.push(format!("{reason}: {src}"));
                self.placeholder(src);
            }
        }
    }

    /// 支持 Data URI 与本地路径；网络图片返回错误（不自动下载）
    fn load_image(&self, src: &str) -> Result<(Vec<u8>, String), String> {
        if let Some(rest) = src.strip_prefix("data:image/") {
            let (meta, payload) = rest
                .split_once(',')
                .ok_or_else(|| "Data URI 格式无效".to_owned())?;
            let ext = meta.split(';').next().unwrap_or("png").to_lowercase();
            let bytes = base64::engine::general_purpose::STANDARD
                .decode(payload.trim())
                .map_err(|err| format!("Data URI 解码失败（{err}）"))?;
            return Ok((bytes, ext));
        }

        if src.starts_with("http://") || src.starts_with("https://") {
            return Err("网络图片未插入（当前版本仅处理本地图片）".to_owned());
        }

        let path = Path::new(src);
        let full = if path.is_absolute() {
            path.to_path_buf()
        } else {
            self.base_dir.join(path)
        };
        let bytes = std::fs::read(&full)
            .map_err(|err| format!("图片读取失败（{}：{err}）", full.display()))?;
        let ext = full
            .extension()
            .and_then(|ext| ext.to_str())
            .unwrap_or("png")
            .to_lowercase();
        Ok((bytes, ext))
    }

    fn placeholder(&mut self, src: &str) {
        self.docx.text(
            &format!("[图片未插入] {src}"),
            &TextStyle {
                italic: true,
                size_pt: 9.0,
                color: "9CA3AF",
                align: Align::Left,
                space_after: 120,
                ..Default::default()
            },
        );
    }

    /// 收集连续普通行并合并为一个段落
    fn parse_paragraph(&mut self) {
        let mut parts = Vec::new();
        while self.pos < self.lines.len() {
            let line = self.lines[self.pos].trim().to_owned();
            if line.is_empty() || is_block_start(&line) || self.is_table_start() {
                break;
            }
            parts.push(line);
            self.pos += 1;
        }
        if parts.is_empty() {
            self.pos += 1;
            return;
        }

        let text = join_lines(&parts);
        let runs = parse_inline(&text);
        self.docx.text_runs(
            &runs,
            &TextStyle {
                size_pt: 10.5,
                space_after: 120,
                ..Default::default()
            },
        );
    }
}

// ==================== 行级识别辅助 ====================

fn is_fence(line: &str) -> bool {
    line.starts_with("```") || line.starts_with("~~~")
}

fn is_hr(line: &str) -> bool {
    let compact: String = line.chars().filter(|c| !c.is_whitespace()).collect();
    let mut chars = compact.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    compact.len() >= 3 && matches!(first, '-' | '*' | '_') && chars.all(|c| c == first)
}

fn is_table_separator(line: &str) -> bool {
    line.contains('|')
        && line.contains('-')
        && line
            .chars()
            .all(|c| matches!(c, '|' | '-' | ':' | ' ' | '\t'))
}

fn is_list_item(line: &str) -> bool {
    line.starts_with("- ")
        || line.starts_with("* ")
        || line.starts_with("+ ")
        || parse_ordered_item(line).is_some()
}

/// 有序列表项：`1. 内容` 或 `1) 内容`
fn parse_ordered_item(line: &str) -> Option<(usize, &str)> {
    let digits_end = line.find(|c: char| !c.is_ascii_digit())?;
    if digits_end == 0 {
        return None;
    }
    let rest = &line[digits_end..];
    if let Some(text) = rest.strip_prefix(". ") {
        return Some((line[..digits_end].parse().ok()?, text));
    }
    if let Some(text) = rest.strip_prefix(") ") {
        return Some((line[..digits_end].parse().ok()?, text));
    }
    None
}

/// 块级起始标记（用于段落收集时判断段落结束）
fn is_block_start(line: &str) -> bool {
    is_fence(line)
        || is_hr(line)
        || line.starts_with('#')
        || line.starts_with('>')
        || is_list_item(line)
        || line.starts_with("![")
        || line.starts_with("<img")
}

fn parse_heading(line: &str) -> Option<(u8, String)> {
    let hashes = line.chars().take_while(|c| *c == '#').count();
    if hashes == 0 || hashes > 6 {
        return None;
    }
    let rest = &line[hashes..];
    if !rest.starts_with(' ') && !rest.starts_with('\t') {
        return None;
    }
    let text = rest.trim().trim_end_matches('#').trim().to_owned();
    if text.is_empty() {
        return None;
    }
    // docx 只定义到 Heading3，更深的层级统一降级
    Some((hashes.min(3) as u8, text))
}

fn split_table_row(line: &str) -> Vec<String> {
    line.trim()
        .trim_matches('|')
        .split('|')
        .map(|cell| cell.trim().to_owned())
        .collect()
}

fn parse_markdown_image(line: &str) -> Option<(String, String)> {
    let rest = line.strip_prefix("![")?;
    let close = rest.find("](")?;
    let alt = rest[..close].to_owned();
    let after = &rest[close + 2..];
    let end = after.rfind(')')?;
    let src = after[..end]
        .trim()
        .trim_matches(|c| c == '<' || c == '>')
        .to_owned();
    if src.is_empty() {
        return None;
    }
    Some((alt, src))
}

fn parse_html_image(line: &str) -> Option<(String, String)> {
    if !line.contains("<img") {
        return None;
    }
    let src = extract_attr(line, "src")?;
    let alt = extract_attr(line, "alt").unwrap_or_default();
    Some((alt, src))
}

fn extract_attr(tag: &str, name: &str) -> Option<String> {
    let pattern = format!("{name}=\"");
    let start = tag.find(&pattern)? + pattern.len();
    let end = tag[start..].find('"')? + start;
    Some(tag[start..end].trim().to_owned())
}

fn extract_html_tag(text: &str, tag: &str) -> Option<String> {
    let open = format!("<{tag}>");
    let close = format!("</{tag}>");
    let start = text.find(&open)? + open.len();
    let end = text[start..].find(&close)? + start;
    Some(text[start..end].trim().to_owned())
}

fn italic_caption(line: &str) -> Option<String> {
    let text = line.strip_prefix('*')?.strip_suffix('*')?;
    if text.starts_with('*') || text.is_empty() {
        return None;
    }
    Some(text.trim().to_owned())
}

/// 合并软换行：两侧都是 ASCII 字母数字时补一个空格，中文直接相连
fn join_lines(lines: &[String]) -> String {
    let mut out = String::new();
    for line in lines {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        if !out.is_empty() {
            let left = out.chars().last().unwrap_or(' ');
            let right = line.chars().next().unwrap_or(' ');
            if left.is_ascii_alphanumeric() && right.is_ascii_alphanumeric() {
                out.push(' ');
            }
        }
        out.push_str(line);
    }
    out
}

// ==================== 行内格式解析 ====================

/// 解析粗体、斜体、行内代码与链接，产出连续的 InlineRun
fn parse_inline(text: &str) -> Vec<InlineRun> {
    let mut runs = Vec::new();
    let mut buffer = String::new();
    let mut rest = text;

    while !rest.is_empty() {
        // **粗体**
        if let Some(after) = rest.strip_prefix("**") {
            if let Some(end) = after.find("**") {
                flush_text(&mut buffer, &mut runs);
                runs.push(InlineRun {
                    text: after[..end].to_owned(),
                    bold: true,
                    ..Default::default()
                });
                rest = &after[end + 2..];
                continue;
            }
        }

        // `行内代码`
        if let Some(after) = rest.strip_prefix('`') {
            if let Some(end) = after.find('`') {
                flush_text(&mut buffer, &mut runs);
                runs.push(InlineRun {
                    text: after[..end].to_owned(),
                    mono: true,
                    color: Some("B91C1C"),
                    ..Default::default()
                });
                rest = &after[end + 1..];
                continue;
            }
        }

        // [文字](链接)
        if let Some(after) = rest.strip_prefix('[') {
            if let Some(close) = after.find("](") {
                if let Some(end) = after[close + 2..].find(')') {
                    let label = &after[..close];
                    let url = &after[close + 2..close + 2 + end];
                    if !label.is_empty() && !url.is_empty() {
                        flush_text(&mut buffer, &mut runs);
                        runs.push(InlineRun {
                            text: label.to_owned(),
                            underline: true,
                            color: Some("5685FF"),
                            link: Some(url.to_owned()),
                            ..Default::default()
                        });
                        rest = &after[close + 2 + end + 1..];
                        continue;
                    }
                }
            }
        }

        // *斜体*（避开 ** 与列表符号）
        if let Some(after) = rest.strip_prefix('*') {
            if !after.starts_with('*') {
                if let Some(end) = after.find('*') {
                    if end > 0 {
                        flush_text(&mut buffer, &mut runs);
                        runs.push(InlineRun {
                            text: after[..end].to_owned(),
                            italic: true,
                            ..Default::default()
                        });
                        rest = &after[end + 1..];
                        continue;
                    }
                }
            }
        }

        // 普通字符逐个累积，保证 UTF-8 边界安全
        let ch = rest.chars().next().unwrap_or(' ');
        buffer.push(ch);
        rest = &rest[ch.len_utf8()..];
    }

    flush_text(&mut buffer, &mut runs);
    if runs.is_empty() {
        runs.push(InlineRun::new(text));
    }
    runs
}

fn flush_text(buffer: &mut String, runs: &mut Vec<InlineRun>) {
    if !buffer.is_empty() {
        runs.push(InlineRun::new(std::mem::take(buffer)));
    }
}

/// 去掉行内标记，供表格单元格与列表项使用
fn plain_text(text: &str) -> String {
    parse_inline(text)
        .into_iter()
        .map(|run| run.text)
        .collect::<Vec<_>>()
        .join("")
}
