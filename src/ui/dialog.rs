//! Markdown 转 Word 对话框
//!
//! 对应 Python 版 `codestat/ui/md2docx_dialog.py`：选择输入/输出路径，
//! 执行转换并把结果回传给主界面。
//!
//! 转换本身是同步调用（读文件 + 生成 docx 通常很快），
//! 因此这里不引入额外线程，保持对话框状态简单可控。

use std::path::{Path, PathBuf};

use egui::{Align, Color32, CornerRadius, Layout, RichText, Stroke};

use codeanalyse::markdown::convert_markdown_to_docx;

use crate::theme;

/// Markdown 转 Word 对话框状态
pub struct MarkdownDialog {
    /// 上次选择的 Markdown 文件
    md_path: String,
    /// 输出 docx 路径
    out_path: String,
    /// 对话框内状态提示
    status: String,
    /// 状态提示是否为错误
    error: bool,
    /// 输出路径是否由输入路径自动推导
    auto_output: bool,
}

impl Default for MarkdownDialog {
    fn default() -> Self {
        Self::new()
    }
}

impl MarkdownDialog {
    pub fn new() -> Self {
        Self {
            md_path: String::new(),
            out_path: String::new(),
            status: String::new(),
            error: false,
            auto_output: true,
        }
    }

    /// 绘制对话框
    ///
    /// `open` 由主界面持有；用户关闭窗口或转换成功后会置为 false。
    /// 返回转换成功时的提示文案，供状态栏与 toast 使用。
    pub fn show(&mut self, ctx: &egui::Context, open: &mut bool) -> Option<String> {
        let mut is_open = *open;
        let mut close_requested = false;
        let mut done = None;

        egui::Window::new("Markdown 转 Word")
            .open(&mut is_open)
            .collapsible(false)
            .resizable(false)
            .default_width(540.0)
            .show(ctx, |ui| {
                ui.label(
                    RichText::new("支持标题、列表、表格、代码块、引用、链接与本地图片。")
                        .size(12.0)
                        .color(theme::SUBTEXT),
                );
                ui.add_space(12.0);

                // ==================== 输入文件 ====================
                theme::section_label(ui, "Markdown 文件");
                ui.add_space(6.0);
                let full_width = ui.available_width();
                ui.horizontal(|ui| {
                    theme::dark_input(
                        ui,
                        &mut self.md_path,
                        "选择 .md / .markdown 文件",
                        full_width - 64.0,
                    );
                    if ui
                        .add_sized([56.0, 42.0], secondary_button("选择"))
                        .clicked()
                    {
                        if let Some(path) = rfd::FileDialog::new()
                            .set_title("选择 Markdown 文件")
                            .add_filter("Markdown", &["md", "markdown"])
                            .pick_file()
                        {
                            self.md_path = path.display().to_string();
                            // 未手动指定输出时，自动推导为同名 .docx
                            if self.auto_output || self.out_path.trim().is_empty() {
                                self.out_path = path.with_extension("docx").display().to_string();
                                self.auto_output = true;
                            }
                            self.status.clear();
                            self.error = false;
                            ctx.request_repaint();
                        }
                    }
                });

                ui.add_space(12.0);

                // ==================== 输出文件 ====================
                theme::section_label(ui, "输出文件");
                ui.add_space(6.0);
                ui.horizontal(|ui| {
                    theme::dark_input(
                        ui,
                        &mut self.out_path,
                        "选择 .docx 输出路径",
                        full_width - 64.0,
                    );
                    if ui
                        .add_sized([56.0, 42.0], secondary_button("选择"))
                        .clicked()
                    {
                        let mut dialog = rfd::FileDialog::new()
                            .set_title("保存 Word 文件")
                            .add_filter("Word 文档", &["docx"]);
                        if !self.md_path.trim().is_empty() {
                            let md = Path::new(self.md_path.trim());
                            if let Some(parent) = md.parent() {
                                dialog = dialog.set_directory(parent);
                            }
                            if let Some(stem) = md.file_stem().and_then(|s| s.to_str()) {
                                dialog = dialog.set_file_name(format!("{stem}.docx"));
                            }
                        }
                        if let Some(path) = dialog.save_file() {
                            self.out_path = path.display().to_string();
                            self.auto_output = false;
                            self.status.clear();
                            self.error = false;
                            ctx.request_repaint();
                        }
                    }
                });

                ui.add_space(10.0);
                if !self.status.is_empty() {
                    ui.label(
                        RichText::new(&self.status)
                            .size(12.0)
                            .color(if self.error {
                                theme::ERROR
                            } else {
                                theme::MUTED
                            }),
                    );
                }

                // ==================== 操作按钮 ====================
                ui.add_space(14.0);
                ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
                    if ui
                        .add_sized([104.0, 36.0], primary_button("开始转换"))
                        .clicked()
                    {
                        match self.convert() {
                            Ok(message) => {
                                self.status = message.clone();
                                self.error = false;
                                done = Some(message);
                                close_requested = true;
                            }
                            Err(message) => {
                                self.status = message;
                                self.error = true;
                            }
                        }
                    }
                    if ui
                        .add_sized([72.0, 36.0], secondary_button("取消"))
                        .clicked()
                    {
                        close_requested = true;
                    }
                });
            });

        if !is_open {
            close_requested = true;
        }
        if close_requested {
            *open = false;
        }
        done
    }

    /// 执行转换并按结果更新内部状态
    fn convert(&mut self) -> Result<String, String> {
        let markdown = self.md_path.trim().to_owned();
        if markdown.is_empty() {
            return Err("请先选择 Markdown 文件".to_owned());
        }

        let md_path = PathBuf::from(&markdown);
        if !md_path.is_file() {
            return Err("Markdown 文件不存在，请重新选择".to_owned());
        }

        let mut out_path = if self.out_path.trim().is_empty() {
            md_path.with_extension("docx")
        } else {
            PathBuf::from(self.out_path.trim())
        };
        if out_path
            .extension()
            .and_then(|ext| ext.to_str())
            .map(|ext| ext.eq_ignore_ascii_case("docx"))
            != Some(true)
        {
            out_path.set_extension("docx");
        }
        self.out_path = out_path.display().to_string();

        let result = convert_markdown_to_docx(&md_path, &out_path)
            .map_err(|err| format!("转换失败: {err}"))?;

        let mut message = format!("已转换 Markdown: {}", result.output.display());
        if !result.warnings.is_empty() {
            message.push_str(&format!(
                "（{} 张图片未插入，文档内已保留占位提示）",
                result.warnings.len()
            ));
        }
        Ok(message)
    }
}

/// 次操作按钮：透明底 + 描边
fn secondary_button(text: &str) -> egui::Button<'static> {
    egui::Button::new(
        RichText::new(text)
            .size(12.0)
            .color(theme::BTN_SECONDARY_TEXT),
    )
    .fill(Color32::TRANSPARENT)
    .stroke(Stroke::new(1.0, theme::DIVIDER))
    .corner_radius(CornerRadius::same(8))
}

/// 主操作按钮：品牌蓝填充
fn primary_button(text: &str) -> egui::Button<'static> {
    egui::Button::new(RichText::new(text).size(12.0).color(Color32::WHITE))
        .fill(theme::PRIMARY)
        .stroke(Stroke::NONE)
        .corner_radius(CornerRadius::same(8))
}
