//! 右侧主内容区
//!
//! 对应 Python 版 `codestat/ui/main_panel.py`：概览卡片、结果表格与导出工具栏。
//! 表格用 egui 的 painter 自绘，便于精确复刻「语言列占两份、数值列右对齐」的布局。

use egui::{
    Align, Align2, Color32, CornerRadius, FontId, Layout, Margin, Rect, RichText, Sense, Stroke,
    vec2,
};

use codeanalyse::core::{LangStat, LineStats};

use crate::theme;

const ROW_HEIGHT: f32 = 38.0;
const HEADER_HEIGHT: f32 = 34.0;

/// 可导出的格式
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum ExportKind {
    Json,
    Csv,
    Word,
}

/// 主面板渲染数据
pub struct MainPanelState<'a> {
    pub results: &'a [LangStat],
    pub scanning: bool,
    /// 空状态提示文案（未统计 / 统计中 / 无结果）
    pub hint: &'a str,
}

/// 主面板产生的动作
#[derive(Default)]
pub struct MainPanelAction {
    pub export: Option<ExportKind>,
}

/// 绘制主内容区
pub fn show(ui: &mut egui::Ui, state: &MainPanelState<'_>) -> MainPanelAction {
    let mut action = MainPanelAction::default();
    let (files, totals) = totals(state.results);

    ui.label(RichText::new("统计概览").size(22.0).strong().color(theme::TEXT));
    ui.add_space(2.0);
    ui.label(
        RichText::new("分析项目代码规模，快速了解代码分布")
            .size(12.5)
            .color(theme::MUTED),
    );
    ui.add_space(16.0);

    // ==================== 概览卡片 ====================
    // 列数随面板宽度自适应：宽 → 4 列；变窄 → 2×2；极窄 → 纵向堆叠。
    // 高 DPI 小窗口下每列分到的宽度可能小于卡片内容的最小宽度，
    // 固定 4 列会把卡片挤压换行甚至溢出面板，因此按宽度降级列数。
    let gap = 16.0;
    let available = ui.available_width();
    let columns = if available >= 500.0 {
        4
    } else if available >= 300.0 {
        2
    } else {
        1
    };
    let cards = [
        // 图标使用 CJK 字体必定覆盖的汉字，避免符号缺字形显示为方块
        ("文", "文件总数", format_number(files)),
        ("</>", "代码行数", format_number(totals.code)),
        ("//", "注释行数", format_number(totals.comment)),
        ("空", "空行数", format_number(totals.blank)),
    ];
    let has_result = !state.results.is_empty();
    for (row_index, chunk) in cards.chunks(columns).enumerate() {
        if row_index > 0 {
            ui.add_space(gap);
        }
        let card_width =
            (available - gap * (chunk.len() - 1) as f32) / chunk.len() as f32;
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing.x = gap;
            for (icon, label, value) in chunk {
                stat_card(ui, card_width, icon, label, value, has_result);
            }
        });
    }

    ui.add_space(16.0);

    // ==================== 结果卡片 ====================
    let card_height = ui.available_height();
    egui::Frame::new()
        .fill(theme::CARD_BG)
        .stroke(Stroke::new(1.0, theme::THIN_BORDER))
        .corner_radius(CornerRadius::same(13))
        .inner_margin(Margin::same(20))
        .show(ui, |ui| {
            ui.set_min_height((card_height - 4.0).max(180.0));
            ui.set_width(ui.available_width());

            header_row(
                ui,
                !state.scanning && !state.results.is_empty(),
                &mut action,
            );
            ui.add_space(16.0);

            if state.results.is_empty() {
                empty_state(ui, state.hint);
            } else {
                result_table(ui, state.results);
            }
        });

    action
}

