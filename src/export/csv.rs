//! CSV 导出
//!
//! 表头与 Python 版保持一致：`Language,Files,Code,Comment,Blank,Total`。

use std::path::Path;

use crate::core::LangStat;

/// 将统计结果写入 CSV 文件（UTF-8 编码）
///
/// 每行一种语言，最后一行为 `Total` 汇总。字段按需加引号，
/// 避免语言名中出现逗号或引号时破坏列结构。
pub fn export_csv(results: &[LangStat], path: &Path) -> Result<(), String> {
    let mut sorted: Vec<&LangStat> = results.iter().collect();
    sorted.sort_by(|a, b| b.stats.code.cmp(&a.stats.code));

    let mut output = String::from("Language,Files,Code,Comment,Blank,Total\n");
    let mut total_files = 0usize;
    let mut total = crate::core::LineStats::default();

    for stat in &sorted {
        output.push_str(&format!(
            "{},{},{},{},{},{}\n",
            csv_field(&stat.name),
            stat.files,
            stat.stats.code,
            stat.stats.comment,
            stat.stats.blank,
            stat.stats.total
        ));
        total_files += stat.files;
        total += stat.stats;
    }

    output.push_str(&format!(
        "Total,{},{},{},{},{}\n",
        total_files, total.code, total.comment, total.blank, total.total
    ));

    std::fs::write(path, output).map_err(|err| format!("写入 CSV 失败: {err}"))
}

/// 按 RFC 4180 对字段做最小转义
fn csv_field(value: &str) -> String {
    if value.contains(',') || value.contains('"') || value.contains('\n') {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_owned()
    }
}
