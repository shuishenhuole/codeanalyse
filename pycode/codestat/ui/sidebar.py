"""
侧边栏模块

负责构建左侧操作面板：目录输入、排除规则、开始统计按钮、
Markdown 转 Word 工具入口，以及底部状态栏。
"""

from dataclasses import dataclass

import flet as ft

from .theme import (
    DIVIDER,
    MUTED_COLOR,
    PANEL_BG,
    PRIMARY_COLOR,
    SUBTEXT_COLOR,
    TEXT_COLOR,
    THIN_BORDER,
    dark_text_field,
    primary_button_style,
    secondary_button_style,
    section_label,
)


@dataclass
class SidebarView:
    """侧边栏控件集合，供主程序绑定事件和更新状态"""

    container: ft.Container
    dir_edit: ft.TextField
    exclude_edit: ft.TextField
    browse_btn: ft.IconButton
    scan_btn: ft.FilledButton
    md2docx_btn: ft.OutlinedButton
    progress: ft.ProgressRing
    status_text: ft.Text


def build_sidebar(initial_directory: str) -> SidebarView:
    """构建左侧操作面板"""
    # 目录输入框内的浏览按钮
    browse_btn = ft.IconButton(
        ft.Icons.FOLDER_OPEN,
        icon_size=18,
        icon_color=SUBTEXT_COLOR,
        tooltip="浏览目录",
        style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
    )
    dir_edit = dark_text_field(
        "选择要统计的目录",
        ft.Icons.PUBLIC,
        value=initial_directory,
        suffix=browse_btn,
    )
    exclude_edit = dark_text_field(
        "目录名/文件名/后缀",
        ft.Icons.BLOCK,
        helper_text="示例: test docs dist *.min.js，空格或逗号分隔",
    )

    scan_btn = ft.FilledButton(
        "开始统计",
        icon=ft.Icons.PLAY_ARROW_ROUNDED,
        key="scan",
        expand=True,
        style=primary_button_style(),
    )

    md2docx_btn = ft.OutlinedButton(
        "Markdown 转 Word",
        icon=ft.Icons.TRANSFORM,
        key="md2docx",
        expand=True,
        style=secondary_button_style(),
    )

    progress = ft.ProgressRing(
        width=16, height=16, stroke_width=2.5, color=PRIMARY_COLOR, visible=False
    )
    status_text = ft.Text("就绪", size=12, color=SUBTEXT_COLOR)

    # 底部固定状态栏
    status_bar = ft.Container(
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        progress,
                        ft.Icon(ft.Icons.CIRCLE, size=7, color=MUTED_COLOR, visible=False),
                        status_text,
                    ],
                ),
                ft.Text("支持 40+ 种编程语言", size=11, color=MUTED_COLOR),
            ],
        ),
        border=ft.Border(top=ft.BorderSide(1, DIVIDER)),
        padding=ft.Padding(0, 12, 0, 4),
    )

    container = ft.Container(
        width=280,
        bgcolor=PANEL_BG,
        border=ft.Border(right=ft.BorderSide(1, THIN_BORDER)),
        padding=ft.Padding(20, 22, 20, 14),
        content=ft.Column(
            spacing=16,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src="assets/icon.png", width=34, height=34, border_radius=8),
                        ft.Column(
                            spacing=1,
                            controls=[
                                ft.Text(
                                    "CodeStat",
                                    key="title",
                                    size=17,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXT_COLOR,
                                ),
                                ft.Text("代码规模分析工具", size=11.5, color=SUBTEXT_COLOR),
                            ],
                        ),
                    ],
                ),
                section_label("统计目录"),
                dir_edit,
                section_label("排除规则"),
                exclude_edit,
                ft.Row(spacing=8, controls=[scan_btn]),
                section_label("工具"),
                ft.Row(spacing=8, controls=[md2docx_btn]),
                ft.Container(expand=True),
                status_bar,
            ],
        ),
    )

    return SidebarView(
        container=container,
        dir_edit=dir_edit,
        exclude_edit=exclude_edit,
        browse_btn=browse_btn,
        scan_btn=scan_btn,
        md2docx_btn=md2docx_btn,
        progress=progress,
        status_text=status_text,
    )
