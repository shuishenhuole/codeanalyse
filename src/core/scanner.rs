//! 目录扫描与排除规则
//!
//! 对应 Python 版 `codestat/core/scanner.py`：默认排除 + `.codestatignore` + 界面输入，
//! 三者取并集后递归遍历目录。

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

use crate::core::language::{detect_language, LanguageConfig};
use crate::core::stats::{count_lines, LineStats};

/// 默认排除的目录（版本控制、依赖、IDE、编译产物等）
pub const DEFAULT_EXCLUDE: &[&str] = &[
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "venv",
    "env",
    ".env",
    ".venv",
    ".tox",
    ".eggs",
    ".idea",
    ".vscode",
    ".vs",
    "dist",
    "build",
    "out",
    "target",
    ".gradle",
    ".maven",
    "vendor",
    "Pods",
    "coverage",
    ".nyc_output",
];

pub const IGNORE_FILE_NAME: &str = ".codestatignore";

/// 按语言聚合的统计结果
#[derive(Clone, Debug)]
pub struct LangStat {
    pub name: String,
    pub files: usize,
    pub stats: LineStats,
}

/// 收集到的代码文件（Word 导出用）
#[derive(Clone, Debug)]
pub struct CodeFile {
    pub rel_path: String,
    pub content: String,
    pub lang: &'static LanguageConfig,
}

/// 排除规则集合
#[derive(Debug)]
pub struct Excludes {
    names: HashSet<String>,
    lower: HashSet<String>,
}

impl Excludes {
    pub fn load(directory: &Path, extra: &[String]) -> Self {
        let mut names: HashSet<String> = DEFAULT_EXCLUDE.iter().map(|s| (*s).to_owned()).collect();
        names.extend(read_ignore_file(directory));
        names.extend(extra.iter().filter(|s| !s.is_empty()).cloned());
        let lower = names.iter().map(|s| s.to_lowercase()).collect();
        Self { names, lower }
    }

    fn is_dir_excluded(&self, name: &str) -> bool {
        self.names.contains(name)
    }

    fn is_file_excluded(&self, filename: &str) -> bool {
        if self.names.contains(filename) {
            return true;
        }
        let Some(ext) = Path::new(filename).extension().and_then(|e| e.to_str()) else {
            return false;
        };
        let ext = ext.to_lowercase();
        self.lower.contains(&ext) || self.lower.contains(&format!(".{ext}"))
    }
}

/// 读取 `.codestatignore`（每行一个排除项，# 开头为注释）
fn read_ignore_file(directory: &Path) -> HashSet<String> {
    let mut excludes = HashSet::new();
    let Ok(content) = std::fs::read_to_string(directory.join(IGNORE_FILE_NAME)) else {
        return excludes;
    };
    for line in content.lines() {
        let line = line.trim();
        if !line.is_empty() && !line.starts_with('#') {
            excludes.insert(line.to_owned());
        }
    }
    excludes
}

/// 解析界面输入的排除项，支持空格 / 英文逗号 / 中文逗号 / 分号分隔
pub fn parse_excludes(input: &str) -> Vec<String> {
    input
        .split(|c: char| matches!(c, ',' | '，' | ';' | '；') || c.is_whitespace())
        .map(|token| token.trim().trim_matches(|c| c == '/' || c == '\\'))
        .filter(|token| !token.is_empty())
        .map(str::to_owned)
        .collect()
}

fn collect_files(root: &Path, excludes: &Excludes) -> Vec<PathBuf> {
    let mut files = Vec::new();
    walk(root, excludes, &mut files);
    files
}

fn walk(dir: &Path, excludes: &Excludes, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let Ok(file_type) = entry.file_type() else {
            continue;
        };
        let name = entry.file_name().to_string_lossy().to_string();
        let path = entry.path();

        if file_type.is_dir() {
            if !excludes.is_dir_excluded(&name) {
                walk(&path, excludes, out);
            }
        } else if file_type.is_file() && !excludes.is_file_excluded(&name) {
            out.push(path);
        }
    }
}

