//! 统计核心：语言识别、行数统计与目录扫描
//!
//! 对应 Python 版 `codestat/core/`。所有用户可见文案与注释保持中文。

pub mod language;
pub mod scanner;
pub mod stats;

pub use language::{detect_language, LanguageConfig, LANGUAGES};
pub use scanner::{
    collect_code_files, parse_excludes, scan_directory, CodeFile, LangStat, DEFAULT_EXCLUDE,
    IGNORE_FILE_NAME,
};
pub use stats::{count_lines, LineStats};
