"""
Flet 图形界面主程序

该模块实现 CodeStat 的桌面界面，使用 Flet 构建，深色仪表盘风格。

界面布局:
    1. 左侧边栏: 应用标识、统计目录/排除项配置、开始统计、状态指示
    2. 右侧主区: 四枚概览统计磁贴 + 统计结果表格卡片 (含导出按钮)

后台扫描使用 threading.Thread，结果通过 page.run_thread 回主线程更新界面。
"""

import os
import re
import threading

import flet as ft

from codestat.core import scan_directory
from codestat.exporters import export_csv, export_json, export_word

# ==================== 主题配色 ====================

BG_TOP = "#0E1322"
BG_BOTTOM = "#151C30"
SIDEBAR_BG = "#141B2D"
CARD_BG = "#1A2338"
CARD_BORDER = "#28334F"
FIELD_BG = "#212C47"
TEXT_COLOR = "#EEF2FF"
SUBTEXT_COLOR = "#A6B4D7"
MUTED_COLOR = "#5F6E94"
PRIMARY_COLOR = "#5B8CFF"

STAT_COLORS = {
    "files": "#5B8CFF",
    "code": "#3DDC97",
    "comment": "#FFB74D",
    "blank": "#9AA7C7",
}

EXPORT_COLORS = {
    "json": "#3DDC97",
    "csv": "#FFB74D",
    "word": "#5B8CFF",
}

TABLE_COLUMNS = ["语言", "文件数", "代码行", "注释行", "空行", "总行数"]

# 输入框边框 (默认/聚焦两态)
FIELD_BORDER = {
    ft.ControlState.DEFAULT: ft.OutlineInputBorder(
        border_radius=12, side=ft.BorderSide(1, CARD_BORDER)
    ),
    ft.ControlState.FOCUSED: ft.OutlineInputBorder(
        border_radius=12, side=ft.BorderSide(2, PRIMARY_COLOR)
    ),
}


def _dark_text_field(hint_text: str, prefix_icon: str, value: str = "") -> ft.TextField:
    """构建深色风格输入框"""
    return ft.TextField(
        value=value,
        hint_text=hint_text,
        hint_style=ft.TextStyle(color=SUBTEXT_COLOR, size=13),
        text_style=ft.TextStyle(color=TEXT_COLOR, size=14),
        prefix_icon=prefix_icon,
        color=SUBTEXT_COLOR,
        cursor_color=PRIMARY_COLOR,
        border=FIELD_BORDER,
        bgcolor=FIELD_BG,
        content_padding=ft.Padding(14, 12, 14, 12),
        expand=True,
    )


def _section_label(text: str) -> ft.Text:
    """侧边栏小节标题"""
    return ft.Text(
        text, size=12, weight=ft.FontWeight.BOLD, color=SUBTEXT_COLOR,
        selectable=False,
    )


def _stat_tile(kind: str, label: str, icon: str) -> tuple[ft.Control, ft.Text]:
    """构建概览统计磁贴，返回 (磁贴控件, 数值文本)"""
    color = STAT_COLORS[kind]
    value = ft.Text("—", key=f"stat-{kind}", size=26, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
    tile = ft.Container(
        content=ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    content=ft.Icon(icon, color=color, size=24),
                    bgcolor=ft.Colors.with_opacity(0.15, color),
                    border_radius=14,
                    padding=12,
                ),
                ft.Column(
                    spacing=2,
                    controls=[
                        value,
                        ft.Text(label, size=13, color=SUBTEXT_COLOR),
                    ],
                ),
            ],
        ),
        expand=True,
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        border_radius=20,
        padding=20,
    )
    return tile, value


