//! Word 导出
//!
//! 对应 Python 版 `codestat/exporters/word.py`：
//! 1. 标题页 + 项目路径
//! 2. 按语言汇总的统计概览表
//! 3. 代码正文（每个文件二级标题 + 语言标签 + 代码卡片）
//! 4. 页数上限：超过「前后各 60 页」时省略中间内容并给出红色提示

use std::collections::BTreeMap;
use std::path::Path;

use crate::core::{collect_code_files, CodeFile};
use crate::docx::{Align, Docx, TableStyle, TextStyle};

/// Word 文档最大页数（前后各保留这么多页）
const MAX_WORD_PAGES: usize = 60;
/// A4 + 9pt 单倍行距下每页约 37 行（与 Python 配置一致）
const LINES_PER_PAGE: usize = 37;
/// 每个文件标题、语言标签与段落间距折算的等效行数
const FILE_OVERHEAD_LINES: usize = 7;

/// Word 导出摘要，供界面状态栏提示
#[derive(Clone, Debug)]
pub struct WordSummary {
    /// 项目总行数（含空行）
    pub total_lines: usize,
    /// 实际写入文档的行数
    pub written_lines: usize,
    /// 写入的文件数
    pub files: usize,
}

/// 收集目录代码并导出为 Word 文档
///
/// 返回 `Err` 时界面直接展示错误文案；目录为空也会返回错误。
pub fn export_word(
    directory: &Path,
    output: &Path,
    extra_excludes: &[String],
) -> Result<WordSummary, String> {
    let code_files = collect_code_files(directory, extra_excludes);
    if code_files.is_empty() {
        return Err("未找到可导出的代码文件".to_owned());
    }

    let mut docx = Docx::new().with_header_footer("代码文档");

    // ==================== 标题页 ====================
    docx.heading("代码文档", 0);
    let project_path = directory
        .canonicalize()
        .unwrap_or_else(|_| directory.to_path_buf());
    docx.text(
        &format!("项目路径: {}", project_path.display()),
        &TextStyle {
            size_pt: 12.0,
            color: "4B5563",
            align: Align::Center,
            space_after: 240,
            ..Default::default()
        },
    );

    // ==================== 统计概览 ====================
    docx.heading("统计概览", 1);

    // BTreeMap 保证语言名有序，后续再按总行数排序
    let mut lang_stats: BTreeMap<&'static str, (usize, usize)> = BTreeMap::new();
    let mut total_lines = 0usize;
    for file in &code_files {
        let lines = line_count(&file.content);
        total_lines += lines;
        let entry = lang_stats.entry(file.lang.name).or_insert((0, 0));
        entry.0 += 1;
        entry.1 += lines;
    }

    let mut overview: Vec<(&str, usize, usize)> = lang_stats
        .iter()
        .map(|(name, (count, lines))| (*name, *count, *lines))
        .collect();
    overview.sort_by(|a, b| b.2.cmp(&a.2));

    let mut rows: Vec<Vec<String>> = overview
        .iter()
        .map(|(name, count, lines)| vec![(*name).to_owned(), count.to_string(), lines.to_string()])
        .collect();
    rows.push(vec![
        "总计".to_owned(),
        code_files.len().to_string(),
        total_lines.to_string(),
    ]);
    docx.table(
        &[
            "语言".to_owned(),
            "文件数".to_owned(),
            "总行数".to_owned(),
        ],
        &rows,
        &[5000, 2000, 2026],
        &TableStyle {
            header_fill: "EEF2FB",
            stripe: true,
            bold_last_row: true,
            highlight_last_row: Some("E8EEFC"),
            right_align_from: 1,
        },
    );

    docx.page_break();

    // ==================== 代码正文 ====================
    docx.heading("代码内容", 1);
    let max_lines = MAX_WORD_PAGES * LINES_PER_PAGE;
    let (head, middle, tail) = split_head_tail(&code_files, max_lines);

    let mut written_lines = 0usize;
    for part in &head {
        write_code_file(&mut docx, part);
        written_lines += part.lines;
    }

    if !middle.is_empty() {
        let omitted_files = middle.len();
        let omitted_lines: usize = middle.iter().map(|part| part.lines).sum();
        docx.text(
            &format!(
                "中间省略 {omitted_files} 个文件共 {omitted_lines} 行代码，仅保留前后各 {MAX_WORD_PAGES} 页"
            ),
            &TextStyle {
                bold: true,
                size_pt: 10.0,
                color: "DC2626",
                space_before: 160,
                space_after: 160,
                ..Default::default()
            },
        );
        docx.page_break();
    }

    for part in &tail {
        write_code_file(&mut docx, part);
        written_lines += part.lines;
    }

    docx.save(output)?;

    Ok(WordSummary {
        total_lines,
        written_lines,
        files: code_files.len(),
    })
}

