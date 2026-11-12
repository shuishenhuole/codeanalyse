//! 核心逻辑集成测试：语言识别、行数统计、目录扫描
//!
//! 运行：cargo test --test core

use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use codeanalyse::core::language::detect_language;
use codeanalyse::core::scanner::{collect_code_files, parse_excludes, scan_directory};
use codeanalyse::core::stats::count_lines_text;

fn lang(path: &str) -> &'static codeanalyse::core::LanguageConfig {
    detect_language(Path::new(path)).expect("语言应被识别")
}

#[test]
fn identifies_common_extensions() {
    assert_eq!(detect_language(Path::new("main.py")).unwrap().name, "Python");
    assert_eq!(
        detect_language(Path::new("A.TSX")).unwrap().name,
        "TypeScript"
    );
    assert_eq!(detect_language(Path::new("app.vue")).unwrap().name, "Vue");
}

#[test]
fn identifies_special_filenames() {
    assert_eq!(
        detect_language(Path::new("Dockerfile")).unwrap().name,
        "Dockerfile"
    );
    assert_eq!(
        detect_language(Path::new("CMakeLists.txt")).unwrap().name,
        "CMake"
    );
    assert_eq!(
        detect_language(Path::new("Makefile")).unwrap().name,
        "Makefile"
    );
}

#[test]
fn rejects_unknown_files() {
    assert!(detect_language(Path::new("unknown.xyz")).is_none());
    assert!(detect_language(Path::new("README")).is_none());
}

#[test]
fn counts_python_docstring_and_comments() {
    let content = "\
'''模块说明

第二行
'''
# 注释
x = 1

print(x)
";
    let stats = count_lines_text(content, lang("demo.py"));
    assert_eq!(stats.total, 8);
    assert_eq!(stats.blank, 2);
    assert_eq!(stats.comment, 4);
    assert_eq!(stats.code, 2);
}

#[test]
fn counts_single_line_and_multi_line_block_comments() {
    let content = "\
/* 一行闭合 */
let a = 1;
/*
 * 块注释
 */
let b = 2; // 行尾注释按代码行计算
";
    let stats = count_lines_text(content, lang("demo.rs"));
    assert_eq!(stats.total, 6);
    assert_eq!(stats.comment, 4);
    assert_eq!(stats.code, 2);
    assert_eq!(stats.blank, 0);
}

#[test]
fn separates_blank_and_code_lines() {
    let content = "\n\nconst a = 1;\n// x\n";
    let stats = count_lines_text(content, lang("demo.js"));
    assert_eq!(stats.total, 4);
    assert_eq!(stats.blank, 2);
    assert_eq!(stats.code, 1);
    assert_eq!(stats.comment, 1);
}

#[test]
fn parses_excludes_with_mixed_separators() {
    assert_eq!(
        parse_excludes("test, docs； dist\n*.min.js /build/"),
        vec!["test", "docs", "dist", "*.min.js", "build"]
    );
    assert!(parse_excludes("  ，； ").is_empty());
}

/// 测试用临时目录，Drop 时自动清理（路径由本测试创建）
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
fn skips_default_and_ignore_file_excluded_directories() {
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
    assert_eq!(python.files, 1, "node_modules 与 ignore_me 应被排除");
    assert_eq!(python.stats.code, 1);
}

#[test]
fn collects_code_files_with_relative_paths() {
    let temp = TempDir::new("collect");
    temp.write("a.py", "print(1)\n");
    temp.write("b.rs", "fn main() {}\n");

    let files = collect_code_files(temp.path(), &[]);
    assert_eq!(files.len(), 2);
    assert!(files
        .iter()
        .any(|f| f.rel_path == "a.py" && f.lang.name == "Python"));
    assert!(files
        .iter()
        .any(|f| f.rel_path == "b.rs" && f.lang.name == "Rust"));
}
