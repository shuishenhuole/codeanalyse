"""
Flet 应用主入口

负责页面初始化、状态管理、事件绑定与各界面模块的组装。
具体的界面构建已拆分到 codestat.ui 包:
    - theme: 配色与通用控件
    - sidebar: 左侧操作面板
    - main_panel: 右侧统计结果区
    - md2docx_dialog: Markdown 转 Word 对话框

后台扫描使用 threading.Thread，结果通过 page.run_thread 回主线程更新界面。
"""

import os
import re
import threading

import flet as ft

from .core import scan_directory
from .exporters import export_csv, export_json, export_word
from .ui.main_panel import build_main_panel
from .ui.md2docx_dialog import MarkdownToDocxDialog
from .ui.sidebar import build_sidebar
from .ui.theme import BG_COLOR, PRIMARY_COLOR


def main(page: ft.Page) -> None:
    """Flet 应用主入口"""
    page.title = "CodeStat - 代码量统计工具"
    page.window.icon = "assets/icon.png"
    page.width = 1160
    page.height = 780
    page.bgcolor = BG_COLOR
    page.theme = ft.Theme(color_scheme_seed=PRIMARY_COLOR, font_family="Microsoft YaHei UI")
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
    md_picker = ft.FilePicker()
    page.services.append(dir_picker)
    page.services.append(save_picker)
    page.services.append(md_picker)

    # ==================== 界面模块 ====================

    sidebar = build_sidebar(os.getcwd())
    main_panel = build_main_panel()
    json_btn, csv_btn, word_btn = main_panel.export_buttons

    # ==================== 辅助函数 ====================

    def parse_excludes() -> set[str]:
        """解析排除项输入 (支持空格/逗号/分号分隔，含中文标点)"""
        excludes = set()
        for token in re.split(r"[,，;；\s]+", sidebar.exclude_edit.value or ""):
            token = token.strip().strip("/\\")
            if token:
                excludes.add(token)
        return excludes

    def dir_is_valid() -> bool:
        """当前目录输入是否为有效目录"""
        return os.path.isdir((sidebar.dir_edit.value or "").strip())

    def set_busy(busy: bool) -> None:
        """切换扫描期间的控件视觉状态 (不禁用点击，点击时给出提示)"""
        sidebar.scan_btn.opacity = 1.0 if (not busy and dir_is_valid()) else 0.45
        sidebar.browse_btn.opacity = 0.45 if busy else 1.0
        sidebar.progress.visible = busy
        main_panel.set_export_enabled(not busy and bool(state["results"]))

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
            initial_directory=(sidebar.dir_edit.value or os.getcwd()).strip(),
        )
        if path:
            sidebar.dir_edit.value = path
        set_busy(False)
        page.update()

    def render_results(results: dict) -> None:
        """渲染统计结果到表格"""
        state["results"] = results
        totals = main_panel.render(results)

        if totals is None:
            sidebar.status_text.value = "未找到可统计的代码文件"
            set_busy(False)
            page.update()
            return

        sidebar.status_text.value = (
            f"统计完成: 共 {totals[0]:,} 个文件, {totals[4]:,} 行"
        )
        set_busy(False)
        page.update()

    def render_error(error: str) -> None:
        """渲染扫描失败信息"""
        state["results"] = {}
        main_panel.update_stats(None)
        main_panel.show_hint("统计失败")
        sidebar.status_text.value = "统计失败"
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
        except Exception as exc:
            page.run_thread(render_error, str(exc))
        else:
            page.run_thread(render_results, results)

    def start_scan(e) -> None:
        """开始统计"""
        if worker_running():
            toast("正在统计中，请稍候...")
            return

        directory = (sidebar.dir_edit.value or "").strip()
        if not os.path.isdir(directory):
            main_panel.show_hint("请选择有效的统计目录")
            sidebar.status_text.value = "目录无效"
            page.update()
            toast("请选择有效的统计目录")
            return

        set_busy(True)
        main_panel.update_stats(None)
        main_panel.show_hint("正在统计，请稍候...")
        sidebar.status_text.value = "正在统计，请稍候..."
        state["results"] = {}
        main_panel.clear_rows()
        page.update()

        state["worker"] = threading.Thread(
            target=scan_worker,
            args=(directory, parse_excludes()),
            daemon=True,
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
                sidebar.status_text.value = "请先执行统计"
                page.update()
                toast("请先执行统计，再导出结果")
                return

            directory = (sidebar.dir_edit.value or "").strip()
            if fmt == "word":
                if not os.path.isdir(directory):
                    sidebar.status_text.value = "统计目录无效，无法导出 Word"
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
                sidebar.status_text.value = f"已导出到 {path}"
            except Exception as exc:
                sidebar.status_text.value = f"导出失败: {exc}"
            page.update()

        return handler

    # ==================== Markdown 转 Word ====================

    def on_markdown_converted(message: str) -> None:
        """Markdown 转换完成后的状态提示"""
        sidebar.status_text.value = message
        page.update()
        toast(message)

    md_dialog = MarkdownToDocxDialog(
        page=page,
        file_picker=md_picker,
        save_picker=save_picker,
        on_converted=on_markdown_converted,
    )

    # ==================== 绑定事件 ====================

    def on_dir_changed(e) -> None:
        """目录输入变化时更新「开始统计」按钮视觉状态"""
        if not worker_running():
            set_busy(False)
        page.update()

    sidebar.dir_edit.on_change = on_dir_changed
    sidebar.browse_btn.on_click = browse_directory
    sidebar.scan_btn.on_click = start_scan
    sidebar.md2docx_btn.on_click = lambda e: md_dialog.open()
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
                controls=[sidebar.container, main_panel.container],
            ),
        )
    )
