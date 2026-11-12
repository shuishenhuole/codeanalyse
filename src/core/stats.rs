//! 行数统计：区分代码行、注释行与空行
//!
//! 对应 Python 版 `codestat/core/stats.py`，判定规则保持一致。

use std::path::Path;

use crate::core::language::LanguageConfig;

/// 单个文件（或多个文件累加）的行数统计
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct LineStats {
    pub total: usize,
    pub code: usize,
    pub comment: usize,
    pub blank: usize,
}

impl std::ops::AddAssign for LineStats {
    fn add_assign(&mut self, other: Self) {
        self.total += other.total;
        self.code += other.code;
        self.comment += other.comment;
        self.blank += other.blank;
    }
}

/// 统计单个文件，读取失败时返回空统计（与原实现「静默跳过」一致）
pub fn count_lines(path: &Path, lang: &LanguageConfig) -> LineStats {
    match std::fs::read(path) {
        Ok(bytes) => count_lines_text(&String::from_utf8_lossy(&bytes), lang),
        Err(_) => LineStats::default(),
    }
}

/// 统计文本内容的行数
pub fn count_lines_text(content: &str, lang: &LanguageConfig) -> LineStats {
    let mut stats = LineStats::default();
    let mut in_block_comment = false;
    let has_block_comment = lang.has_block_comment();

    for line in content.lines() {
        stats.total += 1;
        let stripped = line.trim();

        // -------------------- 空行 --------------------
        if stripped.is_empty() {
            stats.blank += 1;
            continue;
        }

        // -------------------- 块注释 --------------------
        if has_block_comment {
            if in_block_comment {
                stats.comment += 1;
                if stripped.contains(lang.block_end) {
                    in_block_comment = false;
                }
                continue;
            }

            if stripped.contains(lang.block_start) {
                stats.comment += 1;
                // 同一行内闭合（如 `/* 单行注释 */`）则不算进入块注释
                let rest = stripped.get(lang.block_start.len()..).unwrap_or("");
                if !rest.contains(lang.block_end) {
                    in_block_comment = true;
                }
                continue;
            }
        }

        // -------------------- 行注释 --------------------
        if lang
            .line_comments
            .iter()
            .any(|prefix| stripped.starts_with(prefix))
        {
            stats.comment += 1;
        } else {
            stats.code += 1;
        }
    }

    stats
}
