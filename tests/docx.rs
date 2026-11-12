//! docx 生成集成测试：验证包结构、XML 转义与关键部件
//!
//! 运行：cargo test --test docx

use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use codeanalyse::docx::{Docx, TableStyle, TextStyle};

fn temp_path(name: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "codestat-docx-{name}-{}-{nanos}.docx",
        std::process::id()
    ))
}

#[test]
fn writes_valid_zip_package() {
    let path = temp_path("basic");
    let mut docx = Docx::new().with_header_footer("代码文档");
    docx.heading("标题", 1);
    docx.text("正文 & <test>", &TextStyle::default());
    docx.table(
        &["语言".to_owned(), "文件数".to_owned()],
        &[vec!["Rust".to_owned(), "3".to_owned()]],
        &[6000, 3026],
        &TableStyle::default(),
    );
    docx.code_block("fn main() {\n    println!(\"hi\");\n}", Some("rust"));
    docx.save(&path).expect("写出 docx");

    let file = std::fs::File::open(&path).expect("打开 docx");
    let mut zip = zip::ZipArchive::new(file).expect("读取 zip");
    assert!(zip.by_name("[Content_Types].xml").is_ok());
    assert!(zip.by_name("word/document.xml").is_ok());
    assert!(zip.by_name("word/styles.xml").is_ok());
    assert!(zip.by_name("word/header1.xml").is_ok());
    assert!(zip.by_name("word/footer1.xml").is_ok());

    let mut document = String::new();
    std::io::Read::read_to_string(&mut zip.by_name("word/document.xml").unwrap(), &mut document)
        .unwrap();
    assert!(document.contains("正文 &amp; &lt;test&gt;"));
    assert!(document.contains("w:sectPr"));

    let _ = std::fs::remove_file(&path);
}