/// 卡片标题行 + 右侧导出按钮组
fn header_row(ui: &mut egui::Ui, export_enabled: bool, action: &mut MainPanelAction) {
    ui.horizontal(|ui| {
        ui.vertical(|ui| {
            ui.label(RichText::new("统计结果").size(18.0).color(theme::TEXT));
            ui.add_space(2.0);
            ui.label(
                RichText::new("项目文件明细 · 按语言查看代码行数与注释分布")
                    .size(12.0)
                    .color(theme::MUTED),
            );
        });

        ui.with_layout(Layout::right_to_left(Align::Center), |ui| {
            // 外框 + 内部细分隔线，复刻原版导出按钮组
            egui::Frame::new()
                .fill(theme::BG)
                .stroke(Stroke::new(1.0, theme::DIVIDER))
                .corner_radius(CornerRadius::same(8))
                .inner_margin(Margin::same(2))
                .show(ui, |ui| {
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 0.0;
                        // right_to_left 布局从右往左排列，因此倒序声明，
                        // 视觉上仍保持「JSON | CSV | Word」的原始顺序
                        let entries = [
                            (ExportKind::Word, "Word"),
                            (ExportKind::Csv, "CSV"),
                            (ExportKind::Json, "JSON"),
                        ];
                        for (index, (kind, label)) in entries.iter().enumerate() {
                            let button = egui::Button::new(
                                RichText::new(*label)
                                    .size(12.0)
                                    .color(if export_enabled {
                                        theme::BTN_SECONDARY_TEXT
                                    } else {
                                        theme::MUTED
                                    }),
                            )
                            .fill(Color32::TRANSPARENT)
                            .stroke(Stroke::NONE)
                            .corner_radius(CornerRadius::same(6));
                            if ui.add_enabled(export_enabled, button).clicked() {
                                action.export = Some(*kind);
                            }
                            if index + 1 < entries.len() {
                                let (rect, _) = ui.allocate_exact_size(
                                    vec2(1.0, 18.0),
                                    Sense::hover(),
                                );
                                ui.painter().rect_filled(
                                    rect,
                                    CornerRadius::ZERO,
                                    theme::DIVIDER,
                                );
                            }
                        }
                    });
                });
        });
    });
}

/// 单张概览卡片：图标块 + 数值 + 标签
///
/// 内容是固定最小宽度的，而 `width` 由可用宽度均分而来；
/// 窗口较窄时若不缩小内部元素，内容会把卡片撑开，导致整行溢出被截断。
/// 因此按宽度分两档：常规 / 紧凑（缩小图标、字号与内边距）。
fn stat_card(
    ui: &mut egui::Ui,
    width: f32,
    icon: &str,
    label: &str,
    value: &str,
    has_value: bool,
) {
    // 卡片内边距：紧凑档从 16 收窄到 12
    let margin = if width < 150.0 {
        Margin::same(12)
    } else {
        Margin {
            left: 16,
            right: 16,
            top: 14,
            bottom: 14,
        }
    };
    let inner_width = width - (margin.left + margin.right) as f32;

    // 尺寸分档：窄卡片用更小的图标块与数值字号
    let compact = width < 150.0;
    let icon_box = if compact { 30.0 } else { 38.0 };
    let icon_font = if compact { 12.0 } else { 14.0 };
    let value_size = if compact { 20.0 } else { 28.0 };
    let label_size = if compact { 11.0 } else { 12.5 };
    let icon_radius = if compact { 7 } else { 9 };

    egui::Frame::new()
        .fill(theme::CARD_BG)
        .stroke(Stroke::new(1.0, theme::THIN_BORDER))
        .corner_radius(CornerRadius::same(11))
        .inner_margin(margin)
        .show(ui, |ui| {
            // set_width 只是「最小宽度」，内容超出会撑开卡片，故先保证内容 < inner_width
            ui.set_width(inner_width);
            // 覆盖继承自外层横向布局的大间距（16px），卡片内部统一用小间距
            ui.spacing_mut().item_spacing.x = 10.0;
            // 图标块与文字整体垂直居中
            ui.with_layout(Layout::left_to_right(Align::Center), |ui| {
                let (rect, _) =
                    ui.allocate_exact_size(vec2(icon_box, icon_box), Sense::hover());
                ui.painter().rect_filled(
                    rect,
                    CornerRadius::same(icon_radius),
                    theme::tint(theme::PRIMARY, 26),
                );
                ui.painter().text(
                    rect.center(),
                    Align2::CENTER_CENTER,
                    icon,
                    FontId::proportional(icon_font),
                    theme::ICON,
                );

                ui.vertical(|ui| {
                    ui.label(
                        RichText::new(value)
                            .size(value_size)
                            .strong()
                            .color(if has_value { theme::VALUE } else { theme::MUTED }),
                    );
                    ui.label(RichText::new(label).size(label_size).color(theme::SUBTEXT));
                });
            });
        });
}

/// 空状态：圆形图标 + 主提示 + 说明
fn empty_state(ui: &mut egui::Ui, hint: &str) {
    ui.vertical_centered(|ui| {
        ui.add_space((ui.available_height() - 200.0).max(24.0) / 2.0);
        let (rect, _) = ui.allocate_exact_size(vec2(64.0, 64.0), Sense::hover());
        ui.painter()
            .circle_filled(rect.center(), 32.0, theme::tint(theme::PRIMARY, 26));
        ui.painter().text(
            rect.center(),
            Align2::CENTER_CENTER,
            "文",
            FontId::proportional(24.0),
            theme::ICON,
        );
        ui.add_space(10.0);
        ui.label(RichText::new("暂无统计数据").size(17.0).color(theme::TEXT));
        ui.add_space(4.0);
        ui.label(RichText::new(hint).size(13.0).color(theme::SUBTEXT));
        ui.add_space(2.0);
        ui.label(
            RichText::new("统计完成后可导出 JSON / CSV / Word，或使用 Markdown 转 Word 工具")
                .size(11.5)
                .color(theme::MUTED),
        );
    });
}

