//! JSON 导出
//!
//! 输出结构与 Python 版一致：每种语言一项，最后追加 `Total` 汇总项。

use std::path::Path;

use serde_json::json;

use crate::core::LangStat;

/// 将统计结果写入 JSON 文件
///
/// 参数：
/// - `results`：扫描结果（内部会按代码行数重新降序排序，避免依赖调用方顺序）
/// - `path`：输出文件路径
///
/// 返回：写入失败时的错误描述
pub fn export_json(results: &[LangStat], path: &Path) -> Result<(), String> {
    let mut sorted: Vec<&LangStat> = results.iter().collect();
    sorted.sort_by(|a, b| b.stats.code.cmp(&a.stats.code));

    let mut data = Vec::with_capacity(sorted.len() + 1);
    let mut total_files = 0usize;
    let mut total = crate::core::LineStats::default();

    for stat in &sorted {
        data.push(json!({
            "language": stat.name,
            "files": stat.files,
            "code": stat.stats.code,
            "comment": stat.stats.comment,
            "blank": stat.stats.blank,
            "total": stat.stats.total,
        }));
        total_files += stat.files;
        total += stat.stats;
    }

    // 汇总行字段名固定为 Total，便于下游脚本识别
    data.push(json!({
        "language": "Total",
        "files": total_files,
        "code": total.code,
        "comment": total.comment,
        "blank": total.blank,
        "total": total.total,
    }));

    // serde_json 默认输出 UTF-8 中文（不转义为 \uXXXX），与 ensure_ascii=False 一致
    let text = serde_json::to_string_pretty(&data)
        .map_err(|err| format!("序列化 JSON 失败: {err}"))?;
    std::fs::write(path, text).map_err(|err| format!("写入 JSON 失败: {err}"))
}
