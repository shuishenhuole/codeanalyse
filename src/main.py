"""
Flet 图形界面主程序

该模块实现 CodeStat 的桌面界面，使用 Flet 构建。

界面布局:
    1. 顶部: 应用标题区域
    2. 配置卡片: 目录选择 + 排除项 + 开始统计
    3. 中部: 统计结果表格
    4. 底部: 统计摘要 + 进度指示 + 导出按钮

后台扫描使用 threading.Thread，结果通过 page.run_thread 回主线程更新界面。
"""

import os
import re
import threading

import flet as ft

from codestat.core import scan_directory
from codestat.exporters import export_csv, export_json, export_word

# ==================== 主题配色 ====================

BG_COLOR = "#F4F6FB"
CARD_COLOR = "#FFFFFF"
BORDER_COLOR = "#E4E7F0"
TEXT_COLOR = "#1F2430"
HINT_COLOR = "#8A90A0"
PRIMARY_COLOR = "#4F6DF5"
JSON_COLOR = "#34C759"
CSV_COLOR = "#FF9F0A"
WORD_COLOR = "#0A84FF"

TABLE_COLUMNS = ["语言", "文件数", "代码行", "注释行", "空行", "总行数"]


def _card(content: list[ft.Control]) -> ft.Container:
    """构建带圆角边框和阴影的卡片容器"""
    return ft.Container(
        content=ft.Column(content, spacing=12),
        bgcolor=CARD_COLOR,
        border=ft.Border.all(1, ft.Colors.with_opacity(1.0, BORDER_COLOR)),
        border_radius=12,
        padding=20,
        shadow=ft.BoxShadow(
            blur_radius=20,
            spread_radius=0,
            offset=ft.Offset(0, 3),
            color=ft.Colors.with_opacity(0.12, "#1E2850"),
        ),
    )


