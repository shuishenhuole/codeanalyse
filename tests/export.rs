//! 导出功能集成测试：JSON / CSV / Word
//!
//! 运行：cargo test --test export

mod common;

use std::io::Read;

use codeanalyse::core::scanner::scan_directory;
use codeanalyse::export::{export_csv, export_json, export_word};
use common::TempDir;

/// 构造一个包含两种语言的小项目
fn sample_project(tag: &str) -> TempDir {
    let temp = TempDir::new(tag);
    temp.write(
        "src/main.py",
        "# 注释\nprint('hello')\n\nprint('world')\n",
    );
    temp.write("src/app.js", "// 注释\nconst a = 1;\n");
    temp
}

#[test]
fn exports_json_with_total_row() {
    let temp = sample_project("json");
    let results = scan_directory(temp.path(), &[]);
    let output = temp.join("stats.json");
    export_json(&results, &output).expect("导出 JSON");

    let text = std::fs::read_to_string(&output).expect("读取 JSON");
    assert!(text.contains("\"language\": \"Python\""));
    assert!(text.contains("\"language\": \"JavaScript\""));
    assert!(text.contains("\"language\": \"Total\""));
    // 中文不应被转义为 \uXXXX
    assert!(text.contains("Python"));
}

#[test]
fn exports_csv_with_header_and_total() {
    let temp = sample_project("csv");
    let results = scan_directory(temp.path(), &[]);
    let output = temp.join("stats.csv");
    export_csv(&results, &output).expect("导出 CSV");

    let text = std::fs::read_to_string(&output).expect("读取 CSV");
    let mut lines = text.lines();
    assert_eq!(
        lines.next().unwrap(),
        "Language,Files,Code,Comment,Blank,Total"
    );
    assert!(text.contains("Python,1,"));
    assert!(text.lines().last().unwrap().starts_with("Total,"));
}

#[test]
fn exports_word_document_with_zip_package() {
    let temp = sample_project("word");
    let output = temp.join("code.docx");
    let summary = export_word(temp.path(), &output, &[]).expect("导出 Word");

    assert_eq!(summary.files, 2);
    assert!(summary.total_lines > 0);
    assert!(summary.written_lines > 0);

    let file = std::fs::File::open(&output).expect("打开 docx");
    let mut zip = zip::ZipArchive::new(file).expect("读取 docx");
    assert!(zip.by_name("word/document.xml").is_ok());

    let mut document = String::new();
    zip.by_name("word/document.xml")
        .unwrap()
        .read_to_string(&mut document)
        .unwrap();
    assert!(document.contains("统计概览"));
    assert!(document.contains("代码内容"));
    // 相对路径在 Windows 下为反斜杠，这里只校验文件名
    assert!(document.contains("main.py"));
}

#[test]
fn empty_directory_returns_error() {
    let temp = TempDir::new("empty");
    let output = temp.join("empty.docx");
    let error = export_word(temp.path(), &output, &[]).expect_err("空目录应返回错误");
    assert!(error.contains("未找到"));
}
