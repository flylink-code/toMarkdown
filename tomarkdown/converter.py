"""Core conversion logic using markitdown (no GUI dependencies)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from markitdown import MarkItDown

ProgressCallback = Callable[[int, int, Path, bool, str], None]

SUPPORTED_EXTENSIONS = {".doc", ".docx"}


class ConversionError(Exception):
    """Raised when Word to markdown conversion fails."""


def is_supported_word_file(path: Path) -> bool:
    """Return True if path has a supported Word extension."""
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def _extract_markdown(result: object) -> str:
    """Extract markdown text from a MarkItDown result object."""
    if hasattr(result, "markdown") and result.markdown:
        return str(result.markdown)
    if hasattr(result, "text_content") and result.text_content:
        return str(result.text_content)
    raise ConversionError("Conversion produced empty output")


def _find_libreoffice() -> Path | None:
    """Locate LibreOffice soffice executable."""
    candidates: list[Path | str] = ["soffice", "libreoffice"]
    if sys.platform == "win32":
        candidates.extend(
            [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
        )

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            return path
        found = shutil.which(str(candidate))
        if found:
            return Path(found)
    return None


def _doc_to_docx_via_word(src: Path, dst: Path) -> None:
    """Convert .doc to .docx using Microsoft Word COM automation."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(src.resolve()))
        doc.SaveAs2(str(dst.resolve()), FileFormat=12)
        doc.Close()
    finally:
        if doc is not None:
            doc = None
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


