"""
Flet 图形界面主程序

该模块实现 CodeStat 的桌面界面，使用 Flet 构建，风格为「深色极简 + 蓝色强调 + 数据优先」，
贴近现代 IDE 工具面板：紧凑、清晰、有秩序。

设计规范:
    - 页面底色 #111318，侧边栏 #171A21，卡片 #1B202A，分割线 #2A303D，强调色 #5685FF
    - 统计数值接近白色、大字号突出数据；卡片降低高度、减少空白
    - 浏览按钮整合进目录输入框；排除项带示例提示
    - 底部固定状态栏展示运行状态与支持语言数量
    - 圆角分级：面板 13px / 统计卡片 11px / 输入框与按钮 8px，细边框低描边
    - 8px 间距体系

后台扫描使用 threading.Thread，结果通过 page.run_thread 回主线程更新界面。
"""

import os
import re
import threading

import flet as ft

from codestat.core import scan_directory
from codestat.exporters import export_csv, export_json, export_word

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

TABLE_COLUMNS = ["语言", "文件数", "代码行", "注释行", "空行", "总行数"]

# 输入框边框 (默认/聚焦两态)
FIELD_BORDER = {
    ft.ControlState.DEFAULT: ft.OutlineInputBorder(
        border_radius=8, side=ft.BorderSide(1, DIVIDER)
    ),
    ft.ControlState.FOCUSED: ft.OutlineInputBorder(
        border_radius=8, side=ft.BorderSide(1.5, PRIMARY_COLOR)
    ),
}


def _dark_text_field(
    hint_text: str,
    prefix_icon: str,
    value: str = "",
    suffix: ft.Control | None = None,
    helper_text: str | None = None,
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
        expand=True,
    )


def _section_label(text: str) -> ft.Text:
    """侧边栏小节标题 (小号灰色)"""
    return ft.Text(text, size=11, weight=ft.FontWeight.BOLD, color=SUBTEXT_COLOR)


def _stat_tile(kind: str, label: str, icon: str) -> tuple[ft.Control, ft.Text]:
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


def _export_button(label: str, icon: str, key: str) -> ft.TextButton:
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


def _group_divider() -> ft.Container:
    """导出按钮组内的细分隔线"""
    return ft.Container(width=1, height=20, bgcolor=DIVIDER)


