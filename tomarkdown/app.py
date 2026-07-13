"""PySide6 GUI for bidirectional document ↔ Markdown conversion."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QDesktopServices, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tomarkdown import __version__
from tomarkdown.converter import (
    Direction,
    OutputFormat,
    collect_files,
    convert_batch,
    is_supported_file,
)
from tomarkdown.export_settings import ExportSettings, load_export_settings
from tomarkdown.settings_dialog import open_export_settings_dialog
from tomarkdown.theme import apply_theme
from tomarkdown.updater import ReleaseInfo, UpdateError, check_for_update, download_and_install

DirectionChoice = Literal["to_md", "from_md"]
APP_TITLE = "文档 ↔ Markdown 转换器"


@dataclass
class FileItem:
    src: Path
    root: Path | None = None
    status: str = "待处理"


@dataclass
class AppState:
    files: list[FileItem] = field(default_factory=list)
    output_dir: Path | None = None
    converting: bool = False
    direction: DirectionChoice = "to_md"
    export_settings: ExportSettings = field(default_factory=load_export_settings)


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


class ConvertWorker(QObject):
    """Runs batch conversion off the UI thread."""

    progress = Signal(int, int, object, bool, str)
    finished = Signal(dict)

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        *,
        overwrite: bool,
        input_roots: dict[Path, Path],
        direction: Direction,
        output_format: OutputFormat,
        export_settings: ExportSettings | None,
    ) -> None:
        super().__init__()
        self._files = files
        self._output_dir = output_dir
        self._overwrite = overwrite
        self._input_roots = input_roots
        self._direction = direction
        self._output_format = output_format
        self._export_settings = export_settings

    @Slot()
    def run(self) -> None:
        def on_progress(current: int, total: int, src: Path, success: bool, message: str) -> None:
            self.progress.emit(current, total, src, success, message)

        result = convert_batch(
            self._files,
            self._output_dir,
            callback=on_progress,
            overwrite=self._overwrite,
            input_roots=self._input_roots,
            direction=self._direction,
            output_format=self._output_format,
            export_settings=self._export_settings,
        )
        self.finished.emit(result)


class UpdateCheckWorker(QObject):
    finished = Signal(object)  # ReleaseInfo | None
    failed = Signal(str)

    @Slot()
    def run(self) -> None:
        try:
            release = check_for_update()
            self.finished.emit(release)
        except UpdateError as exc:
            self.failed.emit(str(exc))


class UpdateInstallWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, release: ReleaseInfo) -> None:
        super().__init__()
        self._release = release

    @Slot()
    def run(self) -> None:
        try:
            download_and_install(self._release)
            self.finished.emit()
        except UpdateError as exc:
            self.failed.emit(str(exc))


class DropFrame(QFrame):
    """Frame that accepts file/folder drops."""

    paths_dropped = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._default_style = ""
        self._active_style = "border: 2px solid #2A82DA;"

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(self._active_style)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001
        self.setStyleSheet(self._default_style)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet(self._default_style)
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(local)
        if paths:
            self.paths_dropped.emit(paths)
        event.acceptProposedAction()


class ConverterApp(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.app_state = AppState()
        self._dark_mode = True
        self._checking_update = False
        self._worker_thread: QThread | None = None
        self._worker: ConvertWorker | None = None

        self.setWindowTitle(APP_TITLE)
        self.resize(820, 760)
        self.setMinimumSize(680, 600)

        self._build_menu()
        self._build_ui()
        self._sync_mode_ui()
        self._apply_current_theme()

        # Delayed auto update check
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1200, lambda: self._check_for_updates(manual=False))

    def _direction(self) -> Direction:
        return self.app_state.direction

    def _output_format(self) -> OutputFormat:
        if self.app_state.direction == "to_md":
            return "md"
        fmt = self.app_state.export_settings.output_format
        return "pdf" if fmt == "pdf" else "docx"

    def _output_ext(self) -> str:
        return f".{self._output_format()}"

    def _build_menu(self) -> None:
        menu = self.menuBar()
        settings_menu = menu.addMenu("设置")
        act_export = QAction("Markdown 导出设置...", self)
        act_export.triggered.connect(self._open_export_settings)
        settings_menu.addAction(act_export)

        help_menu = menu.addMenu("帮助")
        act_update = QAction("检查更新", self)
        act_update.triggered.connect(lambda: self._check_for_updates(manual=True))
        help_menu.addAction(act_update)
        help_menu.addSeparator()
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel(APP_TITLE)
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch(1)
        self.theme_btn = QPushButton("深色")
        self.theme_btn.setFixedWidth(90)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme_btn)
        root.addLayout(header)

        # Mode
        mode_box = QFrame()
        mode_box.setFrameShape(QFrame.Shape.StyledPanel)
        mode_layout = QVBoxLayout(mode_box)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("转换方向:"))
        self.mode_to_md = QRadioButton("文档 → Markdown")
        self.mode_from_md = QRadioButton("Markdown → 文档")
        self.mode_to_md.setChecked(True)
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_to_md)
        self.mode_group.addButton(self.mode_from_md)
        self.mode_to_md.toggled.connect(self._on_mode_toggled)
        self.mode_from_md.toggled.connect(self._on_mode_toggled)
        mode_row.addWidget(self.mode_to_md)
        mode_row.addWidget(self.mode_from_md)
        mode_row.addStretch(1)

        self.export_summary = QLabel("导出格式: Word (.docx)")
        mode_row.addWidget(self.export_summary)

        self.export_settings_btn = QPushButton("配置")
        self.export_settings_btn.setToolTip("Markdown 导出设置（格式 / 样式 / 页眉页脚）")
        self.export_settings_btn.setFixedWidth(72)
        self.export_settings_btn.clicked.connect(self._open_export_settings)
        mode_row.addWidget(self.export_settings_btn)

        mode_layout.addLayout(mode_row)
        root.addWidget(mode_box)
        self._refresh_export_summary()

        # Input / file list
        self.input_frame = DropFrame()
        self.input_frame.paths_dropped.connect(self._on_paths_dropped)
        input_layout = QVBoxLayout(self.input_frame)
        self.input_hint = QLabel()
        input_layout.addWidget(self.input_hint)

        self.file_table = QTableWidget(0, 3)
        self.file_table.setHorizontalHeaderLabels(["文件名", "大小", "状态"])
        self.file_table.horizontalHeader().setStretchLastSection(True)
        self.file_table.setColumnWidth(0, 360)
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.file_table.setMinimumHeight(180)
        input_layout.addWidget(self.file_table)

        btn_row = QHBoxLayout()
        add_files = QPushButton("+ 添加文件")
        add_folder = QPushButton("+ 添加文件夹")
        clear_btn = QPushButton("清空")
        add_files.clicked.connect(self._add_files)
        add_folder.clicked.connect(self._add_folder)
        clear_btn.clicked.connect(self._clear_files)
        btn_row.addWidget(add_files)
        btn_row.addWidget(add_folder)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        input_layout.addLayout(btn_row)
        root.addWidget(self.input_frame)

        # Options
        options = QFrame()
        options.setFrameShape(QFrame.Shape.StyledPanel)
        opt_layout = QVBoxLayout(options)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("输出目录:"))
        self.output_entry = QLineEdit()
        self.output_entry.setPlaceholderText("默认与输入文件同目录")
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_output)
        out_row.addWidget(self.output_entry, 1)
        out_row.addWidget(browse_btn)
        opt_layout.addLayout(out_row)

        check_row = QHBoxLayout()
        self.recursive_cb = QCheckBox("递归子目录")
        self.overwrite_cb = QCheckBox("覆盖已有文件")
        check_row.addWidget(self.recursive_cb)
        check_row.addWidget(self.overwrite_cb)
        check_row.addStretch(1)
        opt_layout.addLayout(check_row)
        root.addWidget(options)

        # Actions
        action = QFrame()
        action.setFrameShape(QFrame.Shape.StyledPanel)
        action_layout = QVBoxLayout(action)
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        action_layout.addWidget(self.progress_bar)

        act_btn_row = QHBoxLayout()
        self.start_btn = QPushButton("开始转换")
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setMinimumWidth(160)
        self.start_btn.clicked.connect(self._start_conversion)
        self.open_output_btn = QPushButton("打开输出目录")
        self.open_output_btn.setEnabled(False)
        self.open_output_btn.clicked.connect(self._open_output_dir)
        act_btn_row.addStretch(1)
        act_btn_row.addWidget(self.start_btn)
        act_btn_row.addWidget(self.open_output_btn)
        act_btn_row.addStretch(1)
        action_layout.addLayout(act_btn_row)
        root.addWidget(action)

        # Log
        log_box = QFrame()
        log_box.setFrameShape(QFrame.Shape.StyledPanel)
        log_layout = QVBoxLayout(log_box)
        log_layout.addWidget(QLabel("日志:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        log_layout.addWidget(self.log_box, 1)
        root.addWidget(log_box, 1)

    def _refresh_export_summary(self) -> None:
        self.export_summary.setText(
            f"导出格式: {self.app_state.export_settings.format_label()}"
        )

    def _open_export_settings(self) -> None:
        def on_saved(settings: ExportSettings) -> None:
            self.app_state.export_settings = settings
            self._refresh_export_summary()
            self._append_log(
                f"已保存 Markdown 导出设置（格式: {settings.format_label()}）。"
            )

        open_export_settings_dialog(
            self,
            settings=self.app_state.export_settings,
            on_saved=on_saved,
        )

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            "关于 toMarkdown",
            f"{APP_TITLE}\n\n"
            "支持：\n"
            "• Word / PDF → Markdown\n"
            "• Markdown → Word (.docx) / PDF\n\n"
            f"界面：PySide6\n版本: v{__version__}",
        )

    def _on_mode_toggled(self, checked: bool) -> None:
        if not checked:
            return
        new_direction: DirectionChoice = "from_md" if self.mode_from_md.isChecked() else "to_md"
        if new_direction == self.app_state.direction:
            return

        if self.app_state.files:
            reply = QMessageBox.question(
                self,
                "切换方向",
                "切换转换方向将清空当前文件列表，是否继续？",
            )
            if reply != QMessageBox.StandardButton.Yes:
                self.mode_to_md.blockSignals(True)
                self.mode_from_md.blockSignals(True)
                if self.app_state.direction == "from_md":
                    self.mode_from_md.setChecked(True)
                else:
                    self.mode_to_md.setChecked(True)
                self.mode_to_md.blockSignals(False)
                self.mode_from_md.blockSignals(False)
                return
            self.app_state.files.clear()
            self._refresh_file_list()

        self.app_state.direction = new_direction
        self._sync_mode_ui()

    def _sync_mode_ui(self) -> None:
        from_md = self.app_state.direction == "from_md"
        if from_md:
            self.input_hint.setText("输入文件（支持 .md / .markdown，可拖放文件或文件夹到此处）")
            self._refresh_export_summary()
            self.export_summary.show()
            self.export_settings_btn.show()
            self.export_settings_btn.setEnabled(not self.app_state.converting)
        else:
            self.input_hint.setText(
                "输入文件（支持 .doc / .docx / .pdf，可拖放文件或文件夹到此处）"
            )
            self.export_summary.hide()
            self.export_settings_btn.hide()

    def _unsupported_message(self) -> str:
        if self.app_state.direction == "from_md":
            return "未检测到有效的 .md / .markdown 文件。"
        return "未检测到有效的 .doc / .docx / .pdf 文件。"

    def _on_paths_dropped(self, paths: list[str]) -> None:
        items = self._paths_to_file_items(paths)
        if not items:
            QMessageBox.information(self, "提示", self._unsupported_message())
            return
        self._add_file_items(items)

    def _paths_to_file_items(self, paths: list[str]) -> list[FileItem]:
        direction = self._direction()
        items: list[FileItem] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                found = collect_files(
                    path, recursive=self.recursive_cb.isChecked(), direction=direction
                )
                items.extend(FileItem(src=src, root=path) for src in found)
            elif is_supported_file(path, direction):
                items.append(FileItem(src=path))
        return items

    def _apply_current_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, dark=self._dark_mode)
        self.theme_btn.setText("深色" if self._dark_mode else "浅色")

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        self._apply_current_theme()

    def _append_log(self, message: str) -> None:
        self.log_box.append(message)

    def _check_for_updates(self, manual: bool) -> None:
        if self._checking_update:
            return
        self._checking_update = True
        thread = QThread(self)
        worker = UpdateCheckWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def on_done(release: object) -> None:
            self._checking_update = False
            thread.quit()
            self._on_update_check_done(manual, release if isinstance(release, ReleaseInfo) else None)

        def on_fail(message: str) -> None:
            self._checking_update = False
            thread.quit()
            if manual:
                QMessageBox.critical(self, "检查更新失败", message)

        worker.finished.connect(on_done)
        worker.failed.connect(on_fail)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_update_check_done(self, manual: bool, release: ReleaseInfo | None) -> None:
        if release is None:
            if manual:
                QMessageBox.information(self, "检查更新", f"当前已是最新版本 v{__version__}。")
            return
        reply = QMessageBox.question(
            self,
            "发现新版本",
            f"发现 v{release.version}，当前版本为 v{__version__}。\n\n是否下载并安装更新？",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        thread = QThread(self)
        worker = UpdateInstallWorker(release)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def on_done() -> None:
            thread.quit()
            QMessageBox.information(self, "更新已就绪", "程序关闭后将完成更新并自动重新启动。")
            self.close()

        def on_fail(message: str) -> None:
            thread.quit()
            QMessageBox.critical(self, "安装更新失败", message)

        worker.finished.connect(on_done)
        worker.failed.connect(on_fail)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _refresh_file_list(self) -> None:
        self.file_table.setRowCount(0)
        for item in self.app_state.files:
            row = self.file_table.rowCount()
            self.file_table.insertRow(row)
            size = format_size(item.src.stat().st_size) if item.src.exists() else "—"
            self.file_table.setItem(row, 0, QTableWidgetItem(item.src.name))
            self.file_table.setItem(row, 1, QTableWidgetItem(size))
            self.file_table.setItem(row, 2, QTableWidgetItem(item.status))

    def _add_file_items(self, new_items: list[FileItem]) -> None:
        existing = {item.src.resolve() for item in self.app_state.files}
        for item in new_items:
            resolved = item.src.resolve()
            if resolved not in existing:
                self.app_state.files.append(item)
                existing.add(resolved)

        if self.app_state.files and self.app_state.output_dir is None:
            default_out = self.app_state.files[0].src.parent
            self.app_state.output_dir = default_out
            self.output_entry.setText(str(default_out))

        self._refresh_file_list()

    def _file_filters(self) -> str:
        if self.app_state.direction == "from_md":
            return "Markdown 文件 (*.md *.markdown);;所有文件 (*.*)"
        return (
            "支持的文档 (*.doc *.docx *.pdf);;"
            "Word 文档 (*.doc *.docx);;"
            "PDF 文档 (*.pdf);;"
            "所有文件 (*.*)"
        )

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择文件", "", self._file_filters())
        if not paths:
            return
        direction = self._direction()
        items = [FileItem(src=Path(p)) for p in paths if is_supported_file(Path(p), direction)]
        if not items:
            QMessageBox.warning(self, "提示", self._unsupported_message())
            return
        self._add_file_items(items)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if not folder:
            return
        folder_path = Path(folder)
        found = collect_files(
            folder_path,
            recursive=self.recursive_cb.isChecked(),
            direction=self._direction(),
        )
        if not found:
            QMessageBox.warning(self, "提示", self._unsupported_message())
            return
        self._add_file_items([FileItem(src=src, root=folder_path) for src in found])

    def _clear_files(self) -> None:
        self.app_state.files.clear()
        self._refresh_file_list()

    def _browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.app_state.output_dir = Path(folder)
            self.output_entry.setText(folder)

    def _resolve_output_dir(self) -> Path:
        text = self.output_entry.text().strip()
        if text:
            return Path(text)
        if self.app_state.output_dir:
            return self.app_state.output_dir
        if self.app_state.files:
            return self.app_state.files[0].src.parent
        return Path.cwd()

    def _set_converting(self, converting: bool) -> None:
        self.app_state.converting = converting
        self.start_btn.setEnabled(not converting)
        self.mode_to_md.setEnabled(not converting)
        self.mode_from_md.setEnabled(not converting)
        if self.app_state.direction == "from_md":
            self.export_settings_btn.setEnabled(not converting)

    def _update_file_status(self, src: Path, status: str) -> None:
        for row, item in enumerate(self.app_state.files):
            if item.src.resolve() == src.resolve():
                item.status = status
                self.file_table.setItem(row, 2, QTableWidgetItem(status))
                break

    def _start_conversion(self) -> None:
        if self.app_state.converting:
            return
        if not self.app_state.files:
            QMessageBox.warning(self, "提示", "请先添加要转换的文件。")
            return

        if self.app_state.direction == "from_md" and self._output_format() == "pdf":
            self._append_log("ℹ️ PDF 导出需要本机已安装 Microsoft Word 或 LibreOffice。")

        output_dir = self._resolve_output_dir()
        self.app_state.output_dir = output_dir
        self.output_entry.setText(str(output_dir))

        for item in self.app_state.files:
            item.status = "待处理"
        self._refresh_file_list()

        self.progress_bar.setValue(0)
        self.progress_label.setText(f"0 / {len(self.app_state.files)}")
        self.open_output_btn.setEnabled(False)
        self._set_converting(True)

        files = [item.src for item in self.app_state.files]
        input_roots = {item.src: item.root for item in self.app_state.files if item.root}
        direction = self._direction()
        output_format = self._output_format()

        thread = QThread(self)
        worker = ConvertWorker(
            files,
            output_dir,
            overwrite=self.overwrite_cb.isChecked(),
            input_roots=input_roots,
            direction=direction,
            output_format=output_format,
            export_settings=self.app_state.export_settings if direction == "from_md" else None,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_conversion_done)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._worker_thread = thread
        self._worker = worker
        thread.start()

    @Slot(int, int, object, bool, str)
    def _on_progress(
        self,
        current: int,
        total: int,
        src: object,
        success: bool,
        message: str,
    ) -> None:
        src_path = Path(src) if not isinstance(src, Path) else src
        self.progress_bar.setValue(int(current / total * 100) if total else 0)
        self.progress_label.setText(f"{current} / {total}")
        out_name = f"{src_path.stem}{self._output_ext()}"

        if message == "skipped":
            self._update_file_status(src_path, "已跳过(已存在)")
            self._append_log(
                f"⏭ {src_path.name} → 输出文件已存在，跳过（勾选「覆盖已有文件」可重新转换）"
            )
            return

        if success:
            self._update_file_status(src_path, "成功")
            self._append_log(f"✅ {src_path.name} → {out_name}")
        else:
            self._update_file_status(src_path, "失败")
            self._append_log(f"❌ {src_path.name} → {message}")

    @Slot(dict)
    def _on_conversion_done(self, result: dict) -> None:
        self._set_converting(False)
        self.open_output_btn.setEnabled(True)

        success_count = result["success_count"]
        failure_count = result["failure_count"]
        skipped_count = result["skipped_count"]
        total = success_count + failure_count + skipped_count

        parts = [f"成功 {success_count}"]
        if failure_count:
            parts.append(f"失败 {failure_count}")
        if skipped_count:
            parts.append(f"跳过 {skipped_count}")

        summary = f"汇总: {' / '.join(parts)} (共 {total} 个文件)"
        self._append_log(f"\n{summary}")
        QMessageBox.information(self, "转换完成", summary)

    def _open_output_dir(self) -> None:
        output_dir = self._resolve_output_dir()
        if not output_dir.exists():
            QMessageBox.warning(self, "提示", f"输出目录不存在:\n{output_dir}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output_dir.resolve())))


def run_app() -> None:
    """Launch the GUI application."""
    # High-DPI friendly defaults
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("toMarkdown")
    app.setOrganizationName("flylink-code")
    apply_theme(app, dark=True)

    window = ConverterApp()
    window.show()
    sys.exit(app.exec())
