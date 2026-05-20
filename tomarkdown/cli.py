"""CLI entry point for batch docx to markdown conversion."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tomarkdown.converter import ConversionError, convert_docx_to_md


@dataclass
class BatchResult:
    """Summary of a batch conversion run."""

    succeeded: list[Path] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.succeeded)

    @property
    def failure_count(self) -> int:
        return len(self.failed)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def collect_docx_files(input_path: Path, recursive: bool) -> list[Path]:
    """Collect .docx files from a file or directory."""
    input_path = Path(input_path)

    if input_path.is_file():
        if input_path.suffix.lower() != ".docx":
            raise ValueError(f"Input file is not a .docx: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    pattern = "**/*.docx" if recursive else "*.docx"
    return sorted(input_path.glob(pattern))


def resolve_output_path(
    src: Path,
    input_root: Path,
    output_dir: Path,
) -> Path:
    """Map source .docx path to destination .md path, preserving subdirs."""
    if input_root.is_file():
        relative = src.name
    else:
        relative = src.relative_to(input_root)

    return output_dir / relative.with_suffix(".md")


def write_error_log(log_path: Path, failures: list[tuple[Path, str]]) -> None:
    """Append failure records to errors.log."""
    if not failures:
        return

    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n--- Batch run at {timestamp} ---\n")
        for src, message in failures:
            log_file.write(f"{src}\t{message}\n")


def run_batch(
    input_path: Path,
    output_dir: Path | None,
    *,
    recursive: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
    error_log: Path | None = None,
) -> BatchResult:
    """Convert all .docx files under input_path."""
    input_path = Path(input_path).resolve()

    if output_dir is None:
        output_dir = input_path.parent if input_path.is_file() else input_path
    else:
        output_dir = Path(output_dir).resolve()

    files = collect_docx_files(input_path, recursive)
    result = BatchResult()
    total = len(files)

    if total == 0:
        print("No .docx files found.", file=sys.stderr)
        return result

    for index, src in enumerate(files, start=1):
        dst = resolve_output_path(src, input_path, output_dir)

        if dst.exists() and not overwrite:
            result.skipped.append(src)
            if verbose:
                print(f"[{index}/{total}] Skipped (exists): {src}")
            continue

        if verbose:
            print(f"[{index}/{total}] Converting: {src}")
        else:
            print(f"[{index}/{total}] {src.name}")

        try:
            convert_docx_to_md(src, dst)
            result.succeeded.append(src)
            if verbose:
                print(f"  -> {dst}")
        except (ConversionError, FileNotFoundError, ValueError) as exc:
            result.failed.append((src, str(exc)))
            print(f"  ERROR: {exc}", file=sys.stderr)

    if error_log is not None:
        write_error_log(error_log, result.failed)

    return result


def print_summary(result: BatchResult) -> None:
    """Print batch conversion summary."""
    parts = [f"成功 {result.success_count}"]
    if result.failure_count:
        parts.append(f"失败 {result.failure_count}")
    if result.skipped_count:
        parts.append(f"跳过 {result.skipped_count}")

    print(f"\n汇总: {' / '.join(parts)} (共 {result.success_count + result.failure_count + result.skipped_count} 个文件)")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="tomd",
        description="Batch convert .docx files to Markdown using markitdown.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input .docx file or directory containing .docx files",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: same directory as input)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively process .docx files in subdirectories",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .md files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show detailed processing logs",
    )
    parser.add_argument(
        "--error-log",
        type=Path,
        default=Path("errors.log"),
        help="Path to error log file (default: errors.log)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_batch(
            args.input,
            args.output,
            recursive=args.recursive,
            overwrite=args.overwrite,
            verbose=args.verbose,
            error_log=args.error_log,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(result)

    if result.failure_count:
        print(f"失败详情已写入: {args.error_log.resolve()}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
