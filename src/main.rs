mod theme;

fn main() -> eframe::Result {
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
                Ok(Box::new(PlaceholderApp))
            },
        ),
    )
}

struct PlaceholderApp;

impl eframe::App for PlaceholderApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("CodeStat - 代码量统计工具");
        });
    }
}
