"""Markdown export settings: model, persistence, and placeholder helpers."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path
from typing import Any


SETTINGS_VERSION = 3

_HEX6 = re.compile(r"^[0-9A-Fa-f]{6}$")
_HEX3 = re.compile(r"^[0-9A-Fa-f]{3}$")

# Built-in style presets (Typora / GitHub inspired)
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "typora": {
        "heading_color": "1F2328",
        "heading_h1_color": "1F2328",
        "heading_h2_color": "1F2328",
        "heading_h3_color": "1F2328",
        "code_bg": "F6F8FA",
        "code_border": "D0D7DE",
        "code_font": "Consolas",
        "code_font_size": 9.5,
        "code_highlight": True,
        "code_show_language": True,
        "inline_code_bg": "F3F4F6",
        "inline_code_fg": "CF222E",
    },
    "github": {
        "heading_color": "1F2328",
        "heading_h1_color": "1F2328",
        "heading_h2_color": "1F2328",
        "heading_h3_color": "1F2328",
        "code_bg": "F6F8FA",
        "code_border": "D0D7DE",
        "code_font": "Consolas",
        "code_font_size": 9.5,
        "code_highlight": True,
        "code_show_language": True,
        "inline_code_bg": "EFF1F3",
        "inline_code_fg": "24292F",
    },
    "classic": {
        "heading_color": "000000",
        "heading_h1_color": "000000",
        "heading_h2_color": "000000",
        "heading_h3_color": "333333",
        "code_bg": "F5F5F5",
        "code_border": "CCCCCC",
        "code_font": "Courier New",
        "code_font_size": 9.0,
        "code_highlight": False,
        "code_show_language": False,
        "inline_code_bg": "EEEEEE",
        "inline_code_fg": "C7254E",
    },
}

STYLE_PRESET_LABELS = {
    "typora": "Typora 风格",
    "github": "GitHub 风格",
    "classic": "经典黑白",
    "custom": "自定义",
}


def normalize_hex_color(value: str | None, default: str) -> str:
    """Normalize #RGB / #RRGGBB / RGB / RRGGBB to uppercase RRGGBB."""
    raw = (value or "").strip().lstrip("#")
    if _HEX6.fullmatch(raw):
        return raw.upper()
    if _HEX3.fullmatch(raw):
        return "".join(ch * 2 for ch in raw.upper())
    return default.upper()


@dataclass
class ExportSettings:
    """Options applied when converting Markdown → Word / PDF.

    Designed for forward-compatible persistence: unknown keys are ignored on load;
    new fields get defaults when missing from older config files.
    """

    # Output
    output_format: str = "docx"  # docx | pdf

    # Header
    header_enabled: bool = False
    header_text: str = "{filename}"
    header_align: str = "center"  # left | center | right

    # Footer
    footer_enabled: bool = True
    footer_text: str = "第 {page} 页 / 共 {numpages} 页"
    footer_align: str = "center"

    # First page
    different_first_page: bool = False
    first_header_text: str = ""
    first_footer_text: str = ""

    # Document properties
    doc_title: str = ""  # empty → first H1, else filename
    doc_author: str = ""
    doc_subject: str = ""

    # Style
    style_preset: str = "typora"  # typora | github | classic | custom
    heading_color: str = "1F2328"  # fallback / H4+
    heading_h1_color: str = "1F2328"
    heading_h2_color: str = "1F2328"
    heading_h3_color: str = "1F2328"
    code_bg: str = "F6F8FA"
    code_border: str = "D0D7DE"
    code_font: str = "Consolas"
    code_font_size: float = 9.5
    code_highlight: bool = True
    code_show_language: bool = True
    inline_code_bg: str = "F3F4F6"
    inline_code_fg: str = "CF222E"

    # Schema version for future migrations
    version: int = SETTINGS_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def heading_color_for_level(self, level: int) -> str:
        """Return hex color for a heading level."""
        if level <= 1:
            return self.heading_h1_color or self.heading_color
        if level == 2:
            return self.heading_h2_color or self.heading_color
        if level == 3:
            return self.heading_h3_color or self.heading_color
        return self.heading_color

    def apply_style_preset(self, preset: str) -> None:
        """Overwrite style fields from a named preset (no-op for custom)."""
        if preset == "custom" or preset not in STYLE_PRESETS:
            self.style_preset = "custom" if preset == "custom" else self.style_preset
            return
        for key, value in STYLE_PRESETS[preset].items():
            setattr(self, key, value)
        self.style_preset = preset

    def normalize_style_fields(self) -> None:
        """Clamp / normalize style-related fields after load or UI collect."""
        if self.style_preset not in STYLE_PRESET_LABELS:
            self.style_preset = "custom"
        self.heading_color = normalize_hex_color(self.heading_color, "1F2328")
        self.heading_h1_color = normalize_hex_color(self.heading_h1_color, self.heading_color)
        self.heading_h2_color = normalize_hex_color(self.heading_h2_color, self.heading_color)
        self.heading_h3_color = normalize_hex_color(self.heading_h3_color, self.heading_color)
        self.code_bg = normalize_hex_color(self.code_bg, "F6F8FA")
        self.code_border = normalize_hex_color(self.code_border, "D0D7DE")
        self.inline_code_bg = normalize_hex_color(self.inline_code_bg, "F3F4F6")
        self.inline_code_fg = normalize_hex_color(self.inline_code_fg, "CF222E")
        font = (self.code_font or "Consolas").strip() or "Consolas"
        self.code_font = font
        try:
            size = float(self.code_font_size)
        except (TypeError, ValueError):
            size = 9.5
        self.code_font_size = max(7.0, min(16.0, size))
        self.code_highlight = bool(self.code_highlight)
        self.code_show_language = bool(self.code_show_language)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ExportSettings:
        if not data:
            return cls()
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        settings = cls(**filtered)
        settings.version = SETTINGS_VERSION
        if settings.output_format not in {"docx", "pdf"}:
            settings.output_format = "docx"
        if settings.header_align not in {"left", "center", "right"}:
            settings.header_align = "center"
        if settings.footer_align not in {"left", "center", "right"}:
            settings.footer_align = "center"
        settings.normalize_style_fields()
        return settings

    def format_label(self) -> str:
        """Human-readable export format for UI."""
        return "PDF" if self.output_format == "pdf" else "Word (.docx)"


def default_settings_path() -> Path:
    """User-writable settings file path."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "toMarkdown"
    else:
        base = Path.home() / ".config" / "tomarkdown"
    return base / "export_settings.json"


def load_export_settings(path: Path | None = None) -> ExportSettings:
    """Load settings from disk, or return defaults if missing/invalid."""
    path = path or default_settings_path()
    try:
        if not path.is_file():
            return ExportSettings()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ExportSettings()
        return ExportSettings.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return ExportSettings()


def save_export_settings(settings: ExportSettings, path: Path | None = None) -> Path:
    """Persist settings as JSON. Returns the written path."""
    settings.normalize_style_fields()
    path = path or default_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.to_dict()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def build_placeholder_context(
    *,
    source: Path | None = None,
    title: str = "",
    author: str = "",
) -> dict[str, str]:
    """Static placeholders (page fields are handled separately)."""
    filename = source.stem if source is not None else ""
    filename_ext = source.name if source is not None else ""
    return {
        "filename": filename,
        "filename_ext": filename_ext,
        "date": date.today().isoformat(),
        "title": title or filename,
        "author": author,
    }


PLACEHOLDER_HINT = (
    "可用占位符：{filename} {filename_ext} {date} {title} {author} {page} {numpages}"
)
