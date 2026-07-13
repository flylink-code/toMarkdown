"""Settings dialog for Markdown export options (extensible tabbed UI)."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from tomarkdown.export_settings import (
    PLACEHOLDER_HINT,
    STYLE_PRESET_LABELS,
    ExportSettings,
    load_export_settings,
    normalize_hex_color,
    save_export_settings,
)


class ExportSettingsDialog(ctk.CTkToplevel):
    """Modal dialog for Markdown → document export settings.

    Tabs:
      - 输出设置: export format
      - 样式: heading colors, code block / inline code styling
      - 页眉页脚 / 文档属性: document chrome
    """

    def __init__(
        self,
        master,
        *,
        settings: ExportSettings | None = None,
        on_saved: Callable[[ExportSettings], None] | None = None,
    ) -> None:
        super().__init__(master)

        self._on_saved = on_saved
        self._settings = settings or load_export_settings()
        self._result: ExportSettings | None = None

        self.title("Markdown 导出设置")
        self.geometry("620x580")
        self.minsize(520, 480)
        self.transient(master)
        self.grab_set()
        self.focus_force()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(self)
        self._tabs.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))

        self._tab_output = self._tabs.add("输出设置")
        self._tab_style = self._tabs.add("样式")
        self._tab_header = self._tabs.add("页眉页脚")
        self._tab_props = self._tabs.add("文档属性")

        self._build_output_tab()
        self._build_style_tab()
        self._build_header_footer_tab()
        self._build_properties_tab()
        self._build_buttons()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.after(50, self._center_on_parent)

    def _center_on_parent(self) -> None:
        try:
            self.update_idletasks()
            parent = self.master
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_output_tab(self) -> None:
        tab = self._tab_output
        tab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            tab,
            text="导出格式",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 4))

        ctk.CTkLabel(tab, text="目标格式:").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        self._output_format = ctk.CTkSegmentedButton(
            tab,
            values=["Word (.docx)", "PDF"],
            command=self._on_format_preview,
        )
        self._output_format.set(
            "PDF" if self._settings.output_format == "pdf" else "Word (.docx)"
        )
        self._output_format.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        self._format_hint = ctk.CTkLabel(
            tab,
            text="",
            text_color=("gray40", "gray65"),
            wraplength=480,
            justify="left",
            anchor="w",
        )
        self._format_hint.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 12))
        self._on_format_preview(self._output_format.get())

        ctk.CTkLabel(
            tab,
            text="说明",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        ctk.CTkLabel(
            tab,
            text=(
                "• Word (.docx)：纯本地生成，无需安装 Office。\n"
                "• PDF：先生成 Word，再通过本机 Microsoft Word 或 LibreOffice 转换。\n"
                "• 页眉页脚、文档属性、样式等选项对两种格式均生效。"
            ),
            text_color=("gray40", "gray65"),
            wraplength=500,
            justify="left",
            anchor="w",
        ).grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 12))

    def _on_format_preview(self, value: str) -> None:
        if "PDF" in value:
            self._format_hint.configure(
                text="当前选择：PDF。导出时需要本机已安装 Microsoft Word 或 LibreOffice。"
            )
        else:
            self._format_hint.configure(text="当前选择：Word (.docx)。可直接生成，兼容性最好。")

    def _build_style_tab(self) -> None:
        tab = self._tab_style
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        self._suppress_custom_mark = False

        scroll = ctk.CTkScrollableFrame(tab)
        scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        scroll.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(
            scroll,
            text="风格预设",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))

        row += 1
        ctk.CTkLabel(scroll, text="预设:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        preset_values = [STYLE_PRESET_LABELS[k] for k in ("typora", "github", "classic", "custom")]
        self._style_preset = ctk.CTkOptionMenu(
            scroll,
            values=preset_values,
            command=self._on_preset_change,
            width=180,
        )
        self._style_preset.set(
            STYLE_PRESET_LABELS.get(self._settings.style_preset, STYLE_PRESET_LABELS["custom"])
        )
        self._style_preset.grid(row=row, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        row += 1
        ctk.CTkLabel(
            scroll,
            text="标题颜色",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(14, 4))

        self._heading_h1_color, row = self._add_color_row(
            scroll, row + 1, "H1 颜色:", self._settings.heading_h1_color
        )
        self._heading_h2_color, row = self._add_color_row(
            scroll, row, "H2 颜色:", self._settings.heading_h2_color
        )
        self._heading_h3_color, row = self._add_color_row(
            scroll, row, "H3 颜色:", self._settings.heading_h3_color
        )
        self._heading_color, row = self._add_color_row(
            scroll, row, "H4+ 颜色:", self._settings.heading_color
        )

        ctk.CTkLabel(
            scroll,
            text="代码块",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(14, 4))
        row += 1

        self._code_bg, row = self._add_color_row(scroll, row, "背景色:", self._settings.code_bg)
        self._code_border, row = self._add_color_row(
            scroll, row, "边框色:", self._settings.code_border
        )

        ctk.CTkLabel(scroll, text="字体:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        self._code_font = ctk.CTkEntry(scroll, width=180)
        self._code_font.grid(row=row, column=1, sticky="w", padx=8, pady=6)
        self._code_font.insert(0, self._settings.code_font)
        self._code_font.bind("<KeyRelease>", lambda _e: self._mark_custom_preset())
        row += 1

        ctk.CTkLabel(scroll, text="字号:").grid(row=row, column=0, sticky="w", padx=8, pady=6)
        self._code_font_size = ctk.CTkEntry(scroll, width=80)
        self._code_font_size.grid(row=row, column=1, sticky="w", padx=8, pady=6)
        self._code_font_size.insert(0, str(self._settings.code_font_size))
        self._code_font_size.bind("<KeyRelease>", lambda _e: self._mark_custom_preset())
        row += 1

        self._code_highlight = ctk.BooleanVar(value=self._settings.code_highlight)
        ctk.CTkCheckBox(
            scroll,
            text="语法高亮",
            variable=self._code_highlight,
            command=self._mark_custom_preset,
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        row += 1

        self._code_show_language = ctk.BooleanVar(value=self._settings.code_show_language)
        ctk.CTkCheckBox(
            scroll,
            text="显示语言标签",
            variable=self._code_show_language,
            command=self._mark_custom_preset,
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        row += 1

        ctk.CTkLabel(
            scroll,
            text="行内代码",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(14, 4))
        row += 1

        self._inline_code_fg, row = self._add_color_row(
            scroll, row, "文字色:", self._settings.inline_code_fg
        )
        self._inline_code_bg, row = self._add_color_row(
            scroll, row, "背景色:", self._settings.inline_code_bg
        )

        ctk.CTkLabel(
            scroll,
            text="颜色填写 6 位十六进制，如 1F2328 或 #1F2328。修改任意项将自动切到「自定义」。",
            text_color=("gray40", "gray65"),
            wraplength=500,
            justify="left",
            anchor="w",
        ).grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(12, 8))

    def _add_color_row(
        self,
        parent,
        row: int,
        label: str,
        value: str,
    ) -> tuple[ctk.CTkEntry, int]:
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        entry = ctk.CTkEntry(parent, width=120)
        entry.grid(row=row, column=1, sticky="w", padx=8, pady=4)
        entry.insert(0, value)
        swatch = ctk.CTkFrame(parent, width=28, height=22, corner_radius=4)
        swatch.grid(row=row, column=2, sticky="w", padx=4, pady=4)
        swatch.grid_propagate(False)

        def refresh(_event=None) -> None:
            hex_color = normalize_hex_color(entry.get(), value)
            try:
                swatch.configure(fg_color=f"#{hex_color}")
            except Exception:
                swatch.configure(fg_color=("gray70", "gray40"))
            self._mark_custom_preset()

        entry.bind("<KeyRelease>", refresh)
        entry._color_swatch = swatch  # type: ignore[attr-defined]
        entry._color_default = value  # type: ignore[attr-defined]
        refresh()
        return entry, row + 1

    def _refresh_color_swatch(self, entry: ctk.CTkEntry) -> None:
        default = getattr(entry, "_color_default", "1F2328")
        swatch = getattr(entry, "_color_swatch", None)
        if swatch is None:
            return
        hex_color = normalize_hex_color(entry.get(), default)
        try:
            swatch.configure(fg_color=f"#{hex_color}")
        except Exception:
            swatch.configure(fg_color=("gray70", "gray40"))

    def _preset_key_from_label(self, label: str) -> str:
        for key, text in STYLE_PRESET_LABELS.items():
            if text == label:
                return key
        return "custom"

    def _mark_custom_preset(self) -> None:
        if getattr(self, "_suppress_custom_mark", False):
            return
        if hasattr(self, "_style_preset"):
            self._style_preset.set(STYLE_PRESET_LABELS["custom"])

    def _on_preset_change(self, label: str) -> None:
        key = self._preset_key_from_label(label)
        if key == "custom":
            return
        temp = ExportSettings()
        temp.apply_style_preset(key)
        self._suppress_custom_mark = True
        try:
            self._heading_h1_color.delete(0, "end")
            self._heading_h1_color.insert(0, temp.heading_h1_color)
            self._heading_h2_color.delete(0, "end")
            self._heading_h2_color.insert(0, temp.heading_h2_color)
            self._heading_h3_color.delete(0, "end")
            self._heading_h3_color.insert(0, temp.heading_h3_color)
            self._heading_color.delete(0, "end")
            self._heading_color.insert(0, temp.heading_color)
            self._code_bg.delete(0, "end")
            self._code_bg.insert(0, temp.code_bg)
            self._code_border.delete(0, "end")
            self._code_border.insert(0, temp.code_border)
            self._code_font.delete(0, "end")
            self._code_font.insert(0, temp.code_font)
            self._code_font_size.delete(0, "end")
            self._code_font_size.insert(0, str(temp.code_font_size))
            self._code_highlight.set(temp.code_highlight)
            self._code_show_language.set(temp.code_show_language)
            self._inline_code_fg.delete(0, "end")
            self._inline_code_fg.insert(0, temp.inline_code_fg)
            self._inline_code_bg.delete(0, "end")
            self._inline_code_bg.insert(0, temp.inline_code_bg)
            for entry in (
                self._heading_h1_color,
                self._heading_h2_color,
                self._heading_h3_color,
                self._heading_color,
                self._code_bg,
                self._code_border,
                self._inline_code_fg,
                self._inline_code_bg,
            ):
                self._refresh_color_swatch(entry)
            self._style_preset.set(STYLE_PRESET_LABELS[key])
        finally:
            self._suppress_custom_mark = False

    def _build_header_footer_tab(self) -> None:
        tab = self._tab_header
        tab.grid_columnconfigure(1, weight=1)

        row = 0
        self._header_enabled = ctk.BooleanVar(value=self._settings.header_enabled)
        ctk.CTkCheckBox(tab, text="启用页眉", variable=self._header_enabled).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )

        row += 1
        ctk.CTkLabel(tab, text="页眉内容:").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self._header_text = ctk.CTkTextbox(tab, height=56, wrap="word")
        self._header_text.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self._header_text.insert("1.0", self._settings.header_text)

        row += 1
        ctk.CTkLabel(tab, text="页眉对齐:").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self._header_align = ctk.CTkSegmentedButton(tab, values=["左", "中", "右"])
        self._header_align.set({"left": "左", "center": "中", "right": "右"}.get(
            self._settings.header_align, "中"
        ))
        self._header_align.grid(row=row, column=1, sticky="w", padx=8, pady=4)

        row += 1
        self._footer_enabled = ctk.BooleanVar(value=self._settings.footer_enabled)
        ctk.CTkCheckBox(tab, text="启用页脚", variable=self._footer_enabled).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 4)
        )

        row += 1
        ctk.CTkLabel(tab, text="页脚内容:").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self._footer_text = ctk.CTkTextbox(tab, height=56, wrap="word")
        self._footer_text.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self._footer_text.insert("1.0", self._settings.footer_text)

        row += 1
        ctk.CTkLabel(tab, text="页脚对齐:").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self._footer_align = ctk.CTkSegmentedButton(tab, values=["左", "中", "右"])
        self._footer_align.set({"left": "左", "center": "中", "right": "右"}.get(
            self._settings.footer_align, "中"
        ))
        self._footer_align.grid(row=row, column=1, sticky="w", padx=8, pady=4)

        row += 1
        self._diff_first = ctk.BooleanVar(value=self._settings.different_first_page)
        ctk.CTkCheckBox(tab, text="首页不同", variable=self._diff_first).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(12, 4)
        )

        row += 1
        ctk.CTkLabel(tab, text="首页页眉:").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self._first_header = ctk.CTkEntry(tab)
        self._first_header.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self._first_header.insert(0, self._settings.first_header_text)

        row += 1
        ctk.CTkLabel(tab, text="首页页脚:").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self._first_footer = ctk.CTkEntry(tab)
        self._first_footer.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
        self._first_footer.insert(0, self._settings.first_footer_text)

        row += 1
        ctk.CTkLabel(
            tab,
            text=PLACEHOLDER_HINT,
            text_color=("gray40", "gray65"),
            wraplength=480,
            justify="left",
            anchor="w",
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=(12, 8))

    def _build_properties_tab(self) -> None:
        tab = self._tab_props
        tab.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(tab, text="标题:").grid(row=0, column=0, sticky="w", padx=8, pady=(12, 4))
        self._doc_title = ctk.CTkEntry(tab, placeholder_text="留空则使用首个一级标题或文件名")
        self._doc_title.grid(row=0, column=1, sticky="ew", padx=8, pady=(12, 4))
        self._doc_title.insert(0, self._settings.doc_title)

        ctk.CTkLabel(tab, text="作者:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._doc_author = ctk.CTkEntry(tab)
        self._doc_author.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self._doc_author.insert(0, self._settings.doc_author)

        ctk.CTkLabel(tab, text="主题:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self._doc_subject = ctk.CTkEntry(tab)
        self._doc_subject.grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        self._doc_subject.insert(0, self._settings.doc_subject)

        ctk.CTkLabel(
            tab,
            text="这些信息会写入 Word 文档属性，并可用于页眉/页脚占位符。",
            text_color=("gray40", "gray65"),
            wraplength=480,
            justify="left",
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(16, 8))

    def _build_buttons(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 16))

        ctk.CTkButton(bar, text="恢复默认", width=100, command=self._on_reset).pack(
            side="left"
        )
        ctk.CTkButton(bar, text="取消", width=90, command=self._on_cancel).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(bar, text="保存", width=90, command=self._on_save).pack(side="right")

    @staticmethod
    def _align_value(label: str) -> str:
        return {"左": "left", "中": "center", "右": "right"}.get(label, "center")

    @staticmethod
    def _format_value(label: str) -> str:
        return "pdf" if "PDF" in label else "docx"

    def _collect(self) -> ExportSettings:
        try:
            font_size = float(self._code_font_size.get().strip() or "9.5")
        except ValueError:
            font_size = 9.5
        settings = ExportSettings(
            output_format=self._format_value(self._output_format.get()),
            header_enabled=bool(self._header_enabled.get()),
            header_text=self._header_text.get("1.0", "end").strip(),
            header_align=self._align_value(self._header_align.get()),
            footer_enabled=bool(self._footer_enabled.get()),
            footer_text=self._footer_text.get("1.0", "end").strip(),
            footer_align=self._align_value(self._footer_align.get()),
            different_first_page=bool(self._diff_first.get()),
            first_header_text=self._first_header.get().strip(),
            first_footer_text=self._first_footer.get().strip(),
            doc_title=self._doc_title.get().strip(),
            doc_author=self._doc_author.get().strip(),
            doc_subject=self._doc_subject.get().strip(),
            style_preset=self._preset_key_from_label(self._style_preset.get()),
            heading_color=self._heading_color.get().strip(),
            heading_h1_color=self._heading_h1_color.get().strip(),
            heading_h2_color=self._heading_h2_color.get().strip(),
            heading_h3_color=self._heading_h3_color.get().strip(),
            code_bg=self._code_bg.get().strip(),
            code_border=self._code_border.get().strip(),
            code_font=self._code_font.get().strip(),
            code_font_size=font_size,
            code_highlight=bool(self._code_highlight.get()),
            code_show_language=bool(self._code_show_language.get()),
            inline_code_bg=self._inline_code_bg.get().strip(),
            inline_code_fg=self._inline_code_fg.get().strip(),
        )
        settings.normalize_style_fields()
        return settings

    def _apply_to_form(self, settings: ExportSettings) -> None:
        settings.normalize_style_fields()
        self._output_format.set(settings.format_label())
        self._on_format_preview(self._output_format.get())
        self._header_enabled.set(settings.header_enabled)
        self._header_text.delete("1.0", "end")
        self._header_text.insert("1.0", settings.header_text)
        self._header_align.set({"left": "左", "center": "中", "right": "右"}.get(
            settings.header_align, "中"
        ))
        self._footer_enabled.set(settings.footer_enabled)
        self._footer_text.delete("1.0", "end")
        self._footer_text.insert("1.0", settings.footer_text)
        self._footer_align.set({"left": "左", "center": "中", "right": "右"}.get(
            settings.footer_align, "中"
        ))
        self._diff_first.set(settings.different_first_page)
        self._first_header.delete(0, "end")
        self._first_header.insert(0, settings.first_header_text)
        self._first_footer.delete(0, "end")
        self._first_footer.insert(0, settings.first_footer_text)
        self._doc_title.delete(0, "end")
        self._doc_title.insert(0, settings.doc_title)
        self._doc_author.delete(0, "end")
        self._doc_author.insert(0, settings.doc_author)
        self._doc_subject.delete(0, "end")
        self._doc_subject.insert(0, settings.doc_subject)

        self._suppress_custom_mark = True
        try:
            self._style_preset.set(
                STYLE_PRESET_LABELS.get(settings.style_preset, STYLE_PRESET_LABELS["custom"])
            )
            self._heading_h1_color.delete(0, "end")
            self._heading_h1_color.insert(0, settings.heading_h1_color)
            self._heading_h2_color.delete(0, "end")
            self._heading_h2_color.insert(0, settings.heading_h2_color)
            self._heading_h3_color.delete(0, "end")
            self._heading_h3_color.insert(0, settings.heading_h3_color)
            self._heading_color.delete(0, "end")
            self._heading_color.insert(0, settings.heading_color)
            self._code_bg.delete(0, "end")
            self._code_bg.insert(0, settings.code_bg)
            self._code_border.delete(0, "end")
            self._code_border.insert(0, settings.code_border)
            self._code_font.delete(0, "end")
            self._code_font.insert(0, settings.code_font)
            self._code_font_size.delete(0, "end")
            self._code_font_size.insert(0, str(settings.code_font_size))
            self._code_highlight.set(settings.code_highlight)
            self._code_show_language.set(settings.code_show_language)
            self._inline_code_fg.delete(0, "end")
            self._inline_code_fg.insert(0, settings.inline_code_fg)
            self._inline_code_bg.delete(0, "end")
            self._inline_code_bg.insert(0, settings.inline_code_bg)
            for entry in (
                self._heading_h1_color,
                self._heading_h2_color,
                self._heading_h3_color,
                self._heading_color,
                self._code_bg,
                self._code_border,
                self._inline_code_fg,
                self._inline_code_bg,
            ):
                self._refresh_color_swatch(entry)
        finally:
            self._suppress_custom_mark = False

    def _on_reset(self) -> None:
        self._apply_to_form(ExportSettings())

    def _on_save(self) -> None:
        settings = self._collect()
        save_export_settings(settings)
        self._result = settings
        if self._on_saved:
            self._on_saved(settings)
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.grab_release()
        self.destroy()

    @property
    def result(self) -> ExportSettings | None:
        return self._result


def open_export_settings_dialog(
    master,
    *,
    settings: ExportSettings | None = None,
    on_saved: Callable[[ExportSettings], None] | None = None,
) -> ExportSettingsDialog:
    """Open the export settings dialog (non-blocking; use on_saved for updates)."""
    return ExportSettingsDialog(master, settings=settings, on_saved=on_saved)
