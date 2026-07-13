"""CLI entry point for bidirectional document ↔ Markdown conversion."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tomarkdown.converter import (
    ConversionError,
    Direction,
    OutputFormat,
    collect_files,
    convert_batch,
    resolve_output_path,
)


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
    """Collect .docx files from a file or directory (legacy helper)."""
    input_path = Path(input_path)

    if input_path.is_file():
        if input_path.suffix.lower() != ".docx":
            raise ValueError(f"Input file is not a .docx: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    pattern = "**/*.docx" if recursive else "*.docx"
    return sorted(input_path.glob(pattern))


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
    direction: Direction = "to_md",
    output_format: OutputFormat | None = None,
) -> BatchResult:
    """Convert files under input_path according to direction."""
    input_path = Path(input_path).resolve()

    if output_dir is None:
        output_dir = input_path.parent if input_path.is_file() else input_path
    else:
        output_dir = Path(output_dir).resolve()

    files = collect_files(input_path, recursive, direction=direction)
    result = BatchResult()
    total = len(files)

    if total == 0:
        kind = "Markdown" if direction == "from_md" else "document"
        print(f"No {kind} files found.", file=sys.stderr)
        return result

    if direction == "from_md":
        fmt: OutputFormat = output_format or "docx"
        suffix = f".{fmt}"
    else:
        fmt = "md"
        suffix = ".md"

    input_roots: dict[Path, Path] = {}
    if input_path.is_dir():
        for src in files:
            input_roots[src] = input_path

    def on_progress(current: int, total_n: int, src: Path, success: bool, message: str) -> None:
        if message == "skipped":
            result.skipped.append(src)
            if verbose:
                print(f"[{current}/{total_n}] Skipped (exists): {src}")
            return

        if verbose:
            print(f"[{current}/{total_n}] Converting: {src}")
        else:
            print(f"[{current}/{total_n}] {src.name}")

        if success:
            result.succeeded.append(src)
            if verbose:
                dst = resolve_output_path(
                    src,
                    output_dir,
                    input_roots.get(src),
                    output_suffix=suffix,
                )
                print(f"  -> {dst}")
        else:
            result.failed.append((src, message))
            print(f"  ERROR: {message}", file=sys.stderr)

    batch = convert_batch(
        files,
        output_dir,
        callback=on_progress,
        overwrite=overwrite,
        input_roots=input_roots,
        direction=direction,
        output_format=fmt,
    )

    # Prefer batch counters if callback bookkeeping drifts
    if (
        len(result.succeeded) != batch["success_count"]
        or len(result.failed) != batch["failure_count"]
        or len(result.skipped) != batch["skipped_count"]
    ):
        result.succeeded = list(batch["success"])
        result.failed = list(batch["failed"])
        result.skipped = list(batch["skipped"])

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

    total = result.success_count + result.failure_count + result.skipped_count
    print(f"\n汇总: {' / '.join(parts)} (共 {total} 个文件)")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="tomd",
        description="Bidirectional batch converter: Word/PDF ↔ Markdown.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input file or directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: same directory as input)",
    )
    parser.add_argument(
        "-d",
        "--direction",
        choices=["to-md", "from-md"],
        default="to-md",
        help="Conversion direction (default: to-md)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["docx", "pdf"],
        default="docx",
        help="Output format when direction is from-md (default: docx)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively process files in subdirectories",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files",
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

    direction: Direction = "from_md" if args.direction == "from-md" else "to_md"
    output_format: OutputFormat | None = args.format if direction == "from_md" else "md"

    try:
        result = run_batch(
            args.input,
            args.output,
            recursive=args.recursive,
            overwrite=args.overwrite,
            verbose=args.verbose,
            error_log=args.error_log,
            direction=direction,
            output_format=output_format,
        )
    except (FileNotFoundError, ValueError, ConversionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(result)

    if result.failure_count:
        print(f"失败详情已写入: {args.error_log.resolve()}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