/// 扫描目录并统计各语言代码量（按代码行数降序）
pub fn scan_directory(directory: &Path, extra_excludes: &[String]) -> Vec<LangStat> {
    let excludes = Excludes::load(directory, extra_excludes);
    let mut results: HashMap<&'static str, LangStat> = HashMap::new();

    for file in collect_files(directory, &excludes) {
        let Some(lang) = detect_language(&file) else {
            continue;
        };
        let file_stats = count_lines(&file, lang);
        let entry = results.entry(lang.name).or_insert_with(|| LangStat {
            name: lang.name.to_owned(),
            files: 0,
            stats: LineStats::default(),
        });
        entry.files += 1;
        entry.stats += file_stats;
    }

    let mut list: Vec<LangStat> = results.into_values().collect();
    list.sort_by(|a, b| {
        b.stats
            .code
            .cmp(&a.stats.code)
            .then_with(|| a.name.cmp(&b.name))
    });
    list
}

/// 收集代码文件内容（Word 导出用），按语言名与相对路径排序
pub fn collect_code_files(directory: &Path, extra_excludes: &[String]) -> Vec<CodeFile> {
    let excludes = Excludes::load(directory, extra_excludes);
    let mut files = Vec::new();

    for path in collect_files(directory, &excludes) {
        let Some(lang) = detect_language(&path) else {
            continue;
        };
        let Ok(bytes) = std::fs::read(&path) else {
            continue;
        };
        let rel_path = path
            .strip_prefix(directory)
            .unwrap_or(&path)
            .to_string_lossy()
            .to_string();
        files.push(CodeFile {
            rel_path,
            content: String::from_utf8_lossy(&bytes).into_owned(),
            lang,
        });
    }

    files.sort_by(|a, b| {
        a.lang
            .name
            .cmp(b.lang.name)
            .then_with(|| a.rel_path.cmp(&b.rel_path))
    });
    files
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TempDir(PathBuf);

    impl TempDir {
        fn new(tag: &str) -> Self {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            let path = std::env::temp_dir().join(format!(
                "codestat-test-{tag}-{}-{nanos}",
                std::process::id()
            ));
            std::fs::create_dir_all(&path).expect("创建临时目录");
            Self(path)
        }

        fn path(&self) -> &Path {
            &self.0
        }

        fn write(&self, rel: &str, content: &str) {
            let path = self.0.join(rel);
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).expect("创建子目录");
            }
            std::fs::write(path, content).expect("写入测试文件");
        }
    }

    impl Drop for TempDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }

    #[test]
    fn parses_excludes_with_mixed_separators() {
        assert_eq!(
            parse_excludes("test, docs； dist\n*.min.js /build/"),
            vec!["test", "docs", "dist", "*.min.js", "build"]
        );
        assert!(parse_excludes("  ，； ").is_empty());
    }

    #[test]
    fn skips_default_and_user_excluded_directories() {
        let temp = TempDir::new("scan");
        temp.write("src/main.py", "print(1)\n");
        temp.write("src/app.js", "const a = 1;\n");
        temp.write("node_modules/pkg/index.js", "const b = 2;\n");
        temp.write("docs/guide.md", "# 标题\n");
        temp.write(".codestatignore", "# 注释\nignore_me\n");
        temp.write("ignore_me/skip.py", "print(3)\n");

        let results = scan_directory(temp.path(), &[]);
        let names: Vec<&str> = results.iter().map(|r| r.name.as_str()).collect();
        assert!(names.contains(&"Python"));
        assert!(names.contains(&"JavaScript"));

        let python = results.iter().find(|r| r.name == "Python").unwrap();
        assert_eq!(python.files, 1, "docs/ignore_me 中的 Python 文件应被排除");
        assert_eq!(python.stats.code, 1);
    }

    #[test]
    fn collects_code_files_with_relative_paths() {
        let temp = TempDir::new("collect");
        temp.write("a.py", "print(1)\n");
        temp.write("b.rs", "fn main() {}\n");

        let files = collect_code_files(temp.path(), &[]);
        assert_eq!(files.len(), 2);
        assert!(files.iter().any(|f| f.rel_path == "a.py" && f.lang.name == "Python"));
        assert!(files.iter().any(|f| f.rel_path == "b.rs" && f.lang.name == "Rust"));
    }
}
