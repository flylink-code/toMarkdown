"""Tests for docx to markdown conversion."""

from __future__ import annotations

from pathlib import Path

import pytest
from docx import Document

from tomarkdown.converter import (
    ConversionError,
    convert_batch,
    convert_docx_to_md,
    convert_file,
)

SAMPLE_DOCX = Path(__file__).parent / "sample.docx"
SAMPLE_TITLE = "Hello Markdown"


@pytest.fixture(scope="module", autouse=True)
def create_sample_docx() -> None:
    """Create a sample .docx file for tests if it does not exist."""
    if SAMPLE_DOCX.exists():
        return

    doc = Document()
    doc.add_heading(SAMPLE_TITLE, level=1)
    doc.add_paragraph("This is a test paragraph for conversion.")
    doc.add_paragraph("Second line with bold text.", style="Normal")
    doc.save(SAMPLE_DOCX)


def test_convert_docx_to_md(tmp_path: Path) -> None:
    """Given a .docx file, output a valid .md file."""
    dst = tmp_path / "output.md"

    convert_docx_to_md(SAMPLE_DOCX, dst)

    assert dst.exists()
    content = dst.read_text(encoding="utf-8")
    assert content.strip()
    assert SAMPLE_TITLE in content or "Hello" in content


def test_convert_missing_file(tmp_path: Path) -> None:
    """Raise FileNotFoundError when source does not exist."""
    with pytest.raises(FileNotFoundError):
        convert_docx_to_md(tmp_path / "missing.docx", tmp_path / "out.md")


def test_convert_unsupported_format(tmp_path: Path) -> None:
    """Raise ValueError for unsupported extensions."""
    src = tmp_path / "notes.txt"
    src.write_text("not a docx", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        convert_docx_to_md(src, tmp_path / "out.md")


def test_convert_creates_output_directory(tmp_path: Path) -> None:
    """Create nested output directories as needed."""
    dst = tmp_path / "nested" / "dir" / "output.md"

    convert_docx_to_md(SAMPLE_DOCX, dst)

    assert dst.exists()


def test_convert_file_returns_bool(tmp_path: Path) -> None:
    """convert_file returns True on success."""
    dst = tmp_path / "output.md"
    assert convert_file(SAMPLE_DOCX, dst) is True
    assert dst.exists()


def test_convert_file_returns_false_on_missing(tmp_path: Path) -> None:
    """convert_file returns False when source is missing."""
    assert convert_file(tmp_path / "missing.docx", tmp_path / "out.md") is False


def test_convert_batch_with_callback(tmp_path: Path) -> None:
    """convert_batch reports progress via callback."""
    out_dir = tmp_path / "output"
    progress: list[tuple[int, int, bool]] = []

    def callback(current: int, total: int, _src: Path, success: bool, _msg: str) -> None:
        progress.append((current, total, success))

    result = convert_batch([SAMPLE_DOCX], out_dir, callback=callback)

    assert result["success_count"] == 1
    assert progress == [(1, 1, True)]
    assert (out_dir / "sample.md").exists()


def test_convert_empty_result_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Raise ConversionError when markitdown returns empty content."""

    class EmptyResult:
        markdown = ""
        text_content = ""

    class FakeMarkItDown:
        def convert(self, _path: str) -> EmptyResult:
            return EmptyResult()

    monkeypatch.setattr("tomarkdown.converter.MarkItDown", FakeMarkItDown)

    with pytest.raises(ConversionError, match="empty output"):
        convert_docx_to_md(SAMPLE_DOCX, tmp_path / "out.md")