def _doc_to_docx_via_libreoffice(src: Path, out_dir: Path) -> Path:
    """Convert .doc to .docx using LibreOffice headless mode."""
    soffice = _find_libreoffice()
    if soffice is None:
        raise ConversionError("LibreOffice not found")

    result = subprocess.run(
        [
            str(soffice),
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(out_dir),
            str(src.resolve()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise ConversionError(f"LibreOffice conversion failed: {stderr}")

    dst = out_dir / f"{src.stem}.docx"
    if not dst.exists():
        raise ConversionError("LibreOffice did not produce a .docx file")
    return dst


def _convert_doc_to_docx(src: Path) -> tuple[Path, Path]:
    """
    Convert legacy .doc to a temporary .docx file.

    Returns (docx_path, temp_dir) — caller must remove temp_dir when done.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="tomarkdown_"))
    dst = temp_dir / f"{src.stem}.docx"
    errors: list[str] = []

    if sys.platform == "win32":
        try:
            _doc_to_docx_via_word(src, dst)
            return dst, temp_dir
        except Exception as exc:
            errors.append(f"Word: {exc}")

    try:
        converted = _doc_to_docx_via_libreoffice(src, temp_dir)
        return converted, temp_dir
    except Exception as exc:
        errors.append(f"LibreOffice: {exc}")

    shutil.rmtree(temp_dir, ignore_errors=True)
    raise ConversionError(
        "无法转换 .doc 文件。请安装 Microsoft Word 或 LibreOffice，"
        "或先将文件另存为 .docx。"
        + (f" ({'; '.join(errors)})" if errors else "")
    )


def _convert_with_markitdown(src: Path) -> str:
    """Run markitdown on a .docx file and return markdown text."""
    try:
        converter = MarkItDown()
        result = converter.convert(str(src))
        return _extract_markdown(result)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Failed to convert {src.name}: {exc}") from exc


def _convert_docx(src: Path, dst: Path) -> str:
    """
    Convert .docx to markdown via mammoth, extracting embedded images to
    ``{output_stem}_assets/`` instead of stripping them to broken placeholders.
    """
    import mammoth
    from markitdown.converter_utils.docx.pre_process import pre_process_docx
    from markitdown.converters._html_converter import HtmlConverter

    assets_dir = dst.parent / f"{dst.stem}_assets"
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    image_count = 0

    def convert_image(image: object) -> dict[str, str]:
        nonlocal image_count
        image_count += 1
        content_type = getattr(image, "content_type", None) or "image/png"
        ext = content_type.rsplit("/", 1)[-1]
        if ext == "jpeg":
            ext = "jpg"
        filename = f"image{image_count}.{ext}"
        out_path = assets_dir / filename
        open_image = getattr(image, "open", None)
        if not callable(open_image):
            raise ConversionError(f"Unsupported embedded image in {src.name}")
        with open_image() as img_stream:
            out_path.write_bytes(img_stream.read())
        return {"src": f"{assets_dir.name}/{filename}"}

    try:
        with src.open("rb") as docx_file:
            processed = pre_process_docx(docx_file)
            html_result = mammoth.convert_to_html(
                processed,
                convert_image=mammoth.images.img_element(convert_image),
            )
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Failed to convert {src.name}: {exc}") from exc

    html_converter = HtmlConverter()
    md_result = html_converter.convert_string(html_result.value)
    content = (md_result.markdown or md_result.text_content or "").strip()

    if image_count == 0 and assets_dir.exists():
        shutil.rmtree(assets_dir, ignore_errors=True)

    if not content:
        raise ConversionError("Conversion produced empty output")

    return content


def _convert(src: Path, dst: Path) -> None:
    """Convert a single .doc/.docx file to Markdown and write to dst."""
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {src}")

    if not src.is_file():
        raise ValueError(f"Source is not a file: {src}")

    suffix = src.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format (expected .doc or .docx): {src.suffix}"
        )

    temp_dir: Path | None = None
    try:
        convert_src = src
        if suffix == ".doc":
            convert_src, temp_dir = _convert_doc_to_docx(src)

        try:
            content = _convert_docx(convert_src, dst)
        except ConversionError:
            raise
        except Exception:
            content = _convert_with_markitdown(convert_src)
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)

    dst.parent.mkdir(parents=True, exist_ok=True)

    try:
        dst.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ConversionError(f"Failed to write output file {dst}: {exc}") from exc


def convert_file(src: Path, dst: Path) -> bool:
    """Convert a single file. Returns True on success, False on failure."""
    try:
        _convert(src, dst)
        return True
    except Exception:
        return False


def resolve_output_path(src: Path, out_dir: Path, input_root: Path | None = None) -> Path:
    """Map source Word file to destination .md, preserving subdirs when input_root is set."""
    out_dir = Path(out_dir)
    if input_root is not None:
        try:
            relative = Path(src).relative_to(input_root)
            return out_dir / relative.with_suffix(".md")
        except ValueError:
            pass
    return out_dir / Path(src).with_suffix(".md").name


def collect_word_files(path: Path, recursive: bool = False) -> list[Path]:
    """Collect supported Word files from a file or directory."""
    path = Path(path)

    if path.is_file():
        return [path] if is_supported_word_file(path) else []

    if not path.is_dir():
        return []

    if recursive:
        files: list[Path] = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(path.glob(f"**/*{ext}"))
        return sorted(set(files))

    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(path.glob(f"*{ext}"))
    return sorted(set(files))


# Backward-compatible alias
collect_docx_files = collect_word_files


def convert_batch(
    files: list[Path],
    out_dir: Path,
    callback: ProgressCallback | None = None,
    *,
    overwrite: bool = False,
    input_roots: dict[Path, Path] | None = None,
) -> dict[str, Any]:
    """
    Batch convert files to Markdown under out_dir.

    callback(current, total, src, success, message) is invoked after each file.
    input_roots maps each source file to its folder root for relative output paths.
    """
    out_dir = Path(out_dir)
    input_roots = input_roots or {}
    total = len(files)

    succeeded: list[Path] = []
    failed: list[tuple[Path, str]] = []
    skipped: list[Path] = []

    for index, src in enumerate(files, start=1):
        src = Path(src)
        root = input_roots.get(src)
        dst = resolve_output_path(src, out_dir, root)

        if dst.exists() and not overwrite:
            skipped.append(src)
            if callback:
                callback(index, total, src, True, "skipped")
            continue

        try:
            _convert(src, dst)
            succeeded.append(src)
            if callback:
                callback(index, total, src, True, "")
        except Exception as exc:
            message = str(exc)
            failed.append((src, message))
            if callback:
                callback(index, total, src, False, message)

    return {
        "success": succeeded,
        "failed": failed,
        "skipped": skipped,
        "success_count": len(succeeded),
        "failure_count": len(failed),
        "skipped_count": len(skipped),
    }


# Backward-compatible alias for tests
convert_docx_to_md = _convert
