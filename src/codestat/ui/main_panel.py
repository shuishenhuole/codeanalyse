"""
主内容区模块

负责构建右侧概览统计卡片、结果表格、导出工具栏，并封装结果渲染逻辑。
"""

from dataclasses import dataclass, field

import flet as ft

from .theme import (
    BG_COLOR,
    CARD_BG,
    DIVIDER,
    ICON_COLOR,
    MUTED_COLOR,
    PRIMARY_COLOR,
    SUBTEXT_COLOR,
    TEXT_COLOR,
    THIN_BORDER,
    VALUE_COLOR,
    export_button,
    group_divider,
    stat_tile,
)

TABLE_COLUMNS = ["语言", "文件数", "代码行", "注释行", "空行", "总行数"]


def _format_number(number: int) -> str:
    """千分位格式化"""
    return f"{number:,}"


def _grid_row(
    values: list[str],
    *,
    header: bool = False,
    bold: bool = False,
    bgcolor: str | None = None,
) -> ft.Container:
    """构建一行栅格：首列语言占 2 份，其余数值列各占 1 份"""
    cells = []
    for index, value in enumerate(values):
        numeric = index > 0
        cells.append(
            ft.Container(
                content=ft.Text(
                    value,
                    size=12 if header else 13,
                    weight=ft.FontWeight.BOLD if (header or bold) else ft.FontWeight.NORMAL,
                    color=SUBTEXT_COLOR if header else TEXT_COLOR,
                ),
                expand=2 if not numeric else 1,
                alignment=ft.Alignment.CENTER_RIGHT if numeric else ft.Alignment.CENTER_LEFT,
                padding=ft.Padding(8, 0, 18, 0) if numeric else ft.Padding(8, 0, 8, 0),
            )
        )

    return ft.Container(
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=cells,
        ),
        height=38,
        bgcolor=bgcolor,
        border=ft.Border(bottom=ft.BorderSide(1, THIN_BORDER)),
    )


@dataclass
class MainPanel:
    """主内容区控件集合，供主程序更新统计结果"""

    container: ft.Container
    empty_view: ft.Container
    table_scroll: ft.Container
    hint_text: ft.Text
    rows_column: ft.Column
    stat_files: ft.Text
    stat_code: ft.Text
    stat_comment: ft.Text
    stat_blank: ft.Text
    export_buttons: list[ft.TextButton] = field(default_factory=list)

    def update_stats(self, totals: list[int] | None) -> None:
        """更新概览统计卡片数值 (未统计时显示弱化占位 0)"""
        values = ["0"] * 4 if totals is None else [f"{int(total):,}" for total in totals[:4]]
        color = MUTED_COLOR if totals is None else VALUE_COLOR
        for value, text in zip(
            (self.stat_files, self.stat_code, self.stat_comment, self.stat_blank),
            values,
            strict=True,
        ):
            value.value = text
            value.color = color

    def show_hint(self, message: str) -> None:
        """切换到空状态并显示提示文案"""
        self.hint_text.value = message
        self.empty_view.visible = True
        self.table_scroll.visible = False

    def clear_rows(self) -> None:
        """清空结果表格"""
        self.rows_column.controls.clear()

    def set_export_enabled(self, enabled: bool) -> None:
        """切换导出按钮的可用视觉状态"""
        for button in self.export_buttons:
            button.opacity = 1.0 if enabled else 0.45

    def render(self, results: dict) -> list[int] | None:
        """
        渲染统计结果

        参数:
            results: scan_directory 返回的统计结果

        返回:
            各列总计 [文件数, 代码行, 注释行, 空行, 总行数]；
            没有可统计数据时返回 None
        """
        if not results:
            self.update_stats(None)
            self.show_hint("未找到可统计的代码文件")
            return None

        # 按代码行数降序排列
        sorted_items = sorted(
            results.items(), key=lambda item: item[1][1].code, reverse=True
        )

        rows = []
        totals = [0, 0, 0, 0, 0]
        for index, (name, (count, stats)) in enumerate(sorted_items):
            values = [
                name,
                _format_number(count),
                _format_number(stats.code),
                _format_number(stats.comment),
                _format_number(stats.blank),
                _format_number(stats.total),
            ]
            totals[0] += count
            totals[1] += stats.code
            totals[2] += stats.comment
            totals[3] += stats.blank
            totals[4] += stats.total
            stripe = ft.Colors.with_opacity(0.025, "#FFFFFF") if index % 2 == 1 else None
            rows.append(_grid_row(values, bgcolor=stripe))

        rows.append(
            _grid_row(
                ["总计", *[_format_number(total) for total in totals]],
                bold=True,
                bgcolor=ft.Colors.with_opacity(0.12, PRIMARY_COLOR),
            )
        )
        self.rows_column.controls = rows

        self.update_stats(totals)
        self.empty_view.visible = False
        self.table_scroll.visible = True
        return totals


