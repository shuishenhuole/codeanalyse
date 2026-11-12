//! Markdown 转 Word 集成测试
//!
//! 覆盖标题、段落行内格式、列表、引用、代码块、表格、水平线与 Data URI 图片。
//! 运行：cargo test --test markdown

mod common;

use std::io::Read;

use codeanalyse::markdown::convert_markdown_to_docx;
use common::TempDir;

/// 1x1 透明 PNG，用于验证 Data URI 图片处理
const PNG_1X1_BASE64: &str = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

#[test]
fn converts_common_markdown_to_docx() {
    let temp = TempDir::new("md");
    let markdown = format!(
        r#"# 项目说明

这是一段**加粗**文字，含 `行内代码` 和[链接](https://example.com)。

## 列表

- 第一项
- 第二项

1. 有序一
2. 有序二

> 引用内容

```rust
fn main() {{
    println!("你好");
}}
```

| 语言 | 行数 |
| --- | --- |
| Rust | 120 |
| Python | 80 |

---

![示意图](data:image/png;base64,{PNG_1X1_BASE64})
"#
    );
    let input = temp.join("demo.md");
    let output = temp.join("demo.docx");
    temp.write("demo.md", &markdown);

    let result = convert_markdown_to_docx(&input, &output).expect("转换 Markdown");
    assert!(result.warnings.is_empty(), "不应有图片警告: {:?}", result.warnings);
    assert!(output.exists());

    let file = std::fs::File::open(&output).expect("打开 docx");
    let mut zip = zip::ZipArchive::new(file).expect("读取 docx");
    assert!(zip.by_name("word/media/image1.png").is_ok(), "图片应写入 media 目录");

    let mut document = String::new();
    zip.by_name("word/document.xml")
        .unwrap()
        .read_to_string(&mut document)
        .unwrap();

    for expected in [
        "项目说明",
        "加粗",
        "行内代码",
        "第一项",
        "有序一",
        "引用内容",
        "fn main()",
        "Rust",
        "120",
    ] {
        assert!(document.contains(expected), "文档中应包含：{expected}");
    }
}

#[test]
fn reports_network_image_as_warning() {
    let temp = TempDir::new("md-remote");
    let input = temp.join("remote.md");
    let output = temp.join("remote.docx");
    temp.write("remote.md", "# 标题\n\n![远程图](https://example.com/a.png)\n");

    let result = convert_markdown_to_docx(&input, &output).expect("转换应成功");
    assert_eq!(result.warnings.len(), 1);
    assert!(result.warnings[0].contains("网络图片"));
}
