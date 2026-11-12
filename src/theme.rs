//! 界面主题：配色、字体与通用控件样式
//!
//! 对应 Python/Flet 版 `codestat/ui/theme.py`，颜色值保持一致。

use std::sync::Arc;

use egui::{Color32, CornerRadius, FontData, FontDefinitions, FontFamily, Stroke, Visuals};

pub const BG: Color32 = Color32::from_rgb(0x11, 0x13, 0x18);
pub const PANEL_BG: Color32 = Color32::from_rgb(0x17, 0x1A, 0x21);
pub const CARD_BG: Color32 = Color32::from_rgb(0x1B, 0x20, 0x2A);
pub const DIVIDER: Color32 = Color32::from_rgb(0x2A, 0x30, 0x3D);
pub const THIN_BORDER: Color32 = Color32::from_rgb(0x23, 0x2A, 0x36);
pub const TEXT: Color32 = Color32::from_rgb(0xF3, 0xF4, 0xF6);
pub const VALUE: Color32 = Color32::from_rgb(0xF7, 0xF9, 0xFC);
pub const SUBTEXT: Color32 = Color32::from_rgb(0x9C, 0xA3, 0xAF);
pub const MUTED: Color32 = Color32::from_rgb(0x6B, 0x72, 0x80);
pub const PRIMARY: Color32 = Color32::from_rgb(0x56, 0x85, 0xFF);
pub const PRIMARY_HOVER: Color32 = Color32::from_rgb(0x6E, 0x97, 0xFF);
pub const ICON: Color32 = Color32::from_rgb(0x8F, 0xB0, 0xFF);
pub const BTN_SECONDARY_TEXT: Color32 = Color32::from_rgb(0xD1, 0xD5, 0xDB);
pub const ERROR: Color32 = Color32::from_rgb(0xF8, 0x71, 0x71);

/// 主色调透明叠加（egui 的 Color32 用非预乘 alpha）
pub fn tint(color: Color32, alpha: u8) -> Color32 {
    Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), alpha)
}

pub fn visuals() -> Visuals {
    let mut v = Visuals::dark();
    v.override_text_color = Some(TEXT);
    v.weak_text_color = Some(SUBTEXT);
    v.panel_fill = BG;
    v.window_fill = PANEL_BG;
    v.extreme_bg_color = BG;
    v.text_edit_bg_color = Some(BG);
    v.faint_bg_color = CARD_BG;
    v.hyperlink_color = PRIMARY;
    v.selection.bg_fill = tint(PRIMARY, 90);
    v.selection.stroke = Stroke::new(1.0, PRIMARY);

    v.widgets.noninteractive.bg_fill = CARD_BG;
    v.widgets.noninteractive.weak_bg_fill = CARD_BG;
    v.widgets.noninteractive.bg_stroke = Stroke::new(1.0, THIN_BORDER);
    v.widgets.noninteractive.fg_stroke = Stroke::new(1.0, SUBTEXT);
    v.widgets.noninteractive.corner_radius = CornerRadius::same(8);

    v.widgets.inactive.bg_fill = Color32::from_rgb(0x22, 0x27, 0x32);
    v.widgets.inactive.weak_bg_fill = Color32::from_rgb(0x1F, 0x24, 0x2F);
    v.widgets.inactive.bg_stroke = Stroke::new(1.0, DIVIDER);
    v.widgets.inactive.fg_stroke = Stroke::new(1.0, BTN_SECONDARY_TEXT);
    v.widgets.inactive.corner_radius = CornerRadius::same(8);

    v.widgets.hovered.bg_fill = Color32::from_rgb(0x29, 0x30, 0x3E);
    v.widgets.hovered.weak_bg_fill = Color32::from_rgb(0x29, 0x30, 0x3E);
    v.widgets.hovered.bg_stroke = Stroke::new(1.0, PRIMARY);
    v.widgets.hovered.fg_stroke = Stroke::new(1.0, TEXT);
    v.widgets.hovered.corner_radius = CornerRadius::same(8);

    v.widgets.active.bg_fill = Color32::from_rgb(0x30, 0x39, 0x4C);
    v.widgets.active.weak_bg_fill = Color32::from_rgb(0x30, 0x39, 0x4C);
    v.widgets.active.bg_stroke = Stroke::new(1.0, PRIMARY);
    v.widgets.active.fg_stroke = Stroke::new(1.0, TEXT);
    v.widgets.active.corner_radius = CornerRadius::same(8);
    v
}

/// 初始化主题与中文字体
pub fn setup(ctx: &egui::Context) {
    install_cjk_font(ctx);

    // 0.36 起样式按明暗主题分别存放，两个主题都写入同一套深色配置
    ctx.set_theme(egui::Theme::Dark);
    ctx.all_styles_mut(|style| {
        style.spacing.item_spacing = egui::vec2(8.0, 8.0);
        style.spacing.button_padding = egui::vec2(10.0, 6.0);
        style.visuals = visuals();
    });
}

/// egui 内置字体不含 CJK 字形，运行时加载系统中文字体作为主字体
fn install_cjk_font(ctx: &egui::Context) {
    let Some(bytes) = load_cjk_font() else {
        eprintln!("未找到中文字体，界面中文可能显示为方块");
        return;
    };

    let mut fonts = FontDefinitions::default();
    fonts
        .font_data
        .insert("cjk".to_owned(), Arc::new(FontData::from_owned(bytes)));
    for family in [FontFamily::Proportional, FontFamily::Monospace] {
        fonts
            .families
            .entry(family)
            .or_default()
            .insert(0, "cjk".to_owned());
    }
    ctx.set_fonts(fonts);
}

fn load_cjk_font() -> Option<Vec<u8>> {
    let mut candidates: Vec<String> = Vec::new();

    #[cfg(windows)]
    {
        let windir = std::env::var("WINDIR").unwrap_or_else(|_| "C:/Windows".to_owned());
        let fonts = format!("{windir}/Fonts");
        for name in [
            "msyh.ttc",
            "Deng.ttf",
            "simhei.ttf",
            "NotoSansSC-VF.ttf",
            "Noto Sans SC (TrueType).otf",
        ] {
            candidates.push(format!("{fonts}/{name}"));
        }
    }
    #[cfg(target_os = "macos")]
    for path in [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ] {
        candidates.push(path.to_owned());
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    for path in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ] {
        candidates.push(path.to_owned());
    }

    for path in candidates {
        let Ok(bytes) = std::fs::read(&path) else { continue };
        // 只接受 sfnt 系列：TrueType / OTF / TTC（epaint 使用 skrifa，支持 TTC 的第 0 个 face）
        let valid = matches!(
            bytes.get(0..4),
            Some([0x00, 0x01, 0x00, 0x00])
                | Some(b"OTTO")
                | Some(b"true")
                | Some(b"ttcf")
        );
        if valid {
            return Some(bytes);
        }
    }
    None
}

/// 小节标题（侧边栏）
pub fn section_label(ui: &mut egui::Ui, text: &str) {
    ui.label(egui::RichText::new(text).size(11.0).strong().color(SUBTEXT));
}

/// 带边框的卡片容器
pub fn card_frame() -> egui::Frame {
    egui::Frame::new()
        .fill(CARD_BG)
        .stroke(Stroke::new(1.0, THIN_BORDER))
        .corner_radius(CornerRadius::same(11))
        .inner_margin(egui::Margin::same(16))
}
