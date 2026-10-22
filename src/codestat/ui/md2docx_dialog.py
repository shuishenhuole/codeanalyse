"""
Markdown 转 Word 对话框

提供 Markdown 文件选择、输出路径选择与转换进度提示。
转换在后台线程中执行，避免大文档阻塞界面。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from ..converters import convert_markdown_to_docx
from .theme import (
    BTN_SECONDARY_TEXT,
    ERROR_COLOR,
    MUTED_COLOR,
    PANEL_BG,
    SUBTEXT_COLOR,
    TEXT_COLOR,
    dark_text_field,
    primary_button_style,
)


class MarkdownToDocxDialog:
    """Markdown 转 Word 对话框控制器"""

    def __init__(
        self,
        page: ft.Page,
        file_picker: ft.FilePicker,
        save_picker: ft.FilePicker,
        on_converted,
    ) -> None:
        self.page = page
        self.file_picker = file_picker
        self.save_picker = save_picker
        self.on_converted = on_converted

        self._last_markdown = ""
        self._last_output = ""
        self._auto_output = True

        self.md_edit: ft.TextField | None = None
        self.out_edit: ft.TextField | None = None
        self.status_text: ft.Text | None = None
        self.convert_btn: ft.FilledButton | None = None

    # ==================== 打开对话框 ====================

    def open(self) -> None:
        """创建并显示对话框"""
        self._build_controls()
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Markdown 转 Word",
                size=18,
                weight=ft.FontWeight.BOLD,
                color=TEXT_COLOR,
            ),
            content=ft.Column(
                spacing=12,
                width=520,
                tight=True,
                controls=[
                    ft.Text(
                        "支持标题、列表、表格、代码块、引用、链接与本地图片。",
                        size=12,
                        color=SUBTEXT_COLOR,
                    ),
                    ft.Text("Markdown 文件", size=11, weight=ft.FontWeight.BOLD,
                            color=SUBTEXT_COLOR),
                    self.md_edit,
                    ft.Text("输出文件", size=11, weight=ft.FontWeight.BOLD,
                            color=SUBTEXT_COLOR),
                    self.out_edit,
                    self.status_text,
                ],
            ),
            actions=[
                ft.TextButton(
                    "取消",
                    on_click=self._cancel,
                    style=ft.ButtonStyle(color=BTN_SECONDARY_TEXT),
                ),
                self.convert_btn,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=PANEL_BG,
        )
        self.page.show_dialog(dialog)

    def _build_controls(self) -> None:
        """每次打开时重建控件，避免控件复用带来的父子关系问题"""
        md_browse_btn = ft.IconButton(
            ft.Icons.FOLDER_OPEN,
            icon_size=18,
            icon_color=SUBTEXT_COLOR,
            tooltip="选择 Markdown 文件",
            style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
            on_click=self._pick_markdown,
        )
        out_browse_btn = ft.IconButton(
            ft.Icons.SAVE_AS,
            icon_size=18,
            icon_color=SUBTEXT_COLOR,
            tooltip="选择输出位置",
            style=ft.ButtonStyle(padding=ft.Padding(4, 4, 4, 4)),
            on_click=self._pick_output,
        )

        self.md_edit = dark_text_field(
            "选择 .md / .markdown 文件",
            ft.Icons.DESCRIPTION,
            value=self._last_markdown,
            suffix=md_browse_btn,
            read_only=True,
            expand=False,
            width=520,
        )
        self.out_edit = dark_text_field(
            "选择 .docx 输出路径",
            ft.Icons.MENU_BOOK,
            value=self._last_output,
            suffix=out_browse_btn,
            read_only=True,
            expand=False,
            width=520,
        )
        self.status_text = ft.Text("", size=12, color=SUBTEXT_COLOR)
        self.convert_btn = ft.FilledButton(
            "开始转换",
            icon=ft.Icons.TRANSFORM,
            style=primary_button_style(),
            on_click=self._convert,
        )

    # ==================== 文件选择 ====================

    async def _pick_markdown(self, e) -> None:
        """选择 Markdown 文件，并自动推导输出路径"""
        files = await self.file_picker.pick_files(
            dialog_title="选择 Markdown 文件",
            allowed_extensions=["md", "markdown"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        if not files:
            return

        path = files[0].path
        if not path:
            self._set_status("无法获取文件路径，请重试", error=True)
            self.page.update()
            return

        self.md_edit.value = path
        if self._auto_output or not (self.out_edit.value or "").strip():
            self.out_edit.value = str(Path(path).with_suffix(".docx"))
            self._auto_output = True

        self._set_status("")
        self.page.update()

    async def _pick_output(self, e) -> None:
        """选择输出文件位置"""
        markdown = (self.md_edit.value or "").strip()
        if markdown:
            initial_directory = str(Path(markdown).parent)
            file_name = Path(markdown).with_suffix(".docx").name
        else:
            initial_directory = None
            file_name = "output.docx"

        path = await self.save_picker.save_file(
            dialog_title="保存 Word 文件",
            initial_directory=initial_directory,
            file_name=file_name,
            allowed_extensions=["docx"],
            file_type=ft.FilePickerFileType.CUSTOM,
        )
        if not path:
            return

        self.out_edit.value = path
        self._auto_output = False
        self._set_status("")
        self.page.update()

    # ==================== 转换 ====================

    async def _convert(self, e) -> None:
        """执行 Markdown 转 Word"""
        markdown = (self.md_edit.value or "").strip()
        output = (self.out_edit.value or "").strip()

        if not markdown:
            self._set_status("请先选择 Markdown 文件", error=True)
            self.page.update()
            return

        md_path = Path(markdown)
        if not md_path.is_file():
            self._set_status("Markdown 文件不存在，请重新选择", error=True)
            self.page.update()
            return

        if not output:
            output = str(md_path.with_suffix(".docx"))
            self.out_edit.value = output

        out_path = Path(output)
        if out_path.suffix.lower() != ".docx":
            out_path = out_path.with_suffix(".docx")
            self.out_edit.value = str(out_path)

        self.convert_btn.disabled = True
        self._set_status("正在转换，请稍候...")
        self.page.update()

        try:
            # 放到线程池执行，避免大文档阻塞 Flet 界面
            warnings: list[str] = []
            result = await asyncio.to_thread(
                convert_markdown_to_docx,
                md_path,
                out_path,
                warnings=warnings,
            )
        except Exception as exc:
            self.convert_btn.disabled = False
            self._set_status(f"转换失败: {exc}", error=True)
            self.page.update()
            return

        self._last_markdown = str(md_path)
        self._last_output = str(result)
        self.convert_btn.disabled = False
        self.page.pop_dialog()

        message = f"已转换 Markdown: {result}"
        if warnings:
            message += f"（{len(warnings)} 张图片未插入，文档内已保留占位提示）"
        self.on_converted(message)

    # ==================== 辅助方法 ====================

    def _set_status(self, message: str, *, error: bool = False) -> None:
        """更新对话框内的状态提示"""
        self.status_text.value = message
        self.status_text.color = ERROR_COLOR if error else MUTED_COLOR

    def _cancel(self, e) -> None:
        """关闭对话框"""
        self.page.pop_dialog()