def main(page: ft.Page):
    """Flet 应用主入口"""
    page.title = "CodeStat - 代码量统计工具"
    page.window.icon = "assets/icon.png"
    page.width = 1160
    page.height = 780
    page.bgcolor = BG_TOP
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY_COLOR, font_family="Microsoft YaHei UI"
    )
    page.padding = 0

    # ==================== 状态 ====================

    state = {"results": {}, "worker": None}

    # ==================== 轻提示 (SnackBar) ====================

    snack_text = ft.Text("", size=13, color="#0B1020")
    snack = ft.SnackBar(snack_text, duration=2500, bgcolor="#D9E4FF")
    page.overlay.append(snack)

    def toast(message: str) -> None:
        """弹出轻提示"""
        snack_text.value = message
        snack.open = True
        page.update()

    # ==================== 文件选择器 ====================

    dir_picker = ft.FilePicker()
    save_picker = ft.FilePicker()
    page.services.append(dir_picker)
    page.services.append(save_picker)

    # ==================== 侧边栏控件 ====================

    dir_edit = _dark_text_field("选择要统计的目录", ft.Icons.FOLDER_OPEN, value=os.getcwd())
    exclude_edit = _dark_text_field(
        "目录名/文件名/后缀，空格或逗号分隔", ft.Icons.BLOCK,
    )

    browse_btn = ft.FilledButton(
        "浏览",
        icon=ft.Icons.FOLDER_OPEN,
        style=ft.ButtonStyle(
            bgcolor=FIELD_BG, color=SUBTEXT_COLOR, elevation=0,
            padding=ft.Padding(12, 10, 12, 10),
            side=ft.BorderSide(1, CARD_BORDER),
        ),
    )

    scan_btn = ft.FilledButton(
        "开始统计",
        icon=ft.Icons.SEARCH,
        key="scan",
        expand=True,
        style=ft.ButtonStyle(
            bgcolor=PRIMARY_COLOR, color="#0B1020", elevation=0,
            padding=ft.Padding(16, 14, 16, 14),
        ),
    )

    progress = ft.ProgressRing(
        width=22, height=22, stroke_width=3, color=PRIMARY_COLOR, visible=False
    )
    status_text = ft.Text("就绪", size=12, color=SUBTEXT_COLOR)

    sidebar = ft.Container(
        width=340,
        bgcolor=SIDEBAR_BG,
        border=ft.Border(right=ft.BorderSide(1, CARD_BORDER)),
        padding=ft.Padding(24, 24, 24, 18),
        content=ft.Column(
            spacing=18,
            controls=[
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Image(src="assets/icon.png", width=40, height=40, border_radius=10),
                        ft.Column(
                            spacing=2,
                            controls=[
                                ft.Text("CodeStat", key="title", size=20,
                                        weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                                ft.Text("代码量统计工具", size=12, color=SUBTEXT_COLOR),
                            ],
                        ),
                    ],
                ),
                ft.Container(height=1, bgcolor=CARD_BORDER),
                _section_label("统计目录"),
                ft.Row(spacing=10, controls=[dir_edit, browse_btn]),
                _section_label("排除项"),
                exclude_edit,
                ft.Row(spacing=12, controls=[scan_btn]),
                ft.Container(expand=True),
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[progress, status_text],
                ),
                ft.Text("支持 40+ 种编程语言", size=11, color=MUTED_COLOR),
            ],
        ),
    )

    # ==================== 概览磁贴 ====================

    files_tile, stat_files = _stat_tile("files", "文件数", ft.Icons.DESCRIPTION)
    code_tile, stat_code = _stat_tile("code", "代码行", ft.Icons.CODE)
    comment_tile, stat_comment = _stat_tile("comment", "注释行", ft.Icons.COMMENT)
    blank_tile, stat_blank = _stat_tile("blank", "空行", ft.Icons.BLUR_CIRCULAR)

    # ==================== 结果表格 ====================

    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(name)) for name in TABLE_COLUMNS],
        rows=[],
        column_spacing=40,
        heading_row_color=ft.Colors.with_opacity(0.06, PRIMARY_COLOR),
        heading_text_style=ft.TextStyle(
            weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR, size=13
        ),
        data_text_style=ft.TextStyle(color=TEXT_COLOR, size=13),
        horizontal_lines=ft.BorderSide(1, CARD_BORDER),
        horizontal_margin=8,
    )

    hint_text = ft.Text("请选择目录后点击「开始统计」", size=14, color=SUBTEXT_COLOR)
    empty_view = ft.Container(
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
            controls=[
                ft.Icon(ft.Icons.TABLE_VIEW, size=52, color=MUTED_COLOR),
                hint_text,
            ],
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    table_scroll = ft.Container(
        content=ft.Column(scroll=ft.ScrollMode.AUTO, controls=[table]),
        expand=True,
        visible=False,
    )

    export_buttons = [
        ft.FilledButton(
            label,
            icon=ft.Icons.DOWNLOAD if fmt != "word" else ft.Icons.MENU_BOOK,
            key=f"export-{fmt}",
            style=ft.ButtonStyle(
                bgcolor=EXPORT_COLORS[fmt], color="#0B1020", elevation=0,
                padding=ft.Padding(14, 8, 14, 8),
            ),
        )
        for fmt, label in (("json", "导出 JSON"), ("csv", "导出 CSV"), ("word", "导出 Word"))
    ]
    json_btn, csv_btn, word_btn = export_buttons

    results_card = ft.Container(
        content=ft.Column(
            spacing=16,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("统计结果", size=17, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                        ft.Row(spacing=10, controls=export_buttons),
                    ],
                ),
                empty_view,
                table_scroll,
            ],
        ),
        expand=True,
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        border_radius=20,
        padding=22,
    )

    main_area = ft.Container(
        content=ft.Column(
            spacing=18,
            expand=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text("统计概览", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                    ],
                ),
                ft.Row(spacing=14, controls=[files_tile, code_tile, comment_tile, blank_tile]),
                results_card,
            ],
        ),
        expand=True,
        padding=ft.Padding(28, 24, 28, 20),
    )

    # ==================== 辅助函数 ====================

    def parse_excludes() -> set[str]:
        """解析排除项输入 (支持空格/逗号/分号分隔，含中文标点)"""
        excludes = set()
        for token in re.split(r"[,，;；\s]+", exclude_edit.value or ""):
            token = token.strip().strip("/\\")
            if token:
                excludes.add(token)
        return excludes

    def dir_is_valid() -> bool:
        """当前目录输入是否为有效目录"""
        return os.path.isdir((dir_edit.value or "").strip())

    def set_busy(busy: bool) -> None:
        """切换扫描期间的控件视觉状态 (不禁用点击，点击时给出提示)"""
        scan_btn.opacity = 1.0 if (not busy and dir_is_valid()) else 0.45
        browse_btn.opacity = 0.45 if busy else 1.0
        progress.visible = busy
        has_results = bool(state["results"])
        for btn in export_buttons:
            btn.opacity = 1.0 if (not busy and has_results) else 0.45

    def update_stats(totals: list[int] | None) -> None:
        """更新概览统计磁贴数值"""
        values = ["—"] * 4 if totals is None else [str(t) for t in totals[:4]]
        for value, text in zip(
            (stat_files, stat_code, stat_comment, stat_blank), values, strict=True
        ):
            value.value = text

    def cell(text: str, numeric: bool = False, bold: bool = False) -> ft.DataCell:
        """构建表格单元格 (数值列右对齐)"""
        return ft.DataCell(
            ft.Text(
                text,
                text_align=ft.TextAlign.RIGHT if numeric else ft.TextAlign.START,
                weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            )
        )

    def show_hint(message: str) -> None:
        """切换到空状态并显示提示文案"""
        hint_text.value = message
        empty_view.visible = True
        table_scroll.visible = False

    # ==================== 事件处理 ====================

    def worker_running() -> bool:
        """后台扫描线程是否在运行"""
        worker = state["worker"]
        return worker is not None and worker.is_alive()

    async def browse_directory(e) -> None:
        """弹出目录选择对话框"""
        if worker_running():
            toast("正在统计中，请稍候...")
            return
        path = await dir_picker.get_directory_path(
            dialog_title="选择统计目录",
            initial_directory=(dir_edit.value or os.getcwd()).strip(),
        )
        if path:
            dir_edit.value = path
        set_busy(False)
        page.update()

    def render_results(results: dict) -> None:
        """渲染统计结果到表格"""
        state["results"] = results

        if not results:
            update_stats(None)
            show_hint("未找到可统计的代码文件")
            status_text.value = "未找到可统计的代码文件"
            set_busy(False)
            page.update()
            return

        # 按代码行数降序排列
        sorted_items = sorted(
            results.items(), key=lambda x: x[1][1].code, reverse=True
        )

        rows = []
        totals = [0, 0, 0, 0, 0]
        for i, (name, (count, stats)) in enumerate(sorted_items):
            values = [
                name, str(count), str(stats.code),
                str(stats.comment), str(stats.blank), str(stats.total),
            ]
            for j, v in enumerate(values[1:]):
                totals[j] += int(v)
            row = ft.DataRow(cells=[cell(v, numeric=j > 0) for j, v in enumerate(values)])
            if i % 2 == 1:
                row.color = ft.Colors.with_opacity(0.04, "#FFFFFF")
            rows.append(row)

        rows.append(
            ft.DataRow(
                cells=[
                    cell(v, numeric=j > 0, bold=True)
                    for j, v in enumerate(["总计", *[str(t) for t in totals]])
                ],
                color=ft.Colors.with_opacity(0.10, PRIMARY_COLOR),
            )
        )
        table.rows = rows

        update_stats(totals)
        empty_view.visible = False
        table_scroll.visible = True
        status_text.value = f"统计完成: 共 {totals[0]} 个文件, {totals[4]} 行"
        set_busy(False)
        page.update()

    def render_error(error: str) -> None:
        """渲染扫描失败信息"""
        update_stats(None)
        show_hint("统计失败")
        status_text.value = "统计失败"
        set_busy(False)
        page.update()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("错误"),
                content=ft.Text(f"统计失败:\n{error}"),
                actions=[ft.FilledButton("确定")],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def scan_worker(directory: str, excludes: set[str]) -> None:
        """后台扫描线程入口"""
        try:
            results = scan_directory(directory, excludes or None)
        except Exception as ex:
            page.run_thread(render_error, str(ex))
        else:
            page.run_thread(render_results, results)

    def start_scan(e) -> None:
        """开始统计"""
        if worker_running():
            toast("正在统计中，请稍候...")
            return

        directory = (dir_edit.value or "").strip()
        if not os.path.isdir(directory):
            show_hint("请选择有效的统计目录")
            status_text.value = "目录无效"
            page.update()
            toast("请选择有效的统计目录")
            return

        set_busy(True)
        update_stats(None)
        show_hint("正在统计，请稍候...")
        status_text.value = "正在统计，请稍候..."
        state["results"] = {}
        table.rows = []
        page.update()

        state["worker"] = threading.Thread(
            target=scan_worker, args=(directory, parse_excludes()), daemon=True
        )
        state["worker"].start()

    # ==================== 导出 ====================

    def make_export_handler(fmt: str):
        """构建导出回调"""

        async def handler(e) -> None:
            if worker_running():
                toast("正在统计中，请稍候...")
                return

            results = state["results"]
            if not results:
                status_text.value = "请先执行统计"
                page.update()
                toast("请先执行统计，再导出结果")
                return

            directory = (dir_edit.value or "").strip()
            if fmt == "word":
                if not os.path.isdir(directory):
                    status_text.value = "统计目录无效，无法导出 Word"
                    page.update()
                    toast("统计目录无效，无法导出 Word")
                    return
                default_name = "codestat.docx"
                extensions = ["docx"]
            elif fmt == "json":
                default_name = "codestat.json"
                extensions = ["json"]
            else:
                default_name = "codestat.csv"
                extensions = ["csv"]

            path = await save_picker.save_file(
                dialog_title="保存导出文件",
                file_name=default_name,
                allowed_extensions=extensions,
            )
            if not path:
                return

            try:
                if fmt == "json":
                    export_json(results, path)
                elif fmt == "csv":
                    export_csv(results, path)
                else:
                    export_word(directory, path, parse_excludes())
                status_text.value = f"已导出到 {path}"
            except Exception as ex:
                status_text.value = f"导出失败: {ex}"
            page.update()

        return handler

    # ==================== 绑定事件 ====================

    def on_dir_changed(e) -> None:
        """目录输入变化时更新「开始统计」按钮视觉状态"""
        if not worker_running():
            set_busy(False)
        page.update()

    dir_edit.on_change = on_dir_changed
    browse_btn.on_click = browse_directory
    scan_btn.on_click = start_scan
    json_btn.on_click = make_export_handler("json")
    csv_btn.on_click = make_export_handler("csv")
    word_btn.on_click = make_export_handler("word")

    set_busy(False)

    # ==================== 界面布局 ====================

    page.add(
        ft.Container(
            expand=True,
            gradient=ft.LinearGradient(
                colors=[BG_TOP, BG_BOTTOM],
                begin=ft.Alignment.TOP_CENTER,
                end=ft.Alignment.BOTTOM_CENTER,
            ),
            content=ft.SafeArea(
                expand=True,
                content=ft.Row(
                    spacing=0,
                    controls=[sidebar, main_area],
                ),
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)
