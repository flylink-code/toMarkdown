"""CustomTkinter GUI for bidirectional document ↔ Markdown conversion."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import Menu, filedialog, messagebox
from typing import Literal

import customtkinter as ctk
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
from tomarkdown.updater import ReleaseInfo, UpdateError, check_for_update, download_and_install

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)

    DND_AVAILABLE = True
except ImportError:
    DnDCTk = ctk.CTk
    DND_AVAILABLE = False

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


def parse_drop_paths(data: str) -> list[str]:
    """Parse file paths from a tkinterdnd2 drop event payload."""
    data = data.strip()
    if not data:
        return []

    paths: list[str] = []
    index = 0
    length = len(data)

    while index < length:
        char = data[index]
        if char == "{":
            end = data.find("}", index + 1)
            if end == -1:
                break
            paths.append(data[index + 1 : end])
            index = end + 1
        elif char.isspace():
            index += 1
        else:
            end = index
            while end < length and not data[end].isspace():
                end += 1
            paths.append(data[index:end])
            index = end

    return paths


class ConverterApp(DnDCTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self.app_state = AppState()
        self._dark_mode = True
        self._row_widgets: list[tuple[FileItem, ctk.CTkLabel, ctk.CTkLabel]] = []
        self._drop_targets: list[object] = []
        self._checking_update = False

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("780x740")
        self.minsize(660, 600)

        self._build_menu()
        self._build_ui()
        self._setup_drag_drop()
        self._sync_mode_ui()

        self.after(1200, lambda: self._check_for_updates(manual=False))

    def _direction(self) -> Direction:
        return self.app_state.direction

    def _output_format(self) -> OutputFormat:
        if self.app_state.direction == "to_md":
            return "md"
        fmt = self.app_state.export_settings.output_format
        return "pdf" if fmt == "pdf" else "docx"

    def _output_ext(self) -> str:
        return f".{self._output_format()}"

    def _refresh_export_summary(self) -> None:
        label = self.app_state.export_settings.format_label()
        if hasattr(self, "export_summary"):
            self.export_summary.configure(text=f"导出格式: {label}")

    def _build_menu(self) -> None:
        menu_bar = Menu(self)

        settings_menu = Menu(menu_bar, tearoff=False)
        settings_menu.add_command(
            label="Markdown 导出设置...",
            command=self._open_export_settings,
        )
        menu_bar.add_cascade(label="设置", menu=settings_menu)

        help_menu = Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="检查更新", command=lambda: self._check_for_updates(manual=True))
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self._show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        self.config(menu=menu_bar)

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
        messagebox.showinfo(
            "关于 toMarkdown",
            f"{APP_TITLE}\n\n"
            "支持：\n"
            "• Word / PDF → Markdown\n"
            "• Markdown → Word (.docx) / PDF\n\n"
            f"版本: v{__version__}",
        )

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.theme_btn = ctk.CTkButton(
            header,
            text="🌙 深色",
            width=90,
            command=self._toggle_theme,
        )
        self.theme_btn.grid(row=0, column=1, sticky="e")

        mode_frame = ctk.CTkFrame(self)
        mode_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        mode_frame.grid_columnconfigure(1, weight=1)
        mode_frame.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(mode_frame, text="转换方向:").grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame,
            values=["文档 → Markdown", "Markdown → 文档"],
            command=self._on_mode_change,
        )
        self.mode_seg.set("文档 → Markdown")
        self.mode_seg.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        self.export_summary = ctk.CTkLabel(mode_frame, text="导出格式: Word (.docx)", anchor="w")
        self.export_settings_btn = ctk.CTkButton(
            mode_frame,
            text="导出设置...",
            width=100,
            command=self._open_export_settings,
        )
        self._refresh_export_summary()

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.input_hint = ctk.CTkLabel(self.input_frame, text="", anchor="w")
        self.input_hint.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        list_header = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        list_header.grid(row=1, column=0, sticky="ew", padx=12)
        list_header.grid_columnconfigure(0, weight=3)
        list_header.grid_columnconfigure(1, weight=1)
        list_header.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(list_header, text="文件名", anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(list_header, text="大小", anchor="w").grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(list_header, text="状态", anchor="w").grid(row=0, column=2, sticky="w")

        self.file_list = ctk.CTkScrollableFrame(self.input_frame, height=160)
        self.file_list.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 8))
        self.file_list.grid_columnconfigure(0, weight=3)
        self.file_list.grid_columnconfigure(1, weight=1)
        self.file_list.grid_columnconfigure(2, weight=1)

        btn_row = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkButton(btn_row, text="+ 添加文件", width=110, command=self._add_files).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="+ 添加文件夹", width=110, command=self._add_folder).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="清空", width=80, command=self._clear_files).pack(side="left")

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=8)
        options_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(options_frame, text="输出目录:").grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )

        self.output_entry = ctk.CTkEntry(options_frame, placeholder_text="默认与输入文件同目录")
        self.output_entry.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        ctk.CTkButton(options_frame, text="浏览...", width=80, command=self._browse_output).grid(
            row=0, column=2, padx=12, pady=12
        )

        check_row = ctk.CTkFrame(options_frame, fg_color="transparent")
        check_row.grid(row=1, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 12))

        self.recursive_var = ctk.BooleanVar(value=False)
        self.overwrite_var = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(check_row, text="递归子目录", variable=self.recursive_var).pack(
            side="left", padx=(0, 16)
        )
        ctk.CTkCheckBox(check_row, text="覆盖已有文件", variable=self.overwrite_var).pack(
            side="left"
        )

        action_frame = ctk.CTkFrame(self)
        action_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=8)
        action_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(action_frame, text="0 / 0")
        self.progress_label.grid(row=0, column=0, pady=(12, 4))

        self.progress_bar = ctk.CTkProgressBar(action_frame)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=4)
        self.progress_bar.set(0)

        btn_action_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_action_row.grid(row=2, column=0, pady=(8, 12))

        self.start_btn = ctk.CTkButton(
            btn_action_row,
            text="开始转换",
            width=160,
            height=36,
            command=self._start_conversion,
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.open_output_btn = ctk.CTkButton(
            btn_action_row,
            text="打开输出目录",
            width=120,
            state="disabled",
            command=self._open_output_dir,
        )
        self.open_output_btn.pack(side="left")

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=5, column=0, sticky="nsew", padx=16, pady=(8, 16))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="日志:", anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        self.log_box = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _on_mode_change(self, value: str) -> None:
        new_direction: DirectionChoice = "from_md" if "Markdown →" in value else "to_md"
        if new_direction == self.app_state.direction:
            return

        if self.app_state.files:
            if not messagebox.askyesno(
                "切换方向",
                "切换转换方向将清空当前文件列表，是否继续？",
            ):
                # Revert segmented button
                self.mode_seg.set(
                    "Markdown → 文档"
                    if self.app_state.direction == "from_md"
                    else "文档 → Markdown"
                )
                return
            self.app_state.files.clear()
            self._refresh_file_list()

        self.app_state.direction = new_direction
        self._sync_mode_ui()

    def _sync_mode_ui(self) -> None:
        from_md = self.app_state.direction == "from_md"
        if from_md:
            hint = "输入文件（支持 .md / .markdown"
            if DND_AVAILABLE:
                hint += "，可拖放文件或文件夹到此处）"
            else:
                hint += "）"
            self._refresh_export_summary()
            self.export_summary.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="w")
            self.export_settings_btn.grid(row=1, column=2, padx=(0, 12), pady=(0, 12), sticky="e")
        else:
            hint = "输入文件（支持 .doc / .docx / .pdf"
            if DND_AVAILABLE:
                hint += "，可拖放文件或文件夹到此处）"
            else:
                hint += "）"
            self.export_summary.grid_forget()
            self.export_settings_btn.grid_forget()

        self.input_hint.configure(text=hint)

    def _setup_drag_drop(self) -> None:
        if not DND_AVAILABLE:
            return

        for widget in (self, self.input_frame, self.file_list):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
            widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
            widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)
            self._drop_targets.append(widget)

    def _on_drag_enter(self, _event) -> None:
        if hasattr(self, "input_frame"):
            self.input_frame.configure(border_width=2, border_color="#3B8ED0")

    def _on_drag_leave(self, _event) -> None:
        if hasattr(self, "input_frame"):
            self.input_frame.configure(border_width=0)

    def _unsupported_message(self) -> str:
        if self.app_state.direction == "from_md":
            return "未检测到有效的 .md / .markdown 文件。"
        return "未检测到有效的 .doc / .docx / .pdf 文件。"

    def _on_drop(self, event) -> None:
        if hasattr(self, "input_frame"):
            self.input_frame.configure(border_width=0)

        items = self._paths_to_file_items(parse_drop_paths(event.data))
        if not items:
            messagebox.showinfo("提示", self._unsupported_message())
            return

        self._add_file_items(items)

    def _paths_to_file_items(self, paths: list[str]) -> list[FileItem]:
        direction = self._direction()
        items: list[FileItem] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                found = collect_files(path, recursive=self.recursive_var.get(), direction=direction)
                items.extend(FileItem(src=src, root=path) for src in found)
            elif is_supported_file(path, direction):
                items.append(FileItem(src=path))
        return items

    def _toggle_theme(self) -> None:
        self._dark_mode = not self._dark_mode
        mode = "Dark" if self._dark_mode else "Light"
        ctk.set_appearance_mode(mode)
        self.theme_btn.configure(text="🌙 深色" if self._dark_mode else "☀️ 浅色")

    def _append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _check_for_updates(self, manual: bool) -> None:
        if self._checking_update:
            return
        self._checking_update = True
        threading.Thread(target=self._run_update_check, args=(manual,), daemon=True).start()

    def _run_update_check(self, manual: bool) -> None:
        try:
            release = check_for_update()
        except UpdateError as exc:
            self.after(0, lambda: self._on_update_check_error(manual, exc))
            return
        self.after(0, lambda: self._on_update_check_done(manual, release))

    def _finish_update_check(self) -> None:
        self._checking_update = False

    def _on_update_check_error(self, manual: bool, error: UpdateError) -> None:
        self._finish_update_check()
        if manual:
            messagebox.showerror("检查更新失败", str(error))

    def _on_update_check_done(self, manual: bool, release: ReleaseInfo | None) -> None:
        self._finish_update_check()
        if release is None:
            if manual:
                messagebox.showinfo("检查更新", f"当前已是最新版本 v{__version__}。")
            return
        if messagebox.askyesno(
            "发现新版本",
            f"发现 v{release.version}，当前版本为 v{__version__}。\n\n是否下载并安装更新？",
        ):
            threading.Thread(target=self._run_update_install, args=(release,), daemon=True).start()

    def _run_update_install(self, release: ReleaseInfo) -> None:
        try:
            download_and_install(release)
        except UpdateError as exc:
            self.after(0, lambda: self._on_update_install_error(exc))
            return
        self.after(0, self._on_update_install_done)

    def _on_update_install_error(self, error: UpdateError) -> None:
        messagebox.showerror("安装更新失败", str(error))

    def _on_update_install_done(self) -> None:
        messagebox.showinfo("更新已就绪", "程序关闭后将完成更新并自动重新启动。")
        self.destroy()

    def _refresh_file_list(self) -> None:
        for widget in self.file_list.winfo_children():
            widget.destroy()
        self._row_widgets.clear()

        for row_index, item in enumerate(self.app_state.files):
            size = format_size(item.src.stat().st_size) if item.src.exists() else "—"

            name_label = ctk.CTkLabel(self.file_list, text=item.src.name, anchor="w")
            size_label = ctk.CTkLabel(self.file_list, text=size, anchor="w")
            status_label = ctk.CTkLabel(self.file_list, text=item.status, anchor="w")

            name_label.grid(row=row_index, column=0, sticky="ew", padx=4, pady=2)
            size_label.grid(row=row_index, column=1, sticky="ew", padx=4, pady=2)
            status_label.grid(row=row_index, column=2, sticky="ew", padx=4, pady=2)

            self._row_widgets.append((item, name_label, status_label))

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
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, str(default_out))

        self._refresh_file_list()

    def _file_dialog_types(self) -> list[tuple[str, str]]:
        if self.app_state.direction == "from_md":
            return [
                ("Markdown 文件", "*.md;*.markdown"),
                ("所有文件", "*.*"),
            ]
        return [
            ("支持的文档", "*.doc;*.docx;*.pdf"),
            ("Word 文档", "*.doc;*.docx"),
            ("PDF 文档", "*.pdf"),
            ("所有文件", "*.*"),
        ]

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择文件",
            filetypes=self._file_dialog_types(),
        )
        if not paths:
            return

        direction = self._direction()
        items = [FileItem(src=Path(p)) for p in paths if is_supported_file(Path(p), direction)]
        if not items:
            messagebox.showwarning("提示", self._unsupported_message())
            return

        self._add_file_items(items)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return

        folder_path = Path(folder)
        found = collect_files(
            folder_path,
            recursive=self.recursive_var.get(),
            direction=self._direction(),
        )
        if not found:
            messagebox.showwarning("提示", self._unsupported_message())
            return

        items = [FileItem(src=src, root=folder_path) for src in found]
        self._add_file_items(items)

    def _clear_files(self) -> None:
        self.app_state.files.clear()
        self._refresh_file_list()

    def _browse_output(self) -> None:
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self.app_state.output_dir = Path(folder)
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)

    def _resolve_output_dir(self) -> Path:
        text = self.output_entry.get().strip()
        if text:
            return Path(text)
        if self.app_state.output_dir:
            return self.app_state.output_dir
        if self.app_state.files:
            return self.app_state.files[0].src.parent
        return Path.cwd()

    def _set_converting(self, converting: bool) -> None:
        self.app_state.converting = converting
        state = "disabled" if converting else "normal"
        self.start_btn.configure(state=state)
        self.mode_seg.configure(state=state)
        self.export_settings_btn.configure(state=state)

    def _update_file_status(self, src: Path, status: str) -> None:
        for item, _, status_label in self._row_widgets:
            if item.src.resolve() == src.resolve():
                item.status = status
                status_label.configure(text=status)

    def _start_conversion(self) -> None:
        if self.app_state.converting:
            return

        if not self.app_state.files:
            messagebox.showwarning("提示", "请先添加要转换的文件。")
            return

        if self.app_state.direction == "from_md" and self._output_format() == "pdf":
            # Soft note only once per session would be nicer; keep brief in log.
            self._append_log("ℹ️ PDF 导出需要本机已安装 Microsoft Word 或 LibreOffice。")

        output_dir = self._resolve_output_dir()
        self.app_state.output_dir = output_dir
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, str(output_dir))

        for item in self.app_state.files:
            item.status = "待处理"
        self._refresh_file_list()

        self.progress_bar.set(0)
        self.progress_label.configure(text=f"0 / {len(self.app_state.files)}")
        self.open_output_btn.configure(state="disabled")

        self._set_converting(True)
        thread = threading.Thread(
            target=self._run_conversion,
            args=(output_dir,),
            daemon=True,
        )
        thread.start()

    def _run_conversion(self, output_dir: Path) -> None:
        files = [item.src for item in self.app_state.files]
        input_roots = {item.src: item.root for item in self.app_state.files if item.root}
        direction = self._direction()
        output_format = self._output_format()

        def on_progress(current: int, total: int, src: Path, success: bool, message: str) -> None:
            self.after(0, lambda: self._on_progress(current, total, src, success, message))

        result = convert_batch(
            files,
            output_dir,
            callback=on_progress,
            overwrite=self.overwrite_var.get(),
            input_roots=input_roots,
            direction=direction,
            output_format=output_format,
            export_settings=self.app_state.export_settings if direction == "from_md" else None,
        )

        self.after(0, lambda: self._on_conversion_done(result, output_dir))

    def _on_progress(
        self,
        current: int,
        total: int,
        src: Path,
        success: bool,
        message: str,
    ) -> None:
        self.progress_bar.set(current / total if total else 0)
        self.progress_label.configure(text=f"{current} / {total}")
        out_name = f"{src.stem}{self._output_ext()}"

        if message == "skipped":
            self._update_file_status(src, "已跳过(已存在)")
            self._append_log(
                f"⏭ {src.name} → 输出文件已存在，跳过（勾选「覆盖已有文件」可重新转换）"
            )
            return

        if success:
            self._update_file_status(src, "成功")
            self._append_log(f"✅ {src.name} → {out_name}")
        else:
            self._update_file_status(src, "失败")
            self._append_log(f"❌ {src.name} → {message}")

    def _on_conversion_done(self, result: dict, output_dir: Path) -> None:
        self._set_converting(False)
        self.open_output_btn.configure(state="normal")

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

        messagebox.showinfo("转换完成", summary)

    def _open_output_dir(self) -> None:
        output_dir = self._resolve_output_dir()
        if not output_dir.exists():
            messagebox.showwarning("提示", f"输出目录不存在:\n{output_dir}")
            return

        if sys.platform == "win32":
            os.startfile(output_dir)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(output_dir)], check=False)
        else:
            subprocess.run(["xdg-open", str(output_dir)], check=False)


def run_app() -> None:
    """Launch the GUI application."""
    app = ConverterApp()
    app.mainloop()
