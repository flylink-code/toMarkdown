"""Build markdown heading hierarchy from Word outline metadata."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

HEADING_STYLES = {"Heading1", "Heading2", "Heading3", "Heading4", "Heading5", "Heading6"}
CONTACT_RE = re.compile(r"^(Tel|Fax|Email|Web)\b", re.IGNORECASE)
CHAPTER_TEXT_RE = re.compile(r"^(\d+)B\s*(.+)$")
CHAPTER_EMBEDDED_RE = re.compile(
    r"(\d)B([\u4e00-\u9fffA-Za-z/ （）()\-、，。：；]{2,20})(?=ATT7022E/26E/28E|\Z)"
)
BOOKMARK_SECTION_RE = re.compile(r"^([\d.]+)\s*(.*)$")


@dataclass
class OutlineEntry:
    text: str
    level: int
    style: str | None = None


class NumberingResolver:
    """Track Word list numbering counters to recover section labels like 2.5.1."""

    def __init__(self, numbering_root: ET.Element | None) -> None:
        self.numbering = numbering_root
        self.counters: dict[str, list[int]] = {}
        self.num_to_abstract: dict[str, str] = {}
        if numbering_root is None:
            return
        for num in numbering_root.findall("w:num", NS):
            num_id = num.get(f"{{{NS['w']}}}numId")
            abstract = num.find("w:abstractNumId", NS)
            if num_id and abstract is not None:
                self.num_to_abstract[num_id] = abstract.get(f"{{{NS['w']}}}val", "")

    def _lvl_info(self, abstract_id: str, ilvl: int) -> tuple[str, int]:
        if self.numbering is None:
            return "%1", 1
        for absnum in self.numbering.findall("w:abstractNum", NS):
            if absnum.get(f"{{{NS['w']}}}abstractNumId") != abstract_id:
                continue
            for lvl in absnum.findall("w:lvl", NS):
                if int(lvl.get(f"{{{NS['w']}}}ilvl", -1)) != ilvl:
                    continue
                fmt = lvl.find("w:lvlText", NS)
                start = lvl.find("w:start", NS)
                template = fmt.get(f"{{{NS['w']}}}val") if fmt is not None else "%1"
                start_val = int(start.get(f"{{{NS['w']}}}val", "1")) if start is not None else 1
                return template or "%1", start_val
        return "%1", 1

    def label_for(self, num_id: str, ilvl: int) -> str | None:
        abstract_id = self.num_to_abstract.get(num_id)
        if abstract_id is None:
            return None

        counters = self.counters.setdefault(num_id, [])
        while len(counters) <= ilvl:
            _, start_val = self._lvl_info(abstract_id, len(counters))
            counters.append(start_val - 1)

        counters[ilvl] += 1
        for level in range(ilvl + 1, len(counters)):
            _, start_val = self._lvl_info(abstract_id, level)
            counters[level] = start_val - 1

        template, _ = self._lvl_info(abstract_id, ilvl)
        display_values: list[int] = []
        for level in range(ilvl + 1):
            start_val = self._lvl_info(abstract_id, level)[1]
            if level < ilvl and counters[level] < start_val:
                display_values.append(start_val)
            else:
                display_values.append(counters[level])

        label = template
        for index, value in enumerate(display_values):
            label = label.replace(f"%{index + 1}", str(value))
        if "%" in label:
            return None
        return label


def _paragraph_text(paragraph: ET.Element) -> str:
    return "".join(node.text or "" for node in paragraph.findall(".//w:t", NS)).strip()


def _paragraph_style(paragraph: ET.Element) -> str | None:
    style = paragraph.find("w:pPr/w:pStyle", NS)
    if style is None:
        return None
    return style.get(f"{{{NS['w']}}}val")


def _paragraph_numpr(paragraph: ET.Element) -> tuple[int, str] | None:
    num = paragraph.find("w:pPr/w:numPr", NS)
    if num is None:
        return None
    ilvl = num.find("w:ilvl", NS)
    num_id = num.find("w:numId", NS)
    if ilvl is None or num_id is None:
        return None
    return int(ilvl.get(f"{{{NS['w']}}}val", "0")), num_id.get(f"{{{NS['w']}}}val", "")


def _paragraph_bookmarks(paragraph: ET.Element) -> list[str]:
    names: list[str] = []
    for bookmark in paragraph.findall("w:bookmarkStart", NS):
        name = bookmark.get(f"{{{NS['w']}}}name")
        if name and not name.startswith("_"):
            names.append(name.strip())
    return names


def _level_for_label(label: str) -> int:
    """Map a dotted section label (e.g. ``4.2.1``) to a markdown heading depth."""
    depth = len([part for part in label.split(".") if part])
    return min(depth + 1, 6)


def _label_from_bookmark(name: str) -> str | None:
    match = BOOKMARK_SECTION_RE.match(name.strip())
    if not match:
        return None
    parts = [part for part in match.group(1).strip(".").split(".") if part]
    if not parts:
        return None
    return ".".join(parts)


def _compose_heading(label: str, text: str) -> str:
    body = re.sub(rf"^{re.escape(label)}\s*", "", text.strip())
    return f"{label} {body}".strip()


def _normalize_chapter_number(number: str) -> str:
    # Word TOC anchors are sometimes doubled (e.g. "66B"); collapse a run of the
    # same digit back to a single chapter number.
    if len(number) >= 2 and len(set(number)) == 1:
        return number[0]
    return number


def _is_chapter_title(title: str) -> bool:
    return bool(title) and bool(re.match(r"^[\u4e00-\u9fffA-Za-z]", title)) and "0x" not in title


def _chapter_from_text(text: str) -> OutlineEntry | None:
    compact = re.sub(r"\s+", "", text)
    match = CHAPTER_TEXT_RE.match(compact)
    if match:
        number, title = match.group(1), match.group(2).strip()
        if not _is_chapter_title(title):
            return None
        if number == "0":
            return OutlineEntry(text=title, level=2)
        return OutlineEntry(text=f"{_normalize_chapter_number(number)} {title}", level=2)

    embedded = CHAPTER_EMBEDDED_RE.search(text)
    if embedded:
        number, title = embedded.group(1), embedded.group(2).strip()
        if _is_chapter_title(title) and len(title) >= 2:
            return OutlineEntry(text=f"{_normalize_chapter_number(number)} {title}", level=2)
    return None


def _order_outline(entries: list[OutlineEntry]) -> list[OutlineEntry]:
    """Place chapter headings before their numbered sections."""
    chapters: dict[int, OutlineEntry] = {}
    for entry in entries:
        parts = entry.text.split(None, 1)
        if entry.level == 2 and parts and parts[0].isdigit() and "." not in parts[0]:
            chapters[int(parts[0])] = entry

    if not chapters:
        return entries

    ordered: list[OutlineEntry] = []
    emitted: set[int] = set()
    for entry in entries:
        if entry in chapters.values():
            continue

        match = re.match(r"^(\d+)\.", entry.text)
        if match:
            chapter_num = int(match.group(1))
            if chapter_num not in emitted and chapter_num in chapters:
                ordered.append(chapters[chapter_num])
                emitted.add(chapter_num)
        ordered.append(entry)

    for chapter_num, chapter in chapters.items():
        if chapter_num not in emitted:
            ordered.append(chapter)
    return ordered


def extract_docx_outline(src: Path) -> list[OutlineEntry]:
    """Extract document heading order and levels from Word outline metadata."""
    with zipfile.ZipFile(src) as docx:
        document = ET.fromstring(docx.read("word/document.xml"))
        numbering = (
            ET.fromstring(docx.read("word/numbering.xml"))
            if "word/numbering.xml" in docx.namelist()
            else None
        )

    numbering_resolver = NumberingResolver(numbering)
    entries: list[OutlineEntry] = []
    seen_h1: set[str] = set()

    for paragraph in document.findall(".//w:body/w:p", NS):
        text = _paragraph_text(paragraph)
        if not text:
            continue

        style = _paragraph_style(paragraph)
        bookmarks = _paragraph_bookmarks(paragraph)
        numpr = _paragraph_numpr(paragraph)

        chapter = _chapter_from_text(text)
        if chapter is not None:
            if not entries or entries[-1].text != chapter.text:
                entries.append(chapter)
            if numpr is not None:
                numbering_resolver.label_for(numpr[1], numpr[0])
            continue

        if style not in HEADING_STYLES:
            continue

        if style == "Heading3" and CONTACT_RE.match(text):
            continue

        if style == "Heading1":
            if text in seen_h1:
                continue
            seen_h1.add(text)
            entries.append(OutlineEntry(text=text, level=1, style=style))
            continue

        # Always advance the numbering counter for numbered headings so that
        # sibling sections stay in sync even when an earlier sibling's label is
        # taken from its bookmark instead.
        num_label = (
            numbering_resolver.label_for(numpr[1], numpr[0])
            if numpr is not None
            else None
        )

        bookmark_label: str | None = None
        for bookmark in bookmarks:
            bookmark_label = _label_from_bookmark(bookmark)
            if bookmark_label:
                break

        # Bookmarks carry the authoritative section number; fall back to the
        # list-numbering label, then to any number already present in the text.
        label = bookmark_label or num_label
        if label is None:
            text_match = re.match(r"^(\d+(?:\.\d+)+)\s", text)
            if text_match:
                label = text_match.group(1)

        if label:
            heading = OutlineEntry(
                text=_compose_heading(label, text),
                level=_level_for_label(label),
                style=style,
            )
        elif style == "Heading2":
            heading = OutlineEntry(text=text, level=3, style=style)
        elif style == "Heading3":
            heading = OutlineEntry(text=text, level=4, style=style)
        else:
            heading = OutlineEntry(text=text, level=4, style=style)

        entries.append(heading)

    return _order_outline(entries)


def _normalize_heading_text(text: str) -> str:
    text = re.sub(r"\s+", "", text.strip())
    text = re.sub(r"^[\d.]+", "", text)
    return text.casefold()


def _match_heading(candidate: str, target: str) -> bool:
    left = _normalize_heading_text(candidate)
    right = _normalize_heading_text(target)
    if not left or not right:
        return False
    if left == right:
        return True
    # Word bookmark titles may be truncated; accept a prefix relationship only
    # when the shorter side is a substantial prefix of the longer one.
    shorter, longer = sorted((left, right), key=len)
    return len(shorter) >= 4 and longer.startswith(shorter)


def apply_docx_outline(content: str, outline: list[OutlineEntry]) -> str:
    """Replace mammoth heading levels with Word outline-derived headings."""
    if not outline:
        return content

    heading_re = re.compile(r"^(#{1,6})\s+(.*)$")
    outline_index = 0
    result: list[str] = []

    for line in content.splitlines():
        match = heading_re.match(line)
        if not match:
            result.append(line)
            continue

        title = match.group(2).strip()
        # Look ahead for the next matching outline entry without consuming the
        # pointer on misses, so headings absent from the outline (e.g. stray
        # table headings) don't desync the remaining document.
        found = -1
        for offset in range(outline_index, len(outline)):
            if _match_heading(title, outline[offset].text):
                found = offset
                break

        if found == -1:
            result.append(line)
            continue

        entry = outline[found]
        result.append("#" * entry.level + f" {entry.text}")
        outline_index = found + 1

    return "\n".join(result)


def fix_markdown_outline(content: str, src: Path | None = None) -> str:
    """Apply Word-outline-aware heading fixes to converted markdown."""
    from tomarkdown.md_outline import _postprocess_common

    content = _postprocess_common(content)
    if src is None or not src.exists():
        return content

    outline = extract_docx_outline(src)
    return apply_docx_outline(content, outline)