/// 文档中的代码文件片段（截断后内容为 owned）
struct Part<'a> {
    file: &'a CodeFile,
    content: String,
    lines: usize,
}

/// 写入单个文件：二级标题 + 语言标签 + 代码卡片
fn write_code_file(docx: &mut Docx, part: &Part<'_>) {
    docx.heading(&part.file.rel_path, 2);
    docx.text(
        &format!("语言: {}", part.file.lang.name),
        &TextStyle {
            size_pt: 10.0,
            color: "6B7280",
            space_after: 80,
            ..Default::default()
        },
    );
    docx.code_block(&part.content, Some(part.file.lang.name));
}

/// 与 Python `content.count("\n") + 1` 保持一致（末尾换行也计入一行）
fn line_count(content: &str) -> usize {
    content.matches('\n').count() + 1
}

/// 保留前 `keep` 行
fn head_slice(content: &str, keep: usize) -> String {
    let lines: Vec<&str> = content.split('\n').collect();
    lines[..keep.min(lines.len())].join("\n")
}

/// 保留最后 `keep` 行
fn tail_slice(content: &str, keep: usize) -> String {
    let lines: Vec<&str> = content.split('\n').collect();
    let start = lines.len().saturating_sub(keep);
    lines[start..].join("\n")
}

/// 将文件列表拆分为「头部保留 / 中间省略 / 尾部保留」
///
/// 总等效行数不超过 `max_lines * 2` 时全部保留；否则前后各保留
/// `max_lines` 等效行，跨越边界的单个文件按行截断。
fn split_head_tail(
    files: &[CodeFile],
    max_lines: usize,
) -> (Vec<Part<'_>>, Vec<Part<'_>>, Vec<Part<'_>>) {
    // (文件, 等效行数, 真实代码行数)
    let entries: Vec<(&CodeFile, usize, usize)> = files
        .iter()
        .map(|file| {
            let lines = line_count(&file.content);
            (file, lines + FILE_OVERHEAD_LINES, lines)
        })
        .collect();

    let total_effective: usize = entries.iter().map(|(_, effective, _)| *effective).sum();
    if total_effective <= max_lines * 2 {
        let all = entries
            .iter()
            .map(|(file, _, lines)| Part {
                file,
                content: file.content.clone(),
                lines: *lines,
            })
            .collect();
        return (all, Vec::new(), Vec::new());
    }

    // -------------------- 头部 --------------------
    let mut head = Vec::new();
    let mut remaining = max_lines;
    for (file, effective, lines) in &entries {
        if remaining == 0 {
            break;
        }
        if *effective <= remaining {
            head.push(Part {
                file,
                content: file.content.clone(),
                lines: *lines,
            });
            remaining -= effective;
        } else {
            let keep = (*lines).min(remaining);
            head.push(Part {
                file,
                content: head_slice(&file.content, keep),
                lines: keep,
            });
            remaining = 0;
        }
    }

    // -------------------- 尾部 --------------------
    let mut tail = Vec::new();
    let mut remaining = max_lines;
    for (file, effective, lines) in entries.iter().rev() {
        if remaining == 0 {
            break;
        }
        if *effective <= remaining {
            tail.push(Part {
                file,
                content: file.content.clone(),
                lines: *lines,
            });
            remaining -= effective;
        } else {
            let keep = (*lines).min(remaining);
            tail.push(Part {
                file,
                content: tail_slice(&file.content, keep),
                lines: keep,
            });
            remaining = 0;
        }
    }
    tail.reverse();

    // -------------------- 中间省略 --------------------
    let head_count = head.len();
    let end = entries.len().saturating_sub(tail.len());
    let middle = if end > head_count {
        entries[head_count..end]
            .iter()
            .map(|(file, _, lines)| Part {
                file,
                content: file.content.clone(),
                lines: *lines,
            })
            .collect()
    } else {
        Vec::new()
    };

    (head, middle, tail)
}