/// 结果表格：表头固定，行内容可滚动
fn result_table(ui: &mut egui::Ui, results: &[LangStat]) {
    let widths = column_widths(ui.available_width());
    let headers = ["语言", "文件数", "代码行", "注释行", "空行", "总行数"];

    draw_row(
        ui,
        &headers,
        &widths,
        HEADER_HEIGHT,
        DrawStyle {
            background: None,
            color: theme::SUBTEXT,
            size: 12.0,
        },
    );

    egui::ScrollArea::vertical()
        .auto_shrink([false, false])
        .show(ui, |ui| {
            let mut total_files = 0usize;
            let mut total = LineStats::default();

            for (index, stat) in results.iter().enumerate() {
                let cells = [
                    stat.name.clone(),
                    format_number(stat.files),
                    format_number(stat.stats.code),
                    format_number(stat.stats.comment),
                    format_number(stat.stats.blank),
                    format_number(stat.stats.total),
                ];
                // 交替行使用极淡白色叠加，保证深色卡片上仍有层次
                let background = (index % 2 == 1)
                    .then(|| Color32::from_rgba_unmultiplied(255, 255, 255, 6));
                draw_row(
                    ui,
                    &cells,
                    &widths,
                    ROW_HEIGHT,
                    DrawStyle {
                        background,
                        color: theme::TEXT,
                        size: 13.0,
                    },
                );

                total_files += stat.files;
                total += stat.stats;
            }

            let total_cells = [
                "总计".to_owned(),
                format_number(total_files),
                format_number(total.code),
                format_number(total.comment),
                format_number(total.blank),
                format_number(total.total),
            ];
            draw_row(
                ui,
                &total_cells,
                &widths,
                ROW_HEIGHT,
                DrawStyle {
                    background: Some(theme::tint(theme::PRIMARY, 30)),
                    color: theme::VALUE,
                    size: 13.5,
                },
            );
        });
}

struct DrawStyle {
    background: Option<Color32>,
    color: Color32,
    size: f32,
}

/// 绘制一行：首列左对齐，数值列右对齐并留出右侧内边距
///
/// 泛型 `S: AsRef<str>` 让表头（&str）与数据行（String）共用同一套绘制逻辑。
fn draw_row<S: AsRef<str>>(
    ui: &mut egui::Ui,
    cells: &[S],
    widths: &[f32],
    height: f32,
    style: DrawStyle,
) {
    let total_width: f32 = widths.iter().sum();
    let (rect, _) = ui.allocate_exact_size(vec2(total_width, height), Sense::hover());

    if let Some(background) = style.background {
        ui.painter()
            .rect_filled(rect, CornerRadius::ZERO, background);
    }
    ui.painter().line_segment(
        [rect.left_bottom(), rect.right_bottom()],
        Stroke::new(1.0, theme::THIN_BORDER),
    );

    let mut x = rect.left();
    for (index, cell) in cells.iter().enumerate() {
        let width = widths.get(index).copied().unwrap_or(0.0);
        let cell_rect = Rect::from_min_size(egui::pos2(x, rect.top()), vec2(width, rect.height()));
        let (position, anchor) = if index == 0 {
            (
                egui::pos2(cell_rect.left() + 8.0, cell_rect.center().y),
                Align2::LEFT_CENTER,
            )
        } else {
            (
                egui::pos2(cell_rect.right() - 18.0, cell_rect.center().y),
                Align2::RIGHT_CENTER,
            )
        };
        ui.painter().text(
            position,
            anchor,
            cell.as_ref(),
            FontId::proportional(style.size),
            style.color,
        );
        x += width;
    }
}

/// 语言列占 2 份，其余 5 个数值列各占 1 份
fn column_widths(available: f32) -> Vec<f32> {
    let unit = available / 7.0;
    vec![unit * 2.0, unit, unit, unit, unit, unit]
}

/// 汇总文件数与各类行数
fn totals(results: &[LangStat]) -> (usize, LineStats) {
    let mut files = 0usize;
    let mut stats = LineStats::default();
    for item in results {
        files += item.files;
        stats += item.stats;
    }
    (files, stats)
}

/// 千分位格式化
pub fn format_number(value: usize) -> String {
    let digits = value.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, ch) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index) % 3 == 0 {
            out.push(',');
        }
        out.push(ch);
    }
    out
}
