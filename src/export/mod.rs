//! 统计结果导出
//!
//! 对应 Python 版 `codestat/exporters/`：
//! - `json`：语言明细 + Total 汇总的 JSON 数组
//! - `csv`：与 JSON 列一致的 CSV 表格
//! - `word`：概览表格 + 完整代码的 Word 文档（带页数上限）

pub mod csv;
pub mod json;
pub mod word;

pub use csv::export_csv;
pub use json::export_json;
pub use word::{export_word, WordSummary};
