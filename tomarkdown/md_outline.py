"""Lightweight markdown cleanup helpers shared by outline fixers."""

from __future__ import annotations

import re

HEADING_RE = re.compile(r"^(#{1,6})( .+)$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
CONTACT_HEADING_RE = re.compile(r"^#{1,6}\s*(Tel|Fax|Email|Web)\b", re.IGNORECASE)
CHAPTER_PATTERNS = (
    re.compile(r"^\*\*(\d+)\*\*\s*\d+B\*\*(.+?)\*\*\s*$"),
    re.compile(r"^(?:\d+\.\s*)?(\d+)B\*\*(.+?)\*\*\s*$"),
)


def split_images_from_heading(line: str) -> list[str]:
    match = HEADING_RE.match(line)
    if not match:
        return [line]

    marks, text = match.group(1), match.group(2).strip()
    image_match = IMAGE_RE.match(text)
    if not image_match:
        return [line]

    image = image_match.group(0)
    title = text[image_match.end() :].strip()
    lines = [image]
    if title:
        lines.append(f"{marks} {title}")
    return lines


def _promote_chapter_line(line: str) -> str | None:
    stripped = line.strip()
    for pattern in CHAPTER_PATTERNS:
        match = pattern.match(stripped)
        if match:
            number, title = match.group(1), match.group(2).strip()
            if number == "0":
                return f"## {title}"
            return f"## {number} {title}"
    return None


def _postprocess_common(content: str) -> str:
    expanded: list[str] = []
    for line in content.splitlines():
        expanded.extend(split_images_from_heading(line))

    seen_h1: set[str] = set()
    processed: list[str] = []
    for line in expanded:
        chapter = _promote_chapter_line(line)
        if chapter is not None:
            processed.append(chapter)
            continue

        if CONTACT_HEADING_RE.match(line):
            processed.append(re.sub(r"^#{1,6}\s*", "", line))
            continue

        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            title = match.group(2).strip()
            if title in seen_h1:
                processed.append(f"**{title}**")
                continue
            seen_h1.add(title)
        processed.append(line)

    return "\n".join(processed)
