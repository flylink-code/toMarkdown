"""PySide6 settings dialog for Markdown export options."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from tomarkdown.export_settings import (
    PLACEHOLDER_HINT,
    STYLE_PRESET_LABELS,
    ExportSettings,
    load_export_settings,
    normalize_hex_color,
    save_export_settings,
)


class ColorField(QWidget):
    """Hex color entry with live swatch preview."""

    def __init__(self, value: str = "1F2328", parent=None) -> None:
        super().__init__(parent)
        self._default = value
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.entry = QLineEdit(value)
        self.entry.setMaximumWidth(120)
        self.swatch = QFrame()
        self.swatch.setFixedSize(28, 22)
        self.swatch.setFrameShape(QFrame.Shape.StyledPanel)

        layout.addWidget(self.entry)
        layout.addWidget(self.swatch)
        layout.addStretch(1)

        self.entry.textChanged.connect(self._refresh)
        self._refresh(value)

    def text(self) -> str:
        return self.entry.text().strip()

    def set_text(self, value: str) -> None:
        self.entry.setText(value)

    def _refresh(self, _text: str = "") -> None:
        hex_color = normalize_hex_color(self.entry.text(), self._default)
        self.swatch.setStyleSheet(
            f"background-color: #{hex_color}; border: 1px solid #888; border-radius: 3px;"
        )


class ExportSettingsDialog(QDialog):
    """Modal dialog for Markdown → document export settings."""

    def __init__(
        self,
        parent=None,
        *,
        settings: ExportSettings | None = None,
        on_saved: Callable[[ExportSettings], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_saved = on_saved
        self._settings = settings or load_export_settings()
        self._result: ExportSettings | None = None
        self._suppress_custom_mark = False

        self.setWindowTitle("Markdown 导出设置")
        self.resize(640, 600)
        self.setMinimumSize(540, 480)
        self.setModal(True)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        self._build_output_tab()
        self._build_style_tab()
        self._build_header_footer_tab()
        self._build_properties_tab()

        buttons = QDialogButtonBox()
        reset_btn = buttons.addButton("恢复默认", QDialogButtonBox.ButtonRole.ResetRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Save)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        reset_btn.clicked.connect(self._on_reset)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_output_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self._section_label("导出格式"))
        form = QFormLayout()
        self.format_docx = QRadioButton("Word (.docx)")
        self.format_pdf = QRadioButton("PDF")
        self.format_group = QButtonGroup(self)
        self.format_group.addButton(self.format_docx)
        self.format_group.addButton(self.format_pdf)
        if self._settings.output_format == "pdf":
            self.format_pdf.setChecked(True)
        else:
            self.format_docx.setChecked(True)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(self.format_docx)
        fmt_row.addWidget(self.format_pdf)
        fmt_row.addStretch(1)
        form.addRow("目标格式:", fmt_row)
        layout.addLayout(form)

        self.format_hint = QLabel()
        self.format_hint.setWordWrap(True)
        layout.addWidget(self.format_hint)
        self.format_docx.toggled.connect(self._update_format_hint)
        self.format_pdf.toggled.connect(self._update_format_hint)
        self._update_format_hint()

        layout.addWidget(self._section_label("说明"))
        tip = QLabel(
            "• Word (.docx)：纯本地生成，无需安装 Office。\n"
            "• PDF：先生成 Word，再通过本机 Microsoft Word 或 LibreOffice 转换。\n"
            "• 页眉页脚、文档属性、样式等选项对两种格式均生效。"
        )
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addStretch(1)
        self.tabs.addTab(page, "输出设置")

    def _build_style_tab(self) -> None:
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)

        layout.addWidget(self._section_label("风格预设"))
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("预设:"))
        self.style_preset = QComboBox()
        for key in ("typora", "github", "classic", "custom"):
            self.style_preset.addItem(STYLE_PRESET_LABELS[key], key)
        idx = self.style_preset.findData(self._settings.style_preset)
        self.style_preset.setCurrentIndex(max(0, idx))
        self.style_preset.currentIndexChanged.connect(self._on_preset_change)
        preset_row.addWidget(self.style_preset)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        layout.addWidget(self._section_label("标题颜色"))
        form = QFormLayout()
        self.heading_h1 = ColorField(self._settings.heading_h1_color)
        self.heading_h2 = ColorField(self._settings.heading_h2_color)
        self.heading_h3 = ColorField(self._settings.heading_h3_color)
        self.heading_color = ColorField(self._settings.heading_color)
        form.addRow("H1 颜色:", self.heading_h1)
        form.addRow("H2 颜色:", self.heading_h2)
        form.addRow("H3 颜色:", self.heading_h3)
        form.addRow("H4+ 颜色:", self.heading_color)
        layout.addLayout(form)

        layout.addWidget(self._section_label("代码块"))
        code_form = QFormLayout()
        self.code_bg = ColorField(self._settings.code_bg)
        self.code_border = ColorField(self._settings.code_border)
        self.code_font = QLineEdit(self._settings.code_font)
        self.code_font_size = QLineEdit(str(self._settings.code_font_size))
        self.code_font_size.setMaximumWidth(80)
        code_form.addRow("背景色:", self.code_bg)
        code_form.addRow("边框色:", self.code_border)
        code_form.addRow("字体:", self.code_font)
        code_form.addRow("字号:", self.code_font_size)
        layout.addLayout(code_form)

        self.code_highlight = QCheckBox("语法高亮")
        self.code_highlight.setChecked(self._settings.code_highlight)
        self.code_show_language = QCheckBox("显示语言标签")
        self.code_show_language.setChecked(self._settings.code_show_language)
        layout.addWidget(self.code_highlight)
        layout.addWidget(self.code_show_language)

        layout.addWidget(self._section_label("行内代码"))
        inline_form = QFormLayout()
        self.inline_code_fg = ColorField(self._settings.inline_code_fg)
        self.inline_code_bg = ColorField(self._settings.inline_code_bg)
        inline_form.addRow("文字色:", self.inline_code_fg)
        inline_form.addRow("背景色:", self.inline_code_bg)
        layout.addLayout(inline_form)

        hint = QLabel(
            "颜色填写 6 位十六进制，如 1F2328 或 #1F2328。修改任意项将自动切到「自定义」。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

        for field in (
            self.heading_h1,
            self.heading_h2,
            self.heading_h3,
            self.heading_color,
            self.code_bg,
            self.code_border,
            self.inline_code_fg,
            self.inline_code_bg,
        ):
            field.entry.textChanged.connect(self._mark_custom_preset)
        self.code_font.textChanged.connect(self._mark_custom_preset)
        self.code_font_size.textChanged.connect(self._mark_custom_preset)
        self.code_highlight.toggled.connect(self._mark_custom_preset)
        self.code_show_language.toggled.connect(self._mark_custom_preset)

        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.tabs.addTab(page, "样式")

    def _build_header_footer_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.header_enabled = QCheckBox("启用页眉")
        self.header_enabled.setChecked(self._settings.header_enabled)
        layout.addWidget(self.header_enabled)

        self.header_text = QTextEdit(self._settings.header_text)
        self.header_text.setMaximumHeight(70)
        form.addRow("页眉内容:", self.header_text)
        self.header_align = self._align_combo(self._settings.header_align)
        form.addRow("页眉对齐:", self.header_align)

        self.footer_enabled = QCheckBox("启用页脚")
        self.footer_enabled.setChecked(self._settings.footer_enabled)
        layout.addWidget(self.footer_enabled)

        self.footer_text = QTextEdit(self._settings.footer_text)
        self.footer_text.setMaximumHeight(70)
        form.addRow("页脚内容:", self.footer_text)
        self.footer_align = self._align_combo(self._settings.footer_align)
        form.addRow("页脚对齐:", self.footer_align)

        self.diff_first = QCheckBox("首页不同")
        self.diff_first.setChecked(self._settings.different_first_page)
        layout.addWidget(self.diff_first)

        self.first_header = QLineEdit(self._settings.first_header_text)
        self.first_footer = QLineEdit(self._settings.first_footer_text)
        form.addRow("首页页眉:", self.first_header)
        form.addRow("首页页脚:", self.first_footer)
        layout.addLayout(form)

        hint = QLabel(PLACEHOLDER_HINT)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        self.tabs.addTab(page, "页眉页脚")

    def _build_properties_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()
        self.doc_title = QLineEdit(self._settings.doc_title)
        self.doc_title.setPlaceholderText("留空则使用首个一级标题或文件名")
        self.doc_author = QLineEdit(self._settings.doc_author)
        self.doc_subject = QLineEdit(self._settings.doc_subject)
        form.addRow("标题:", self.doc_title)
        form.addRow("作者:", self.doc_author)
        form.addRow("主题:", self.doc_subject)
        layout.addLayout(form)
        tip = QLabel("这些信息会写入 Word 文档属性，并可用于页眉/页脚占位符。")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addStretch(1)
        self.tabs.addTab(page, "文档属性")

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        font.setPointSize(max(font.pointSize(), 11))
        label.setFont(font)
        return label

    @staticmethod
    def _align_combo(value: str) -> QComboBox:
        combo = QComboBox()
        for key, text in (("left", "左"), ("center", "中"), ("right", "右")):
            combo.addItem(text, key)
        idx = combo.findData(value)
        combo.setCurrentIndex(max(0, idx))
        return combo

    def _update_format_hint(self) -> None:
        if self.format_pdf.isChecked():
            self.format_hint.setText(
                "当前选择：PDF。导出时需要本机已安装 Microsoft Word 或 LibreOffice。"
            )
        else:
            self.format_hint.setText("当前选择：Word (.docx)。可直接生成，兼容性最好。")

    def _mark_custom_preset(self, *_args) -> None:
        if self._suppress_custom_mark:
            return
        idx = self.style_preset.findData("custom")
        if idx >= 0:
            self.style_preset.blockSignals(True)
            self.style_preset.setCurrentIndex(idx)
            self.style_preset.blockSignals(False)

    def _on_preset_change(self, _index: int = 0) -> None:
        key = self.style_preset.currentData()
        if key == "custom":
            return
        temp = ExportSettings()
        temp.apply_style_preset(str(key))
        self._suppress_custom_mark = True
        try:
            self.heading_h1.set_text(temp.heading_h1_color)
            self.heading_h2.set_text(temp.heading_h2_color)
            self.heading_h3.set_text(temp.heading_h3_color)
            self.heading_color.set_text(temp.heading_color)
            self.code_bg.set_text(temp.code_bg)
            self.code_border.set_text(temp.code_border)
            self.code_font.setText(temp.code_font)
            self.code_font_size.setText(str(temp.code_font_size))
            self.code_highlight.setChecked(temp.code_highlight)
            self.code_show_language.setChecked(temp.code_show_language)
            self.inline_code_fg.set_text(temp.inline_code_fg)
            self.inline_code_bg.set_text(temp.inline_code_bg)
        finally:
            self._suppress_custom_mark = False

    def _collect(self) -> ExportSettings:
        try:
            font_size = float(self.code_font_size.text().strip() or "9.5")
        except ValueError:
            font_size = 9.5
        settings = ExportSettings(
            output_format="pdf" if self.format_pdf.isChecked() else "docx",
            header_enabled=self.header_enabled.isChecked(),
            header_text=self.header_text.toPlainText().strip(),
            header_align=str(self.header_align.currentData()),
            footer_enabled=self.footer_enabled.isChecked(),
            footer_text=self.footer_text.toPlainText().strip(),
            footer_align=str(self.footer_align.currentData()),
            different_first_page=self.diff_first.isChecked(),
            first_header_text=self.first_header.text().strip(),
            first_footer_text=self.first_footer.text().strip(),
            doc_title=self.doc_title.text().strip(),
            doc_author=self.doc_author.text().strip(),
            doc_subject=self.doc_subject.text().strip(),
            style_preset=str(self.style_preset.currentData() or "custom"),
            heading_color=self.heading_color.text(),
            heading_h1_color=self.heading_h1.text(),
            heading_h2_color=self.heading_h2.text(),
            heading_h3_color=self.heading_h3.text(),
            code_bg=self.code_bg.text(),
            code_border=self.code_border.text(),
            code_font=self.code_font.text().strip(),
            code_font_size=font_size,
            code_highlight=self.code_highlight.isChecked(),
            code_show_language=self.code_show_language.isChecked(),
            inline_code_bg=self.inline_code_bg.text(),
            inline_code_fg=self.inline_code_fg.text(),
        )
        settings.normalize_style_fields()
        return settings

    def _apply_to_form(self, settings: ExportSettings) -> None:
        settings.normalize_style_fields()
        self.format_pdf.setChecked(settings.output_format == "pdf")
        self.format_docx.setChecked(settings.output_format != "pdf")
        self._update_format_hint()

        self.header_enabled.setChecked(settings.header_enabled)
        self.header_text.setPlainText(settings.header_text)
        self.header_align.setCurrentIndex(max(0, self.header_align.findData(settings.header_align)))
        self.footer_enabled.setChecked(settings.footer_enabled)
        self.footer_text.setPlainText(settings.footer_text)
        self.footer_align.setCurrentIndex(max(0, self.footer_align.findData(settings.footer_align)))
        self.diff_first.setChecked(settings.different_first_page)
        self.first_header.setText(settings.first_header_text)
        self.first_footer.setText(settings.first_footer_text)
        self.doc_title.setText(settings.doc_title)
        self.doc_author.setText(settings.doc_author)
        self.doc_subject.setText(settings.doc_subject)

        self._suppress_custom_mark = True
        try:
            idx = self.style_preset.findData(settings.style_preset)
            self.style_preset.setCurrentIndex(max(0, idx))
            self.heading_h1.set_text(settings.heading_h1_color)
            self.heading_h2.set_text(settings.heading_h2_color)
            self.heading_h3.set_text(settings.heading_h3_color)
            self.heading_color.set_text(settings.heading_color)
            self.code_bg.set_text(settings.code_bg)
            self.code_border.set_text(settings.code_border)
            self.code_font.setText(settings.code_font)
            self.code_font_size.setText(str(settings.code_font_size))
            self.code_highlight.setChecked(settings.code_highlight)
            self.code_show_language.setChecked(settings.code_show_language)
            self.inline_code_fg.set_text(settings.inline_code_fg)
            self.inline_code_bg.set_text(settings.inline_code_bg)
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
        self.accept()

    @property
    def result(self) -> ExportSettings | None:
        return self._result


def open_export_settings_dialog(
    parent=None,
    *,
    settings: ExportSettings | None = None,
    on_saved: Callable[[ExportSettings], None] | None = None,
) -> ExportSettingsDialog:
    """Open the export settings dialog and exec it modally."""
    dialog = ExportSettingsDialog(parent, settings=settings, on_saved=on_saved)
    dialog.exec()
    return dialog
