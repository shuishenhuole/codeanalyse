"""
GUI 主程序

该模块实现 CodeStat 的图形界面，使用 PySide6 (Qt) 构建。

界面布局:
    1. 顶部: 应用标题区域
    2. 配置卡片: 目录选择 + 排除项 + 开始统计
    3. 中部: 统计结果表格
    4. 底部: 统计摘要 + 导出按钮 + 进度条

后台扫描使用 QThread，避免大目录扫描时界面卡顿。
界面通过 QSS 样式表实现现代化浅色主题。
"""

import os
import re

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import scan_directory
from ..exporters import export_csv, export_json, export_word

# ==================== 主题样式 ====================

STYLE_SHEET = """
QMainWindow {
    background-color: #F4F6FB;
}

* {
    font-family: "Noto Sans SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #1F2430;
}

#titleLabel {
    font-size: 24px;
    font-weight: 700;
    background: transparent;
}

#subtitleLabel {
    font-size: 12px;
    color: #8A90A0;
    background: transparent;
}

QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E4E7F0;
    border-radius: 12px;
}

QLabel {
    background: transparent;
}

#fieldLabel {
    font-weight: 600;
}

QLineEdit {
    background-color: #F8F9FE;
    border: 1px solid #E4E7F0;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #4F6DF5;
}
QLineEdit:focus {
    border: 1px solid #4F6DF5;
    background-color: #FFFFFF;
}

QPushButton {
    background-color: #F0F2FA;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #E3E7F7;
}
QPushButton:pressed {
    background-color: #D6DBF0;
}
QPushButton:disabled {
    background-color: #E9EBF0;
    color: #A0A5B0;
}

#primaryBtn {
    background-color: #4F6DF5;
    color: #FFFFFF;
    padding: 8px 24px;
}
#primaryBtn:hover {
    background-color: #3D5BE0;
}
#primaryBtn:pressed {
    background-color: #324CC9;
}

#exportJsonBtn {
    background-color: #34C759;
    color: #FFFFFF;
}
#exportJsonBtn:hover {
    background-color: #2AB34F;
}

#exportCsvBtn {
    background-color: #FF9F0A;
    color: #FFFFFF;
}
#exportCsvBtn:hover {
    background-color: #E88F06;
}

#exportWordBtn {
    background-color: #0A84FF;
    color: #FFFFFF;
}
#exportWordBtn:hover {
    background-color: #0872E0;
}

QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E4E7F0;
    border-radius: 8px;
    gridline-color: #EEF0F8;
    alternate-background-color: #F8F9FE;
    selection-background-color: #4F6DF5;
    selection-color: #FFFFFF;
}
QTableWidget::item {
    padding: 6px 4px;
}

QHeaderView::section {
    background-color: #E9EBF5;
    color: #1F2430;
    border: none;
    border-bottom: 1px solid #D9DCE8;
    padding: 8px;
    font-weight: 600;
}

QProgressBar {
    border: none;
    border-radius: 3px;
    background-color: #E9EBF5;
}
QProgressBar::chunk {
    border-radius: 3px;
    background-color: #4F6DF5;
}

#summaryLabel {
    font-weight: 600;
    color: #2A3F8F;
    background: transparent;
}

QStatusBar {
    background-color: #F4F6FB;
    color: #8A90A0;
}
"""


