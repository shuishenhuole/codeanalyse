//! 语言识别：扩展名 / 特殊文件名 -> 语言配置
//!
//! 对应 Python 版 `codestat/core/language.py`，语言清单保持一致。

use std::collections::HashMap;
use std::path::Path;
use std::sync::OnceLock;

/// 单种语言的识别规则与注释格式
#[derive(Clone, Copy, Debug)]
pub struct LanguageConfig {
    pub name: &'static str,
    pub extensions: &'static [&'static str],
    pub line_comments: &'static [&'static str],
    pub block_start: &'static str,
    pub block_end: &'static str,
}

impl LanguageConfig {
    pub fn has_block_comment(&self) -> bool {
        !self.block_start.is_empty() && !self.block_end.is_empty()
    }
}

macro_rules! lang {
    // 名称 + 扩展名 + 行注释 + 块注释
    ($name:literal, [$($ext:literal),+ $(,)?], [$($lc:literal),* $(,)?], $bs:literal, $be:literal) => {
        LanguageConfig {
            name: $name,
            extensions: &[$($ext),+],
            line_comments: &[$($lc),*],
            block_start: $bs,
            block_end: $be,
        }
    };
    // 名称 + 扩展名 + 行注释
    ($name:literal, [$($ext:literal),+ $(,)?], [$($lc:literal),+ $(,)?]) => {
        LanguageConfig {
            name: $name,
            extensions: &[$($ext),+],
            line_comments: &[$($lc),+],
            block_start: "",
            block_end: "",
        }
    };
    // 名称 + 扩展名（无注释）
    ($name:literal, [$($ext:literal),+ $(,)?]) => {
        LanguageConfig {
            name: $name,
            extensions: &[$($ext),+],
            line_comments: &[],
            block_start: "",
            block_end: "",
        }
    };
}

/// 支持的语言清单（40+ 种）
pub static LANGUAGES: &[LanguageConfig] = &[
    // -------------------- 主流编程语言 --------------------
    lang!("Python", [".py", ".pyw"], ["#"], "'''", "'''"),
    lang!("JavaScript", [".js", ".jsx", ".mjs", ".cjs"], ["//"], "/*", "*/"),
    lang!("TypeScript", [".ts", ".tsx"], ["//"], "/*", "*/"),
    lang!("Java", [".java"], ["//"], "/*", "*/"),
    lang!("C", [".c", ".h"], ["//"], "/*", "*/"),
    lang!("C++", [".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"], ["//"], "/*", "*/"),
    lang!("C#", [".cs"], ["//"], "/*", "*/"),
    lang!("Go", [".go"], ["//"], "/*", "*/"),
    lang!("Rust", [".rs"], ["//"], "/*", "*/"),
    lang!("Swift", [".swift"], ["//"], "/*", "*/"),
    lang!("Kotlin", [".kt", ".kts"], ["//"], "/*", "*/"),
    lang!("Scala", [".scala"], ["//"], "/*", "*/"),
    // -------------------- 脚本语言 --------------------
    lang!("Ruby", [".rb", ".rake"], ["#"]),
    lang!("PHP", [".php", ".phtml"], ["//", "#"], "/*", "*/"),
    lang!("Perl", [".pl", ".pm", ".t"], ["#"]),
    lang!("Shell", [".sh", ".bash", ".zsh"], ["#"]),
    lang!("PowerShell", [".ps1", ".psm1"], ["#"], "<#", "#>"),
    lang!("Lua", [".lua"], ["--"], "--[[", "]]"),
    lang!("R", [".r", ".R"], ["#"]),
    lang!("Dart", [".dart"], ["//"], "/*", "*/"),
    // -------------------- 函数式语言 --------------------
    lang!("Elixir", [".ex", ".exs"], ["#"]),
    lang!("Erlang", [".erl", ".hrl"], ["%"]),
    lang!("Haskell", [".hs", ".lhs"], ["--"], "{-", "-}"),
    lang!("Clojure", [".clj", ".cljs"], [";;"]),
    lang!("Lisp", [".lisp", ".lsp"], [";", "#|", "|#"]),
    // -------------------- 数据库/查询 --------------------
    lang!("SQL", [".sql"], ["--"], "/*", "*/"),
    lang!("GraphQL", [".graphql", ".gql"], ["#"]),
    // -------------------- 标记语言 --------------------
    lang!("HTML", [".html", ".htm"], [], "<!--", "-->"),
    lang!("XML", [".xml", ".svg", ".xaml"], [], "<!--", "-->"),
    lang!("CSS", [".css", ".scss", ".sass", ".less"], ["//"], "/*", "*/"),
    lang!("Markdown", [".md", ".markdown"], [], "<!--", "-->"),
    // -------------------- 前端框架 --------------------
    lang!("Vue", [".vue"], ["//", "<!--", "-->"], "/*", "*/"),
    // -------------------- 鸿蒙开发 --------------------
    lang!("Harmony", [".ets", ".har"], ["//"], "/*", "*/"),
    // -------------------- 配置/数据格式 --------------------
    lang!("JSON", [".json"]),
    lang!("YAML", [".yaml", ".yml"], ["#"]),
    lang!("TOML", [".toml"], ["#"]),
    lang!("INI", [".ini", ".cfg", ".conf"], ["#", ";"]),
    // -------------------- 构建/工具 --------------------
    lang!("Assembly", [".asm", ".s"], [";", "#", "//"]),
    lang!("Dockerfile", ["Dockerfile", ".dockerfile"], ["#"]),
    lang!("Makefile", ["Makefile", "makefile", ".mk"], ["#"]),
    lang!("CMake", ["CMakeLists.txt", ".cmake"], ["#"]),
    lang!("Protobuf", [".proto"], ["//"], "/*", "*/"),
    lang!("YARA", [".yara"], ["//"], "/*", "*/"),
];

struct LanguageIndex {
    by_extension: HashMap<&'static str, &'static LanguageConfig>,
    by_special_file: HashMap<String, &'static LanguageConfig>,
}

fn index() -> &'static LanguageIndex {
    static INDEX: OnceLock<LanguageIndex> = OnceLock::new();
    INDEX.get_or_init(|| {
        let mut by_extension = HashMap::new();
        let mut by_special_file = HashMap::new();
        for lang in LANGUAGES {
            for ext in lang.extensions {
                if ext.starts_with('.') {
                    by_extension.insert(*ext, lang);
                } else {
                    // 特殊文件名大小写不敏感（Dockerfile / Makefile / CMakeLists.txt）
                    by_special_file.insert(ext.to_lowercase(), lang);
                }
            }
        }
        LanguageIndex {
            by_extension,
            by_special_file,
        }
    })
}

/// 根据文件路径检测语言，先匹配特殊文件名，再匹配扩展名（大小写不敏感）
pub fn detect_language(path: &Path) -> Option<&'static LanguageConfig> {
    let basename = path.file_name()?.to_string_lossy().to_lowercase();
    let index = index();

    if let Some(lang) = index.by_special_file.get(basename.as_str()) {
        return Some(lang);
    }

    let ext = Path::new(&basename).extension()?.to_str()?;
    let key = format!(".{ext}");
    index.by_extension.get(key.as_str()).copied()
}
