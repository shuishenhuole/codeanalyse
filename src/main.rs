//! CodeStat 桌面端入口
//!
//! 使用 eframe + egui 渲染界面，业务逻辑位于 `lib.rs` 暴露的模块中，
//! 界面组件按侧边栏 / 主面板 / 对话框分层。

mod app;
mod theme;
mod ui;

use app::CodeStatApp;

fn main() -> eframe::Result {
    // 窗口图标：与 Flet 版共用同一张 assets/icon.png
    let icon = eframe::icon_data::from_png_bytes(include_bytes!("../assets/icon.png")).ok();

    let mut viewport = egui::ViewportBuilder::default()
        .with_inner_size([1160.0, 780.0])
        .with_min_inner_size([880.0, 600.0]);
    if let Some(icon) = icon {
        viewport = viewport.with_icon(icon);
    }

    let options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    eframe::run_native(
        "CodeStat - 代码量统计工具",
        options,
        Box::new(
            |cc| -> Result<Box<dyn eframe::App>, Box<dyn std::error::Error + Send + Sync>> {
                theme::setup(&cc.egui_ctx);
                Ok(Box::new(CodeStatApp::new(cc)))
            },
        ),
    )
}