class ScanWorker(QThread):
    """
    后台扫描线程

    在独立线程中执行 scan_directory，避免阻塞界面。

    信号:
        finished: 扫描完成，携带统计结果
        failed: 扫描失败，携带错误信息
    """

    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, directory: str, extra_excludes: set[str] | None = None):
        super().__init__()
        self.directory = directory
        self.extra_excludes = extra_excludes

    def run(self) -> None:
        try:
            results = scan_directory(self.directory, self.extra_excludes)
            self.finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    """CodeStat 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CodeStat - 代码量统计工具")
        self.resize(1024, 720)
        self.setStyleSheet(STYLE_SHEET)

        self.worker: ScanWorker | None = None
        self._results = {}

        self._init_ui()

    # ==================== 界面构建 ====================

    def _init_ui(self) -> None:
        """构建界面"""
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 20, 24, 16)
        root_layout.setSpacing(16)

        # 标题区域
        title = QLabel("CodeStat")
        title.setObjectName("titleLabel")
        root_layout.addWidget(title)

        subtitle = QLabel("代码量统计工具 · 支持 40+ 种编程语言")
        subtitle.setObjectName("subtitleLabel")
        root_layout.addWidget(subtitle)

        # 配置卡片
        card = QFrame()
        card.setObjectName("card")
        self._add_shadow(card)
        root_layout.addWidget(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        # 目录选择行
        dir_layout = QHBoxLayout()
        dir_label = QLabel("统计目录")
        dir_label.setObjectName("fieldLabel")
        dir_layout.addWidget(dir_label)

        self.dir_edit = QLineEdit(os.getcwd())
        self.dir_edit.setPlaceholderText("选择要统计的目录")
        dir_layout.addWidget(self.dir_edit, stretch=1)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(self.browse_btn)

        self.scan_btn = QPushButton("开始统计")
        self.scan_btn.setObjectName("primaryBtn")
        self.scan_btn.clicked.connect(self._start_scan)
        dir_layout.addWidget(self.scan_btn)

        card_layout.addLayout(dir_layout)

        # 排除项输入行
        exclude_layout = QHBoxLayout()
        exclude_label = QLabel("排除项")
        exclude_label.setObjectName("fieldLabel")
        exclude_layout.addWidget(exclude_label)

        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("用空格或逗号分隔，可填目录名/文件名/后缀，例如: tests, md, py")
        exclude_layout.addWidget(self.exclude_edit, stretch=1)
        card_layout.addLayout(exclude_layout)

        # 结果表格
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["语言", "文件数", "代码行", "注释行", "空行", "总行数"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        root_layout.addWidget(self.table, stretch=1)

        # 底部: 摘要 + 进度条 + 导出按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(12)

        self.summary_label = QLabel("请选择目录后点击「开始统计」")
        self.summary_label.setObjectName("summaryLabel")
        bottom_layout.addWidget(self.summary_label, stretch=1)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        bottom_layout.addWidget(self.progress)

        self.json_btn = QPushButton("导出 JSON")
        self.json_btn.setObjectName("exportJsonBtn")
        self.json_btn.clicked.connect(lambda: self._export("json"))
        bottom_layout.addWidget(self.json_btn)

        self.csv_btn = QPushButton("导出 CSV")
        self.csv_btn.setObjectName("exportCsvBtn")
        self.csv_btn.clicked.connect(lambda: self._export("csv"))
        bottom_layout.addWidget(self.csv_btn)

        self.word_btn = QPushButton("导出 Word")
        self.word_btn.setObjectName("exportWordBtn")
        self.word_btn.clicked.connect(lambda: self._export("word"))
        bottom_layout.addWidget(self.word_btn)

        root_layout.addLayout(bottom_layout)

        self._set_export_enabled(False)
        self.statusBar().showMessage("就绪")

    def _add_shadow(self, widget: QWidget) -> None:
        """为控件添加柔和阴影"""
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(30, 40, 80, 30))
        widget.setGraphicsEffect(shadow)

    # ==================== 事件处理 ====================

    def _browse_directory(self) -> None:
        """弹出目录选择对话框"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择统计目录", self.dir_edit.text()
        )
        if directory:
            self.dir_edit.setText(directory)

    def _parse_excludes(self) -> set[str]:
        """解析排除项输入 (支持空格/逗号/分号分隔，含中文标点)"""
        text = self.exclude_edit.text()
        excludes = set()
        for token in re.split(r"[,，;；\s]+", text):
            token = token.strip().strip("/\\")
            if token:
                excludes.add(token)
        return excludes

    def _set_export_enabled(self, enabled: bool) -> None:
        """切换导出按钮可用状态"""
        self.json_btn.setEnabled(enabled)
        self.csv_btn.setEnabled(enabled)
        self.word_btn.setEnabled(enabled)

    def _start_scan(self) -> None:
        """开始统计"""
        directory = self.dir_edit.text().strip()
        if not os.path.isdir(directory):
            QMessageBox.warning(self, "提示", "请选择有效的统计目录")
            return

        if self.worker is not None and self.worker.isRunning():
            return

        self.scan_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self._set_export_enabled(False)
        self.progress.setVisible(True)
        self.summary_label.setText("正在统计，请稍候...")
        self.statusBar().showMessage("正在统计，请稍候...")
        self._results = {}

        self.worker = ScanWorker(directory, self._parse_excludes())
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.failed.connect(self._on_scan_failed)
        self.worker.start()

    def _on_scan_finished(self, results: dict) -> None:
        """扫描完成，填充表格"""
        self._results = results
        self.scan_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress.setVisible(False)

        if not results:
            self.table.setRowCount(0)
            self.summary_label.setText("未找到可统计的代码文件")
            self.statusBar().showMessage("未找到可统计的代码文件")
            QMessageBox.information(self, "提示", "未找到可统计的代码文件")
            return

        # 按代码行数降序排列
        sorted_items = sorted(results.items(), key=lambda x: x[1][1].code, reverse=True)

        self.table.setRowCount(len(sorted_items) + 1)

        total_files = 0
        total_code = 0
        total_comment = 0
        total_blank = 0
        total_lines = 0

        for row, (name, (count, stats)) in enumerate(sorted_items):
            self._set_cell(row, 0, name)
            self._set_cell(row, 1, str(count))
            self._set_cell(row, 2, str(stats.code))
            self._set_cell(row, 3, str(stats.comment))
            self._set_cell(row, 4, str(stats.blank))
            self._set_cell(row, 5, str(stats.total))

            total_files += count
            total_code += stats.code
            total_comment += stats.comment
            total_blank += stats.blank
            total_lines += stats.total

        # 总计行 (加粗)
        total_row = len(sorted_items)
        self._set_cell(total_row, 0, "总计", bold=True)
        self._set_cell(total_row, 1, str(total_files), bold=True)
        self._set_cell(total_row, 2, str(total_code), bold=True)
        self._set_cell(total_row, 3, str(total_comment), bold=True)
        self._set_cell(total_row, 4, str(total_blank), bold=True)
        self._set_cell(total_row, 5, str(total_lines), bold=True)

        self.summary_label.setText(
            f"共 {total_files} 个文件 · {total_code} 行代码 · {total_comment} 行注释 · {total_blank} 行空行"
        )
        self.statusBar().showMessage(f"统计完成: 共 {total_files} 个文件, {total_lines} 行")
        self._set_export_enabled(True)

    def _set_cell(self, row: int, col: int, text: str, bold: bool = False) -> None:
        """写入表格单元格"""
        item = QTableWidgetItem(text)
        if col > 0:
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        self.table.setItem(row, col, item)

    def _on_scan_failed(self, error: str) -> None:
        """扫描失败"""
        self.scan_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.summary_label.setText("统计失败")
        self.statusBar().showMessage("统计失败")
        QMessageBox.critical(self, "错误", f"统计失败:\n{error}")

    def _export(self, fmt: str) -> None:
        """导出统计结果"""
        if not self._results:
            QMessageBox.warning(self, "提示", "请先执行统计")
            return

        if fmt == "word":
            # Word 导出需要目录路径和排除项
            directory = self.dir_edit.text().strip()
            if not os.path.isdir(directory):
                QMessageBox.warning(self, "提示", "统计目录无效，无法导出 Word")
                return
            default_name = "codestat.docx"
            file_filter = "Word 文档 (*.docx)"
        else:
            ext = "json" if fmt == "json" else "csv"
            default_name = f"codestat.{ext}"
            file_filter = f"{fmt.upper()} 文件 (*.{ext})"

        path, _ = QFileDialog.getSaveFileName(
            self, "保存导出文件", default_name, file_filter
        )
        if not path:
            return

        try:
            if fmt == "json":
                export_json(self._results, path)
            elif fmt == "csv":
                export_csv(self._results, path)
            elif fmt == "word":
                export_word(directory, path, self._parse_excludes())
            self.statusBar().showMessage(f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{e}")


def run_app() -> int:
    """
    GUI 主入口

    创建 QApplication 并启动主窗口。

    返回:
        程序退出码
    """
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_app())
