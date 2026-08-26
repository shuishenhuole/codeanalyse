"""
GUI 主程序

该模块实现 CodeStat 的图形界面，使用 PySide6 (Qt) 构建。

界面布局:
    1. 顶部: 目录选择 + 排除项配置 + 扫描按钮
    2. 中部: 统计结果表格
    3. 底部: 导出按钮 (JSON / CSV / Word) + 状态栏

后台扫描使用 QThread，避免大目录扫描时界面卡顿。
"""

import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import scan_directory
from ..exporters import export_csv, export_json, export_word


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
        self.resize(900, 600)

        self.worker: ScanWorker | None = None

        self._init_ui()

    def _init_ui(self) -> None:
        """构建界面"""
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        # ==================== 顶部: 配置区域 ====================

        # 目录选择行
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("统计目录:"))
        self.dir_edit = QLineEdit(os.getcwd())
        self.dir_edit.setPlaceholderText("选择要统计的目录")
        dir_layout.addWidget(self.dir_edit, stretch=1)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_directory)
        dir_layout.addWidget(browse_btn)

        scan_btn = QPushButton("开始统计")
        scan_btn.clicked.connect(self._start_scan)
        dir_layout.addWidget(scan_btn)

        root_layout.addLayout(dir_layout)

        # 排除项输入行
        exclude_layout = QHBoxLayout()
        exclude_layout.addWidget(QLabel("排除项:"))
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("用空格分隔，例如: test docs dist")
        exclude_layout.addWidget(self.exclude_edit, stretch=1)
        root_layout.addLayout(exclude_layout)

        # ==================== 中部: 结果表格 ====================

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["语言", "文件数", "代码行", "注释行", "空行", "总行数"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root_layout.addWidget(self.table, stretch=1)

        # ==================== 底部: 导出区域 ====================

        export_layout = QHBoxLayout()
        export_layout.addStretch(1)

        json_btn = QPushButton("导出 JSON")
        json_btn.clicked.connect(lambda: self._export("json"))
        export_layout.addWidget(json_btn)

        csv_btn = QPushButton("导出 CSV")
        csv_btn.clicked.connect(lambda: self._export("csv"))
        export_layout.addWidget(csv_btn)

        word_btn = QPushButton("导出 Word")
        word_btn.clicked.connect(lambda: self._export("word"))
        export_layout.addWidget(word_btn)

        root_layout.addLayout(export_layout)

        # ==================== 状态栏 ====================

        self.statusBar().showMessage("就绪")

        self._results = {}

    # ==================== 事件处理 ====================

    def _browse_directory(self) -> None:
        """弹出目录选择对话框"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择统计目录", self.dir_edit.text()
        )
        if directory:
            self.dir_edit.setText(directory)

    def _parse_excludes(self) -> set[str]:
        """解析排除项输入"""
        text = self.exclude_edit.text().strip()
        if not text:
            return set()
        return set(text.split())

    def _start_scan(self) -> None:
        """开始统计"""
        directory = self.dir_edit.text().strip()
        if not os.path.isdir(directory):
            QMessageBox.warning(self, "提示", "请选择有效的统计目录")
            return

        if self.worker is not None and self.worker.isRunning():
            return

        self.statusBar().showMessage("正在统计，请稍候...")
        self._results = {}

        self.worker = ScanWorker(directory, self._parse_excludes())
        self.worker.finished.connect(self._on_scan_finished)
        self.worker.failed.connect(self._on_scan_failed)
        self.worker.start()

    def _on_scan_finished(self, results: dict) -> None:
        """扫描完成，填充表格"""
        self._results = results

        if not results:
            self.table.setRowCount(0)
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

        # 总计行
        total_row = len(sorted_items)
        self._set_cell(total_row, 0, "总计")
        self._set_cell(total_row, 1, str(total_files))
        self._set_cell(total_row, 2, str(total_code))
        self._set_cell(total_row, 3, str(total_comment))
        self._set_cell(total_row, 4, str(total_blank))
        self._set_cell(total_row, 5, str(total_lines))

        self.statusBar().showMessage(
            f"统计完成: 共 {total_files} 个文件, {total_lines} 行"
        )

    def _set_cell(self, row: int, col: int, text: str) -> None:
        """写入表格单元格"""
        item = QTableWidgetItem(text)
        if col > 0:
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, col, item)

    def _on_scan_failed(self, error: str) -> None:
        """扫描失败"""
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
