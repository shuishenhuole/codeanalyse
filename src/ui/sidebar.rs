//! 左侧操作面板
//!
//! 对应 Python 版 `codestat/ui/sidebar.py`：品牌区、目录输入、排除规则、
//! 开始统计按钮、Markdown 转 Word 工具入口与底部状态栏。
//! 只负责绘制与收集用户意图，具体业务动作由 `app` 模块执行。

use std::path::Path;

use egui::{Align, Color32, CornerRadius, Layout, RichText, Stroke, TextureHandle};

use crate::theme;

/// 侧边栏产生的用户动作
#[derive(Default)]
pub struct SidebarAction {
    /// 点击「浏览」选择目录
    pub browse: bool,
    /// 点击「开始统计」
    pub scan: bool,
    /// 点击「Markdown 转 Word」
    pub open_markdown: bool,
}

/// 侧边栏渲染所需的只读数据与可编辑输入
pub struct SidebarState<'a> {
    pub dir: &'a mut String,
    pub exclude: &'a mut String,
    pub scanning: bool,
    pub status: &'a str,
    pub logo: Option<&'a TextureHandle>,
}

/// 绘制侧边栏并返回用户动作
pub fn show(ui: &mut egui::Ui, state: &mut SidebarState<'_>) -> SidebarAction {
    let mut action = SidebarAction::default();

    brand(ui, state.logo);
    ui.add_space(20.0);

    // ==================== 统计目录 ====================
    theme::section_label(ui, "统计目录");
    ui.add_space(6.0);
    let full_width = ui.available_width();
    ui.horizontal(|ui| {
        let browse_width = 56.0;
        let input_width = full_width - browse_width - 8.0;
        theme::dark_input(ui, state.dir, "选择要统计的目录", input_width);

        let browse = egui::Button::new(
            RichText::new("浏览")
                .size(12.0)
                .color(theme::BTN_SECONDARY_TEXT),
        )
        .fill(Color32::from_rgb(0x1F, 0x24, 0x2F))
        .stroke(Stroke::new(1.0, theme::DIVIDER))
        .corner_radius(CornerRadius::same(8));
        if ui.add_sized([browse_width, 42.0], browse).clicked() {
            action.browse = true;
        }
    });

    ui.add_space(14.0);

    // ==================== 排除规则 ====================
    theme::section_label(ui, "排除规则");
    ui.add_space(6.0);
    theme::    dark_input(ui, state.exclude, "目录名/文件名/后缀", full_width);
    ui.add_space(6.0);
    // 侧栏较窄，示例拆成两行避免截断
    ui.label(
        RichText::new("示例: test docs dist *.min.js")
            .size(11.0)
            .color(theme::MUTED),
    );
    ui.label(
        RichText::new("空格或逗号分隔")
            .size(11.0)
            .color(theme::MUTED),
    );

    ui.add_space(16.0);

    // ==================== 开始统计 ====================
    // 与原版一致：扫描期间不禁用点击，只用亮度提示，点击时给出 toast
    let dir_valid = Path::new(state.dir.trim()).is_dir();
    let active = !state.scanning && dir_valid;
    let fill = if active {
        theme::PRIMARY
    } else {
        theme::tint(theme::PRIMARY, 110)
    };
    let scan = egui::Button::new(
        RichText::new(if state.scanning {
            "正在统计..."
        } else {
            "▶  开始统计"
        })
        .size(14.0)
        .color(Color32::WHITE),
    )
    .fill(fill)
    .stroke(Stroke::NONE)
    .corner_radius(CornerRadius::same(8));
    if ui.add_sized([full_width, 42.0], scan).clicked() {
        action.scan = true;
    }

    ui.add_space(18.0);

    // ==================== 工具 ====================
    theme::section_label(ui, "工具");
    ui.add_space(6.0);
    let md_button = egui::Button::new(
        RichText::new("Markdown 转 Word")
            .size(13.0)
            .color(theme::BTN_SECONDARY_TEXT),
    )
    .fill(Color32::TRANSPARENT)
    .stroke(Stroke::new(1.0, theme::DIVIDER))
    .corner_radius(CornerRadius::same(8));
    if ui.add_sized([full_width, 40.0], md_button).clicked() {
        action.open_markdown = true;
    }

    // ==================== 底部状态栏 ====================
    ui.with_layout(Layout::bottom_up(Align::LEFT), |ui| {
        ui.add_space(4.0);
        ui.label(
            RichText::new("支持 40+ 种编程语言")
                .size(11.0)
                .color(theme::MUTED),
        );
        ui.add_space(8.0);
        ui.horizontal(|ui| {
            if state.scanning {
                ui.add(egui::Spinner::new().size(14.0));
            }
            ui.label(
                RichText::new(state.status)
                    .size(12.0)
                    .color(theme::SUBTEXT),
            );
        });
        ui.add_space(10.0);
        // 顶部分隔线
        let width = ui.available_width();
        let (rect, _) = ui.allocate_exact_size(egui::vec2(width, 1.0), egui::Sense::hover());
        ui.painter()
            .rect_filled(rect, CornerRadius::ZERO, theme::DIVIDER);
    });

    action
}

/// 品牌区：应用图标 + 名称 + 副标题
fn brand(ui: &mut egui::Ui, logo: Option<&TextureHandle>) {    ui.horizontal(|ui| {
        match logo {
            Some(texture) => {
                ui.add(
                    egui::Image::new(texture)
                        .fit_to_exact_size(egui::vec2(34.0, 34.0))
                        .corner_radius(CornerRadius::same(8)),
                );
            }
            None => {
                // 未加载到图标时用主色方块兜底
                let (rect, _) =
                    ui.allocate_exact_size(egui::vec2(34.0, 34.0), egui::Sense::hover());
                ui.painter()
                    .rect_filled(rect, CornerRadius::same(8), theme::PRIMARY);
            }
        }
        ui.add_space(4.0);
        ui.vertical(|ui| {
            ui.label(RichText::new("CodeStat").size(17.0).strong().color(theme::TEXT));
            ui.label(
                RichText::new("代码规模分析工具")
                    .size(11.5)
                    .color(theme::SUBTEXT),
            );
        });
    });
}
