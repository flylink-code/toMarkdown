"""CustomTkinter GUI for Word to Markdown conversion."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from tomarkdown.converter import (
    collect_word_files,
    convert_batch,
    is_supported_word_file,
)

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

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.title("Word → Markdown 转换器")
        self.geometry("760x680")
        self.minsize(640, 560)

        self._build_ui()
        self._setup_drag_drop()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Word → Markdown 转换器",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self.theme_btn = ctk.CTkButton(
            header,
            text="🌙 深色",
            width=90,
            command=self._toggle_theme,
        )
        self.theme_btn.grid(row=0, column=1, sticky="e")

        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=8)
        self.input_frame.grid_columnconfigure(0, weight=1)

        input_hint = "输入文件（支持 .doc / .docx，可拖放文件或文件夹到此处）"
        if not DND_AVAILABLE:
            input_hint = "输入文件（支持 .doc / .docx）"

        ctk.CTkLabel(self.input_frame, text=input_hint, anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

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
        options_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=8)
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
        action_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=8)
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
        log_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(8, 16))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_frame, text="日志:", anchor="w").grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        self.log_box = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

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

    def _on_drop(self, event) -> None:
        if hasattr(self, "input_frame"):
            self.input_frame.configure(border_width=0)

        items = self._paths_to_file_items(parse_drop_paths(event.data))
        if not items:
            messagebox.showinfo("提示", "未检测到有效的 .doc / .docx 文件。")
            return

        self._add_file_items(items)

    def _paths_to_file_items(self, paths: list[str]) -> list[FileItem]:
        items: list[FileItem] = []
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                word_files = collect_word_files(path, recursive=self.recursive_var.get())
                items.extend(FileItem(src=src, root=path) for src in word_files)
            elif is_supported_word_file(path):
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

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 Word 文件",
            filetypes=[
                ("Word 文档", "*.doc;*.docx"),
                ("Word 97-2003", "*.doc"),
                ("Word 2007+", "*.docx"),
                ("所有文件", "*.*"),
            ],
        )
        if not paths:
            return

        items = [FileItem(src=Path(p)) for p in paths if is_supported_word_file(Path(p))]
        if not items:
            messagebox.showwarning("提示", "未选择有效的 .doc / .docx 文件。")
            return

        self._add_file_items(items)

    def _add_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择文件夹")
        if not folder:
            return

        folder_path = Path(folder)
        word_files = collect_word_files(folder_path, recursive=self.recursive_var.get())
        if not word_files:
            messagebox.showwarning("提示", "文件夹中未找到 .doc / .docx 文件。")
            return

        items = [FileItem(src=src, root=folder_path) for src in word_files]
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

        def on_progress(current: int, total: int, src: Path, success: bool, message: str) -> None:
            self.after(0, lambda: self._on_progress(current, total, src, success, message))

        result = convert_batch(
            files,
            output_dir,
            callback=on_progress,
            overwrite=self.overwrite_var.get(),
            input_roots=input_roots,
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

        if message == "skipped":
            self._update_file_status(src, "已跳过")
            self._append_log(f"⏭ {src.name} → 已存在，跳过")
            return

        if success:
            self._update_file_status(src, "成功")
            self._append_log(f"✅ {src.name} → {src.stem}.md")
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