def main(page: ft.Page):
    """Flet 应用主入口"""
    page.title = "CodeStat - 代码量统计工具"
    page.window.icon = "assets/icon.png"
    page.width = 1024
    page.height = 720
    page.bgcolor = BG_COLOR
    page.theme = ft.Theme(color_scheme_seed=PRIMARY_COLOR)
    page.padding = 0

    # ==================== 状态 ====================

    state = {"results": {}, "worker": None}

    # ==================== 文件选择器 ====================

    dir_picker = ft.FilePicker()
    save_picker = ft.FilePicker()
    page.services.append(dir_picker)
    page.services.append(save_picker)

    # ==================== 控件定义 ====================

    dir_edit = ft.TextField(
        value=os.getcwd(),
        hint_text="选择要统计的目录",
        expand=True,
        border_radius=8,
        bgcolor="#F8F9FE",
    )

    exclude_edit = ft.TextField(
        hint_text="用空格或逗号分隔，可填目录名/文件名/后缀，例如: tests, md, py",
        expand=True,
        border_radius=8,
        bgcolor="#F8F9FE",
    )

    summary_text = ft.Text(
        "请选择目录后点击「开始统计」",
        weight=ft.FontWeight.BOLD,
        color="#2A3F8F",
        expand=True,
    )

    status_text = ft.Text("就绪", size=12, color=HINT_COLOR)

    progress = ft.ProgressRing(width=22, height=22, visible=False)

    table = ft.DataTable(
        columns=[ft.DataColumn(ft.Text(name)) for name in TABLE_COLUMNS],
        rows=[],
        bgcolor=CARD_COLOR,
        border_radius=8,
        column_spacing=32,
        heading_text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
    )

    scan_btn = ft.FilledButton("开始统计", key="scan", disabled=True)
    browse_btn = ft.FilledButton("浏览...", icon=ft.Icons.FOLDER_OPEN)

    json_btn = ft.FilledButton(
        "导出 JSON",
        key="export-json",
        disabled=True,
        style=ft.ButtonStyle(bgcolor=JSON_COLOR),
    )
    csv_btn = ft.FilledButton(
        "导出 CSV",
        key="export-csv",
        disabled=True,
        style=ft.ButtonStyle(bgcolor=CSV_COLOR),
    )
    word_btn = ft.FilledButton(
        "导出 Word",
        key="export-word",
        disabled=True,
        style=ft.ButtonStyle(bgcolor=WORD_COLOR),
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

    def set_busy(busy: bool) -> None:
        """切换扫描期间的控件可用状态"""
        scan_btn.disabled = busy or not os.path.isdir((dir_edit.value or "").strip())
        browse_btn.disabled = busy
        progress.visible = busy
        export_enabled = not busy and bool(state["results"])
        for btn in (json_btn, csv_btn, word_btn):
            btn.disabled = not export_enabled

    def cell(text: str, numeric: bool = False, bold: bool = False) -> ft.DataCell:
        """构建表格单元格"""
        return ft.DataCell(
            ft.Text(
                text,
                text_align=ft.TextAlign.RIGHT if numeric else ft.TextAlign.START,
                weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL,
            )
        )

    # ==================== 事件处理 ====================

    def on_dir_picked(path: str | None) -> None:
        """目录选择完成回调"""
        if path:
            dir_edit.value = path
        set_busy(bool(state["worker"]) and state["worker"].is_alive())
        page.update()

    async def _browse_directory(e) -> None:
        """弹出目录选择对话框"""
        path = await dir_picker.get_directory_path(
            dialog_title="选择统计目录",
            initial_directory=(dir_edit.value or os.getcwd()).strip(),
        )
        on_dir_picked(path)

    def make_cell_row(row_values: list[str], bold: bool = False) -> ft.DataRow:
        """构建一行表格数据 (首列左对齐，其余右对齐)"""
        return ft.DataRow(
            cells=[
                cell(v, numeric=i > 0, bold=bold) for i, v in enumerate(row_values)
            ]
        )

    def render_results(results: dict) -> None:
        """渲染统计结果到表格"""
        state["results"] = results

        if not results:
            table.rows = []
            summary_text.value = "未找到可统计的代码文件"
            status_text.value = "未找到可统计的代码文件"
            set_busy(False)
            page.update()
            return

        # 按代码行数降序排列
        sorted_items = sorted(results.items(), key=lambda x: x[1][1].code, reverse=True)

        rows = []
        totals = [0, 0, 0, 0, 0]
        for name, (count, stats) in sorted_items:
            values = [name, str(count), str(stats.code), str(stats.comment), str(stats.blank), str(stats.total)]
            for i, v in enumerate(values[1:]):
                totals[i] += int(v)
            rows.append(make_cell_row(values))

        rows.append(
            make_cell_row(["总计", *[str(t) for t in totals]], bold=True)
        )
        table.rows = rows

        summary_text.value = (
            f"共 {totals[0]} 个文件 · {totals[1]} 行代码 · {totals[2]} 行注释 · {totals[3]} 行空行"
        )
        status_text.value = f"统计完成: 共 {totals[0]} 个文件, {totals[4]} 行"
        set_busy(False)
        page.update()

    def render_error(error: str) -> None:
        """渲染扫描失败信息"""
        summary_text.value = "统计失败"
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

    def _scan_worker(directory: str, excludes: set[str]) -> None:
        """后台扫描线程入口"""
        try:
            results = scan_directory(directory, excludes or None)
        except Exception as ex:
            page.run_thread(render_error, str(ex))
        else:
            page.run_thread(render_results, results)

    def _start_scan(e) -> None:
        """开始统计"""
        directory = (dir_edit.value or "").strip()
        if not os.path.isdir(directory):
            summary_text.value = "请选择有效的统计目录"
            status_text.value = "目录无效"
            page.update()
            return

        worker = state["worker"]
        if worker is not None and worker.is_alive():
            return

        scan_btn.disabled = True
        browse_btn.disabled = True
        for btn in (json_btn, csv_btn, word_btn):
            btn.disabled = True
        progress.visible = True
        summary_text.value = "正在统计，请稍候..."
        status_text.value = "正在统计，请稍候..."
        state["results"] = {}
        table.rows = []
        page.update()

        state["worker"] = threading.Thread(
            target=_scan_worker, args=(directory, parse_excludes()), daemon=True
        )
        state["worker"].start()

    # ==================== 导出 ====================

    def _export(fmt: str):
        """导出统计结果 (返回异步回调)"""

        async def handler(e) -> None:
            results = state["results"]
            if not results:
                status_text.value = "请先执行统计"
                page.update()
                return

            directory = (dir_edit.value or "").strip()
            if fmt == "word":
                if not os.path.isdir(directory):
                    status_text.value = "统计目录无效，无法导出 Word"
                    page.update()
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
        """目录输入变化时更新「开始统计」按钮状态"""
        if not scan_btn.disabled or not state["worker"]:
            scan_btn.disabled = not os.path.isdir((e.control.value or "").strip())
        page.update()

    dir_edit.on_change = on_dir_changed
    browse_btn.on_click = _browse_directory
    scan_btn.on_click = _start_scan
    json_btn.on_click = _export("json")
    csv_btn.on_click = _export("csv")
    word_btn.on_click = _export("word")

    # ==================== 界面布局 ====================

    page.add(
        ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding(24, 20, 24, 16),
                content=ft.Column(
                    spacing=16,
                    expand=True,
                    controls=[
                        ft.Text("CodeStat", key="title", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("代码量统计工具 · 支持 40+ 种编程语言", size=12, color=HINT_COLOR),
                        _card(
                            [
                                ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Text("统计目录", weight=ft.FontWeight.BOLD, width=64),
                                        dir_edit,
                                        browse_btn,
                                        scan_btn,
                                    ],
                                ),
                                ft.Row(
                                    spacing=12,
                                    controls=[
                                        ft.Text("排除项", weight=ft.FontWeight.BOLD, width=64),
                                        exclude_edit,
                                    ],
                                ),
                            ]
                        ),
                        ft.Container(
                            expand=True,
                            content=ft.Column(
                                scroll=ft.ScrollMode.AUTO,
                                controls=[table],
                            ),
                        ),
                        ft.Row(
                            spacing=12,
                            controls=[
                                summary_text,
                                progress,
                                json_btn,
                                csv_btn,
                                word_btn,
                            ],
                        ),
                        ft.Container(
                            content=status_text,
                            padding=ft.Padding(4, 0, 4, 0),
                        ),
                    ],
                ),
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)
