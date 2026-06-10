"""Tests for markdown outline post-processing."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tomarkdown.converter import convert_docx_to_md
from tomarkdown.docx_outline import (
    apply_docx_outline,
    extract_docx_outline,
    fix_markdown_outline,
)
from tomarkdown.md_outline import _postprocess_common

SAMPLE_DOCX = Path(__file__).parent / "sample.docx"
ATT7022_DOCX = Path(__file__).parent.parent / "_batch_test" / "ATT7022EU-N_Data_Copy.docx"


def test_split_image_from_heading() -> None:
    md = _postprocess_common("# ![](assets/a.png)Document Title\n\nBody")
    assert md.splitlines()[:2] == ["![](assets/a.png)", "# Document Title"]


def test_promote_chapter_line() -> None:
    md = _postprocess_common("**1** 1B**芯片概况**\n")
    assert md.strip() == "## 1 芯片概况"


def test_extract_att7022_outline_has_numbered_sections() -> None:
    if not ATT7022_DOCX.exists():
        pytest.skip("ATT7022 sample docx not available")

    outline = extract_docx_outline(ATT7022_DOCX)
    texts = [entry.text for entry in outline]

    assert any(text.startswith("1 芯片概况") for text in texts)
    assert any(text.startswith("1.1 芯片简介") for text in texts)
    assert any("2.4 A/D转换" in text for text in texts)
    assert any("SAG功能" in text for text in texts)


def test_apply_docx_outline_uses_bookmark_numbers() -> None:
    outline = [
        type("E", (), {"text": "1.1 芯片简介", "level": 3})(),
        type("E", (), {"text": "2.4 A/D转换", "level": 3})(),
        type("E", (), {"text": "2.5.1 SAG功能", "level": 3})(),
        type("E", (), {"text": "2.5.2 过流检测功能", "level": 4})(),
    ]
    md = apply_docx_outline(
        "## 芯片简介\n\n## A/D转换\n\n#### SAG功能\n\n#### 过流检测功能\n",
        outline,
    )
    lines = md.splitlines()
    assert lines[0] == "### 1.1 芯片简介"
    assert lines[2] == "### 2.4 A/D转换"
    assert lines[4] == "### 2.5.1 SAG功能"
    assert lines[6] == "#### 2.5.2 过流检测功能"


def test_att7022_outline_structure() -> None:
    if not ATT7022_DOCX.exists():
        pytest.skip("ATT7022 sample docx not available")

    dst = Path(__file__).parent / "_att7022_outline.md"
    convert_docx_to_md(ATT7022_DOCX, dst)
    md = dst.read_text(encoding="utf-8")
    lines = md.splitlines()

    assert lines[0].startswith("![](")
    assert lines[1].startswith("# ATT7022E")
    assert "Tel:" in md
    assert "### Tel:" not in md

    assert "## 1 芯片概况" in lines
    assert "### 1.1 芯片简介" in lines
    assert "### 2.4 A/D转换" in lines
    assert "#### 2.5.1 SAG功能" in lines
    assert "#### 2.5.2 过流检测功能" in lines

    sag_index = lines.index("#### 2.5.1 SAG功能")
    ad_index = lines.index("### 2.4 A/D转换")
    assert sag_index > ad_index

    chapter_headings = [line for line in lines if re.match(r"^## \d+ ", line)]
    assert chapter_headings == [
        "## 1 芯片概况",
        "## 2 功能描述",
        "## 3 通信接口",
        "## 4 寄存器",
        "## 5 电气规格",
        "## 6 校表过程",
        "## 7 芯片封装",
        "## 8 典型应用",
    ]

    assert "### 4.1 计量参数寄存器" in lines
    assert "### 4.3 校表参数寄存器" in lines
    assert "### 4.4 校表参数寄存器说明" in lines
    assert "#### 4.4.1 模式配置寄存器（地址：0x01）" in lines
    assert "#### 4.4.27 算法控制寄存器(0x70)" in lines

    h1_titles = [line for line in lines if line.startswith("# ") and not line.startswith("##")]
    assert len(h1_titles) == 1

    dst.unlink(missing_ok=True)


def test_fix_markdown_outline_without_src_keeps_basic_cleanup() -> None:
    md = fix_markdown_outline("# ![](a.png)Title\n\n### Tel: 021\n", src=None)
    assert md.splitlines()[0] == "![](a.png)"
    assert "Tel: 021" in md
