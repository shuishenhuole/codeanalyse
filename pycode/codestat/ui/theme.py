"""
界面主题与通用控件

集中维护配色、圆角、间距等视觉规范，以及输入框、统计卡片、
导出按钮等可复用控件，避免界面代码散落在各个模块中。
"""

import flet as ft

# ==================== 主题配色 ====================

BG_COLOR = "#111318"          # 页面底色
PANEL_BG = "#171A21"          # 侧边栏
CARD_BG = "#1B202A"           # 卡片
DIVIDER = "#2A303D"           # 分割线
THIN_BORDER = "#232A36"       # 卡片细边框
TEXT_COLOR = "#F3F4F6"        # 主文字
VALUE_COLOR = "#F7F9FC"       # 统计数值（接近白色）
SUBTEXT_COLOR = "#9CA3AF"     # 次级文字
MUTED_COLOR = "#6B7280"       # 弱化文字
PRIMARY_COLOR = "#5685FF"     # 品牌强调色
PRIMARY_HOVER = "#6E97FF"     # 主按钮悬停提亮
ICON_COLOR = "#8FB0FF"        # 主色调浅色版（图标统一色）
BTN_SECONDARY_TEXT = "#D1D5DB"  # 次级按钮文字
ERROR_COLOR = "#F87171"       # 错误提示文字

# 输入框边框 (默认/聚焦两态)
FIELD_BORDER = {
    ft.ControlState.DEFAULT: ft.OutlineInputBorder(
        border_radius=8, side=ft.BorderSide(1, DIVIDER)
    ),
    ft.ControlState.FOCUSED: ft.OutlineInputBorder(
        border_radius=8, side=ft.BorderSide(1.5, PRIMARY_COLOR)
    ),
}


# ==================== 通用控件 ====================


def dark_text_field(
    hint_text: str,
    prefix_icon: ft.IconData,
    value: str = "",
    suffix: ft.Control | None = None,
    helper_text: str | None = None,
    *,
    read_only: bool = False,
    expand: bool = True,
    width: int | float | None = None,
) -> ft.TextField:
    """构建深色风格输入框 (高 42px，圆角 8px)"""
    return ft.TextField(
        value=value,
        hint_text=hint_text,
        hint_style=ft.TextStyle(color=MUTED_COLOR, size=12.5),
        text_style=ft.TextStyle(color=TEXT_COLOR, size=13),
        prefix_icon=prefix_icon,
        suffix=suffix,
        helper=helper_text,
        helper_max_lines=3,
        helper_style=ft.TextStyle(color=MUTED_COLOR, size=11),
        color=SUBTEXT_COLOR,
        cursor_color=PRIMARY_COLOR,
        border=FIELD_BORDER,
        bgcolor=BG_COLOR,
        content_padding=ft.Padding(12, 8, 6, 8),
        height=42,
        read_only=read_only,
        expand=expand,
        width=width,
    )


def section_label(text: str) -> ft.Text:
    """侧边栏小节标题 (小号灰色)"""
    return ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=SUBTEXT_COLOR)


def stat_tile(kind: str, label: str, icon: ft.IconData) -> tuple[ft.Control, ft.Text]:
    """构建概览统计卡片：紧凑横向布局，数值大字号接近白色"""
    value = ft.Text(
        "0", key=f"stat-{kind}", size=32, weight=ft.FontWeight.BOLD, color=MUTED_COLOR
    )
    tile = ft.Container(
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    content=ft.Icon(icon, size=20, color=ICON_COLOR),
                    width=38,
                    height=38,
                    bgcolor=ft.Colors.with_opacity(0.10, PRIMARY_COLOR),
                    border_radius=9,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Column(
                    spacing=0,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        value,
                        ft.Text(label, size=13, color=SUBTEXT_COLOR),
                    ],
                ),
            ],
        ),
        expand=True,
        bgcolor=CARD_BG,
        border=ft.Border.all(1, THIN_BORDER),
        border_radius=11,
        padding=ft.Padding(16, 14, 16, 14),
    )
    return tile, value


def export_button(label: str, icon: ft.IconData, key: str) -> ft.TextButton:
    """构建导出工具栏内的轻量文字按钮"""
    return ft.TextButton(
        label,
        icon=icon,
        key=key,
        style=ft.ButtonStyle(
            color=BTN_SECONDARY_TEXT,
            icon_color=SUBTEXT_COLOR,
            padding=ft.Padding(10, 6, 10, 6),
        ),
    )


def group_divider() -> ft.Container:
    """导出按钮组内的细分隔线"""
    return ft.Container(width=1, height=20, bgcolor=DIVIDER)


def primary_button_style() -> ft.ButtonStyle:
    """主操作按钮样式（蓝色填充、悬停提亮）"""
    return ft.ButtonStyle(
        bgcolor={
            ft.ControlState.DEFAULT: PRIMARY_COLOR,
            ft.ControlState.HOVERED: PRIMARY_HOVER,
        },
        color="#FFFFFF",
        icon_color="#FFFFFF",
        elevation=0,
        padding=ft.Padding(16, 12, 16, 12),
        shape=ft.RoundedRectangleBorder(radius=8),
    )


def secondary_button_style() -> ft.ButtonStyle:
    """次级描边按钮样式"""
    return ft.ButtonStyle(
        color=BTN_SECONDARY_TEXT,
        icon_color=ICON_COLOR,
        side=ft.BorderSide(1, DIVIDER),
        padding=ft.Padding(14, 10, 14, 10),
        shape=ft.RoundedRectangleBorder(radius=8),
    )