def main(page: ft.Page):
    """Flet 应用主入口"""
    page.title = "CodeStat - 代码量统计工具"
    page.window.icon = "assets/icon.png"
    page.width = 1160
    page.height = 780
    page.bgcolor = BG_COLOR
    page.theme = ft.Theme(
        color_scheme_seed=PRIMARY_COLOR, font_family="Microsoft YaHei UI"
    )
    page.padding = 0

    # ==================== 状态 ====================

    state = {"results": {}, "worker": None}

    # ==================== 轻提示 (SnackBar) ====================

    snack_text = ft.Text("", size=13, color=BG_COLOR)
    snack = ft.SnackBar(snack_text, duration=2500, bgcolor="#E5EAF3")
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

    browse_btn = ft.IconButton(
        ft.Icons.FOLDER_OPEN,
        icon_size=18,
        icon_color=SUBTEXT_COLOR,
        tooltip="浏览目录",
        style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
    )
    dir_edit = _dark_text_field(
        "选择要统计的目录", ft.Icons.PUBLIC, value=os.getcwd(), suffix=browse_btn
    )
    exclude_edit = _dark_text_field(
        "目录名/文件名/后缀",
        ft.Icons.BLOCK,
        helper_text="示例: test docs dist *.min.js，空格或逗号分隔",
    )

    scan_btn = ft.FilledButton(
        "开始统计",
        icon=ft.Icons.PLAY_ARROW_ROUNDED,
        key="scan",
        expand=True,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: PRIMARY_COLOR,
                ft.ControlState.HOVERED: PRIMARY_HOVER,
            },
            color="#FFFFFF",
            icon_color="#FFFFFF",
            elevation=0,
            padding=ft.Padding(16, 12, 16, 12),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
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

    sidebar = ft.Container(
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
                                ft.Text("CodeStat", key="title", size=17,
                                        weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                                ft.Text("代码规模分析工具", size=11.5, color=SUBTEXT_COLOR),
                            ],
                        ),
                    ],
                ),
                _section_label("统计目录"),
                dir_edit,
                _section_label("排除规则"),
                exclude_edit,
                ft.Row(spacing=8, controls=[scan_btn]),
                ft.Container(expand=True),
                status_bar,
            ],
        ),
    )

    # ==================== 概览统计卡片 ====================

    files_tile, stat_files = _stat_tile("files", "文件总数", ft.Icons.DESCRIPTION)
    code_tile, stat_code = _stat_tile("code", "代码行数", ft.Icons.CODE)
    comment_tile, stat_comment = _stat_tile("comment", "注释行数", ft.Icons.COMMENT)
    blank_tile, stat_blank = _stat_tile("blank", "空行数", ft.Icons.BLUR_CIRCULAR)

    # ==================== 结果表格 (行式栅格，自动铺满宽度) ====================

    def _grid_row(values: list[str], *, header: bool = False, bold: bool = False,
                  bgcolor: str | None = None) -> ft.Container:
        """构建一行栅格：首列语言占 2 份，其余数值列各占 1 份"""
        cells = []
        for j, v in enumerate(values):
            numeric = j > 0
            cells.append(
                ft.Container(
                    content=ft.Text(
                        v,
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

    rows_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    header_row = _grid_row(TABLE_COLUMNS, header=True)

    hint_text = ft.Text(
        "选择一个项目目录，开始分析代码规模", size=14, color=SUBTEXT_COLOR
    )
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
                    "统计完成后可导出 JSON / CSV / Word",
                    size=12, color=MUTED_COLOR,
                ),
            ],
        ),
        alignment=ft.Alignment.CENTER,
        expand=True,
    )

    table_scroll = ft.Container(
        content=ft.Column(
            spacing=0,
            controls=[header_row, rows_column],
        ),
        expand=True,
        visible=False,
    )

    export_buttons = [
        _export_button("JSON", ft.Icons.DOWNLOAD, "export-json"),
        _export_button("CSV", ft.Icons.DOWNLOAD, "export-csv"),
        _export_button("Word", ft.Icons.MENU_BOOK, "export-word"),
    ]
    json_btn, csv_btn, word_btn = export_buttons

    export_group = ft.Container(
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                json_btn, _group_divider(),
                csv_btn, _group_divider(),
                word_btn,
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
                                ft.Text("统计结果", size=18, weight=ft.FontWeight.W_500,
                                        color=TEXT_COLOR),
                                ft.Text("项目文件明细 · 按语言查看代码行数与注释分布",
                                        size=12, color=MUTED_COLOR),
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

    main_area = ft.Container(
        content=ft.Column(
            spacing=16,
            expand=True,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text("统计概览", size=22, weight=ft.FontWeight.W_600,
                                color=TEXT_COLOR),
                        ft.Text("分析项目代码规模，快速了解代码分布", size=12.5,
                                color=MUTED_COLOR),
                    ],
                ),
                ft.Row(spacing=16, controls=[files_tile, code_tile, comment_tile, blank_tile]),
                results_card,
            ],
        ),
        expand=True,
        padding=ft.Padding(24, 20, 24, 16),
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
        """更新概览统计卡片数值 (未统计时显示弱化占位 0)"""
        values = ["0"] * 4 if totals is None else [f"{int(t):,}" for t in totals[:4]]
        color = MUTED_COLOR if totals is None else VALUE_COLOR
        for value, text in zip(
            (stat_files, stat_code, stat_comment, stat_blank), values, strict=True
        ):
            value.value = text
            value.color = color

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
                name, _format_number(count), _format_number(stats.code),
                _format_number(stats.comment), _format_number(stats.blank),
                _format_number(stats.total),
            ]
            totals[0] += count
            totals[1] += stats.code
            totals[2] += stats.comment
            totals[3] += stats.blank
            totals[4] += stats.total
            stripe = ft.Colors.with_opacity(0.025, "#FFFFFF") if i % 2 == 1 else None
            rows.append(_grid_row(values, bgcolor=stripe))

        rows.append(
            _grid_row(
                ["总计", *[_format_number(t) for t in totals]],
                bold=True,
                bgcolor=ft.Colors.with_opacity(0.12, PRIMARY_COLOR),
            )
        )
        rows_column.controls = rows

        update_stats(totals)
        empty_view.visible = False
        table_scroll.visible = True
        status_text.value = f"统计完成: 共 {totals[0]:,} 个文件, {totals[4]:,} 行"
        set_busy(False)
        page.update()

    def _format_number(n: int) -> str:
        """千分位格式化"""
        return f"{n:,}"

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
        rows_column.controls.clear()
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
        ft.SafeArea(
            expand=True,
            content=ft.Row(
                spacing=0,
                controls=[sidebar, main_area],
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)
