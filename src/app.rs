//! 应用状态与事件绑定
//!
//! 对应 Python 版 `codestat/app.py`：
//! - 持有界面状态（目录/排除项/统计结果/状态文案）
//! - 通过后台线程执行扫描，主线程只轮询结果，避免界面卡顿
//! - 把侧边栏、主面板、对话框的「动作」转成具体业务调用

use std::path::Path;
use std::sync::mpsc::{self, Receiver};
use std::time::{Duration, Instant};

use crate::theme;
use crate::ui::dialog::MarkdownDialog;
use crate::ui::main_panel::{self, ExportKind};
use crate::ui::sidebar::{self, SidebarState};
use codeanalyse::core::{parse_excludes, scan_directory, LangStat};
use codeanalyse::export::{export_csv, export_json, export_word};

/// 轻提示展示时长
const TOAST_DURATION_MS: u64 = 2_600;

struct Toast {
    message: String,
    created: Instant,
}

/// CodeStat 主应用
pub struct CodeStatApp {
    /// 统计目录输入
    dir_input: String,
    /// 排除规则输入
    exclude_input: String,
    /// 最近一次统计结果
    results: Vec<LangStat>,
    /// 是否有后台扫描在运行
    scanning: bool,
    /// 侧边栏状态文案
    status: String,
    /// 空状态提示文案
    hint: String,
    /// 后台扫描结果通道
    scan_rx: Option<Receiver<Vec<LangStat>>>,
    /// 轻提示
    toast: Option<Toast>,
    /// Markdown 转 Word 对话框（None 表示未打开）
    dialog: Option<MarkdownDialog>,
    /// 应用图标纹理
    logo: Option<egui::TextureHandle>,
}

impl CodeStatApp {
    /// 创建应用：默认统计目录为当前工作目录
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        let cwd = std::env::current_dir()
            .map(|path| path.display().to_string())
            .unwrap_or_default();
        Self {
            dir_input: cwd,
            exclude_input: String::new(),
            results: Vec::new(),
            scanning: false,
            status: "就绪".to_owned(),
            hint: "选择一个项目目录，开始分析代码规模".to_owned(),
            scan_rx: None,
            toast: None,
            dialog: None,
            logo: theme::load_logo(&cc.egui_ctx),
        }
    }

    /// 打开系统目录选择框
    fn browse_directory(&mut self, ctx: &egui::Context) {
        if self.scanning {
            self.show_toast("正在统计中，请稍候...");
            return;
        }

        let current = self.dir_input.trim().to_owned();
        let initial = if Path::new(&current).is_dir() {
            current
        } else {
            std::env::current_dir()
                .map(|path| path.display().to_string())
                .unwrap_or_default()
        };

        if let Some(path) = rfd::FileDialog::new()
            .set_title("选择统计目录")
            .set_directory(initial)
            .pick_folder()
        {
            self.dir_input = path.display().to_string();
            self.status = "就绪".to_owned();
        }
        ctx.request_repaint();
    }

    /// 启动后台扫描线程
    fn start_scan(&mut self, ctx: &egui::Context) {
        if self.scanning {
            self.show_toast("正在统计中，请稍候...");
            return;
        }

        let directory = self.dir_input.trim().to_owned();
        if !Path::new(&directory).is_dir() {
            self.hint = "请选择有效的统计目录".to_owned();
            self.status = "目录无效".to_owned();
            self.show_toast("请选择有效的统计目录");
            return;
        }

        let excludes = parse_excludes(&self.exclude_input);
        self.scanning = true;
        self.results.clear();
        self.hint = "正在统计，请稍候...".to_owned();
        self.status = "正在统计，请稍候...".to_owned();

        let (tx, rx) = mpsc::channel();
        self.scan_rx = Some(rx);
        let ctx = ctx.clone();
        std::thread::spawn(move || {
            // scan_directory 内部已静默跳过不可读文件，不会 panic
            let results = scan_directory(Path::new(&directory), &excludes);
            let _ = tx.send(results);
            // 唤醒主线程轮询结果
            ctx.request_repaint();
        });
    }

    /// 轮询后台扫描结果并更新状态
    fn poll_scan(&mut self) {
        let message = self.scan_rx.as_ref().map(|rx| rx.try_recv());
        match message {
            Some(Ok(results)) => {
                self.scan_rx = None;
                self.scanning = false;
                self.results = results;

                if self.results.is_empty() {
                    self.status = "未找到可统计的代码文件".to_owned();
                    self.hint = "未找到可统计的代码文件".to_owned();
                } else {
                    let files: usize = self.results.iter().map(|item| item.files).sum();
                    let lines: usize = self.results.iter().map(|item| item.stats.total).sum();
                    self.status = format!(
                        "统计完成: 共 {} 个文件, {} 行",
                        main_panel::format_number(files),
                        main_panel::format_number(lines)
                    );
                }
            }
            Some(Err(std::sync::mpsc::TryRecvError::Disconnected)) => {
                // 线程异常退出：恢复界面并提示失败
                self.scan_rx = None;
                self.scanning = false;
                self.status = "统计失败".to_owned();
                self.hint = "统计失败".to_owned();
                self.show_toast("统计失败");
            }
            _ => {}
        }
    }

    /// 导出当前结果（JSON / CSV / Word）
    fn export(&mut self, kind: ExportKind) {
        if self.scanning {
            self.show_toast("正在统计中，请稍候...");
            return;
        }
        if self.results.is_empty() {
            self.status = "请先执行统计".to_owned();
            self.show_toast("请先执行统计，再导出结果");
            return;
        }

        let directory = self.dir_input.trim().to_owned();
        if kind == ExportKind::Word && !Path::new(&directory).is_dir() {
            self.status = "统计目录无效，无法导出 Word".to_owned();
            self.show_toast("统计目录无效，无法导出 Word");
            return;
        }

        let (file_name, filter_name, extension) = match kind {
            ExportKind::Json => ("codestat.json", "JSON", "json"),
            ExportKind::Csv => ("codestat.csv", "CSV", "csv"),
            ExportKind::Word => ("codestat.docx", "Word 文档", "docx"),
        };

        let Some(path) = rfd::FileDialog::new()
            .set_title("保存导出文件")
            .set_file_name(file_name)
            .add_filter(filter_name, &[extension])
            .save_file()
        else {
            return;
        };

        let result = match kind {
            ExportKind::Json => export_json(&self.results, &path),
            ExportKind::Csv => export_csv(&self.results, &path),
            ExportKind::Word => {
                let excludes = parse_excludes(&self.exclude_input);
                export_word(Path::new(&directory), &path, &excludes).map(|_| ())
            }
        };

        match result {
            Ok(()) => {
                let name = path
                    .file_name()
                    .and_then(|name| name.to_str())
                    .unwrap_or("导出文件");
                self.status = format!("已导出到 {name}");
                self.show_toast(format!("已导出到 {}", path.display()));
            }
            Err(error) => {
                self.status = format!("导出失败: {error}");
                self.show_toast("导出失败，请检查文件占用情况");
            }
        }
    }

    fn set_status(&mut self, text: impl Into<String>) {
        self.status = text.into();
    }

    fn show_toast(&mut self, message: impl Into<String>) {
        self.toast = Some(Toast {
            message: message.into(),
            created: Instant::now(),
        });
    }

    /// 底部居中轻提示
    fn draw_toast(&self, ctx: &egui::Context) {
        let Some(toast) = &self.toast else {
            return;
        };
        egui::Area::new(egui::Id::new("codestat-toast"))
            .anchor(egui::Align2::CENTER_BOTTOM, egui::vec2(0.0, -24.0))
            .show(ctx, |ui| {
                egui::Frame::new()
                    .fill(egui::Color32::from_rgb(0xE5, 0xEA, 0xF3))
                    .corner_radius(egui::CornerRadius::same(8))
                    .inner_margin(egui::Margin {
                        left: 16,
                        right: 16,
                        top: 10,
                        bottom: 10,
                    })
                    .show(ui, |ui| {
                        ui.label(
                            egui::RichText::new(&toast.message)
                                .size(13.0)
                                .color(egui::Color32::from_rgb(0x11, 0x13, 0x18)),
                        );
                    });
            });
    }
}