def build_main_panel() -> MainPanel:
    """构建右侧主内容区"""
    files_tile, stat_files = stat_tile("files", "文件总数", ft.Icons.DESCRIPTION)
    code_tile, stat_code = stat_tile("code", "代码行数", ft.Icons.CODE)
    comment_tile, stat_comment = stat_tile("comment", "注释行数", ft.Icons.COMMENT)
    blank_tile, stat_blank = stat_tile("blank", "空行数", ft.Icons.BLUR_CIRCULAR)

    # ==================== 结果表格 ====================

    rows_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    header_row = _grid_row(TABLE_COLUMNS, header=True)

    hint_text = ft.Text("选择一个项目目录，开始分析代码规模", size=14, color=SUBTEXT_COLOR)
    empty_view = ft.Container(
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.FOLDER_ZIP, size=30, color=ICON_COLOR),
                    width=64,
                    height=64,
                    bgcolor=ft.Colors.with_opacity(0.10, PRIMARY_COLOR),
                    border_radius=999,
                    alignment=ft.Alignment.CENTER,
                ),
                ft.Text("暂无统计数据", size=17, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
                hint_text,
                ft.Text(
                    "统计完成后可导出 JSON / CSV / Word，或使用 Markdown 转 Word 工具",
                    size=12,
                    color=MUTED_COLOR,
                ),
            ],
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    table_scroll = ft.Container(
        content=ft.Column(spacing=0, controls=[header_row, rows_column]),
        expand=True,
        visible=False,
    )

    # ==================== 导出工具栏 ====================

    export_buttons = [
        export_button("JSON", ft.Icons.DOWNLOAD, "export-json"),
        export_button("CSV", ft.Icons.DOWNLOAD, "export-csv"),
        export_button("Word", ft.Icons.MENU_BOOK, "export-word"),
    ]
    export_group = ft.Container(
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                export_buttons[0],
                group_divider(),
                export_buttons[1],
                group_divider(),
                export_buttons[2],
            ],
        ),
        bgcolor=BG_COLOR,
        border=ft.Border.all(1, DIVIDER),
        border_radius=8,
        padding=ft.Padding(2, 2, 2, 2),
    )

    results_card = ft.Container(
        content=ft.Column(
            spacing=16,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text(
                                    "统计结果",
                                    size=18,
                                    weight=ft.FontWeight.W_500,
                                    color=TEXT_COLOR,
                                ),
                                ft.Text(
                                    "项目文件明细 · 按语言查看代码行数与注释分布",
                                    size=12,
                                    color=MUTED_COLOR,
                                ),
                            ],
                        ),
                        export_group,
                    ],
                ),
                empty_view,
                table_scroll,
            ],
        ),
        expand=True,
        bgcolor=CARD_BG,
        border=ft.Border.all(1, THIN_BORDER),
        border_radius=13,
        padding=20,
    )

    container = ft.Container(
        content=ft.Column(
            spacing=16,
            expand=True,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(
                            "统计概览",
                            size=22,
                            weight=ft.FontWeight.W_600,
                            color=TEXT_COLOR,
                        ),
                        ft.Text(
                            "分析项目代码规模，快速了解代码分布",
                            size=12.5,
                            color=MUTED_COLOR,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=16,
                    controls=[files_tile, code_tile, comment_tile, blank_tile],
                ),
                results_card,
            ],
        ),
        expand=True,
        padding=ft.Padding(24, 20, 24, 16),
    )

    return MainPanel(
        container=container,
        empty_view=empty_view,
        table_scroll=table_scroll,
        hint_text=hint_text,
        rows_column=rows_column,
        stat_files=stat_files,
        stat_code=stat_code,
        stat_comment=stat_comment,
        stat_blank=stat_blank,
        export_buttons=export_buttons,
    )