impl eframe::App for CodeStatApp {
    /// 每帧的纯逻辑阶段：轮询后台结果、处理 toast 过期
    fn logic(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.poll_scan();

        if self.scanning {
            ctx.request_repaint_after(Duration::from_millis(100));
        }
        if let Some(toast) = &self.toast {
            if toast.created.elapsed() > Duration::from_millis(TOAST_DURATION_MS) {
                self.toast = None;
            } else {
                ctx.request_repaint_after(Duration::from_millis(100));
            }
        }
    }

    /// 绘制整个窗口
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();

        // ==================== 侧边栏 ====================
        let mut browse = false;
        let mut scan = false;
        let mut open_markdown = false;
        egui::Panel::left("codestat-sidebar")
            .exact_size(280.0)
            .resizable(false)
            .frame(
                egui::Frame::new()
                    .fill(theme::PANEL_BG)
                    .inner_margin(egui::Margin {
                        left: 20,
                        right: 20,
                        top: 22,
                        bottom: 14,
                    }),
            )
            .show(ui, |ui| {
                let action = sidebar::show(
                    ui,
                    &mut SidebarState {
                        dir: &mut self.dir_input,
                        exclude: &mut self.exclude_input,
                        scanning: self.scanning,
                        status: &self.status,
                        logo: self.logo.as_ref(),
                    },
                );
                browse = action.browse;
                scan = action.scan;
                open_markdown = action.open_markdown;
            });

        if browse {
            self.browse_directory(&ctx);
        }
        if scan {
            self.start_scan(&ctx);
        }
        if open_markdown {
            self.dialog = Some(MarkdownDialog::new());
        }

        // ==================== 主内容区 ====================
        let mut export_kind = None;
        egui::CentralPanel::default()
            .frame(
                egui::Frame::new().fill(theme::BG).inner_margin(egui::Margin {
                    left: 24,
                    right: 24,
                    top: 20,
                    bottom: 16,
                }),
            )
            .show(ui, |ui| {
                let action = main_panel::show(
                    ui,
                    &main_panel::MainPanelState {
                        results: &self.results,
                        scanning: self.scanning,
                        hint: &self.hint,
                    },
                );
                export_kind = action.export;
            });

        if let Some(kind) = export_kind {
            self.export(kind);
        }

        // ==================== Markdown 转 Word 对话框 ====================
        let mut dialog_open = true;
        let done = if let Some(dialog) = self.dialog.as_mut() {
            dialog.show(&ctx, &mut dialog_open)
        } else {
            None
        };
        if let Some(message) = done {
            self.set_status(message.clone());
            self.show_toast(message);
        }
        if !dialog_open {
            self.dialog = None;
        }

        self.draw_toast(&ctx);
    }
}
