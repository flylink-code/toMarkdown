# toMarkdown

**文档 ↔ Markdown 双向转换器** — Windows 桌面工具，支持 Word / PDF 与 Markdown 互相转换。

[English](#english) · [中文](#中文)

[![Release](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml/badge.svg)](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## English

### Overview

**toMarkdown** is a lightweight Windows desktop app for bidirectional conversion between Microsoft Word / PDF and Markdown. Built with Python, [markitdown](https://github.com/microsoft/markitdown), [python-docx](https://python-docx.readthedocs.io/), [markdown-it-py](https://github.com/executablebooks/markdown-it-py), and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

### Features

- **Word / PDF → Markdown** — Batch convert `.doc`, `.docx`, and `.pdf`
- **Markdown → Word / PDF** — Export `.md` to `.docx` or `.pdf`
- **Batch conversion** — Process multiple files or entire folders
- **Legacy `.doc` support** — Via Microsoft Word or LibreOffice
- **PDF export** — Via Microsoft Word or LibreOffice (from Markdown)
- **Drag & drop** — Drop files or folders into the window
- **Recursive scan** — Optionally include subdirectories
- **Dark / Light theme** — Toggle appearance with one click
- **Progress & logs** — Live progress bar and per-file result log

### Download (Windows)

Download the latest release from **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)**:

1. Download `toMarkdown-vX.X.X-windows-x64.zip`
2. Extract to any folder
3. Run `toMarkdown.exe`

> **Notes:**
> - Converting `.doc` files requires **Microsoft Word** or **LibreOffice**.
> - Exporting Markdown to **PDF** also requires **Microsoft Word** or **LibreOffice**.
> - `.docx` ↔ Markdown works without extra apps.

### Run from Source

**Requirements:** Python 3.10+, Windows 10/11

```powershell
git clone https://github.com/flylink-code/toMarkdown.git
cd toMarkdown
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Or double-click `run.bat`.

### CLI

```powershell
# Document → Markdown
tomd input.docx -o out_dir
tomd ./docs -r --overwrite

# Markdown → Word / PDF
tomd note.md -d from-md -f docx -o out_dir
tomd ./notes -d from-md -f pdf -r
```

### Tech Stack

| Component | Purpose |
|-----------|---------|
| [markitdown](https://github.com/microsoft/markitdown) | Document → Markdown |
| [markdown-it-py](https://github.com/executablebooks/markdown-it-py) + [python-docx](https://python-docx.readthedocs.io/) | Markdown → Word |
| Microsoft Word / LibreOffice | `.doc` handling and PDF export |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | GUI |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | Drag-and-drop |

### Build Windows Release

```powershell
pip install pyinstaller
pyinstaller --noconfirm tomarkdown.spec
# Output: dist/toMarkdown/toMarkdown.exe
```

### Development

```powershell
pip install -e .
pytest tests/
```

---

## 中文

### 项目简介

**toMarkdown** 是一款轻量级 Windows 桌面工具，支持 **Word / PDF ↔ Markdown** 双向批量转换。基于 Python、[markitdown](https://github.com/microsoft/markitdown)、[python-docx](https://python-docx.readthedocs.io/)、[markdown-it-py](https://github.com/executablebooks/markdown-it-py) 与 [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 构建。

### 功能特性

- **文档 → Markdown** — 批量转换 `.doc` / `.docx` / `.pdf`
- **Markdown → 文档** — 导出为 `.docx` 或 `.pdf`
- **批量处理** — 支持多文件与整个文件夹
- **旧版 `.doc`** — 通过 Microsoft Word 或 LibreOffice 转换
- **PDF 导出** — Markdown 转 PDF 同样依赖 Word 或 LibreOffice
- **拖放文件** — 直接将文件或文件夹拖入窗口
- **递归扫描** — 可选包含子目录
- **深色 / 浅色主题** — 一键切换
- **进度与日志** — 实时进度条及每个文件的结果

### 下载（Windows 版）

从 **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)** 下载最新版本：

1. 下载 `toMarkdown-vX.X.X-windows-x64.zip`
2. 解压到任意目录
3. 运行 `toMarkdown.exe`

> **说明：**
> - 转换 `.doc` 需要安装 **Microsoft Word** 或 **LibreOffice**。
> - Markdown 导出为 **PDF** 同样需要 **Microsoft Word** 或 **LibreOffice**。
> - `.docx` ↔ Markdown 可直接使用。

### 从源码运行

**环境要求：** Python 3.10+，Windows 10/11

```powershell
git clone https://github.com/flylink-code/toMarkdown.git
cd toMarkdown
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

也可双击 `run.bat`。

### 使用方法

1. 选择转换方向：**文档 → Markdown** 或 **Markdown → 文档**
2. 若为导出方向，再选择 **Word (.docx)** 或 **PDF**
3. 添加文件 / 文件夹（或拖放）
4. 设置输出目录与选项后，点击「开始转换」

### 命令行

```powershell
# 文档 → Markdown
tomd input.docx -o out_dir

# Markdown → Word / PDF
tomd note.md -d from-md -f docx -o out_dir
tomd ./notes -d from-md -f pdf -r
```

### 项目结构

```
toMarkdown/
├── tomarkdown/
│   ├── converter.py      # 文档 → Markdown
│   ├── md_export.py      # Markdown → Word / PDF
│   ├── app.py            # GUI
│   └── cli.py            # 命令行
├── tests/
├── main.py
└── requirements.txt
```

### 技术栈

| 组件 | 用途 |
|------|------|
| markitdown | 文档转 Markdown |
| markdown-it-py + python-docx | Markdown 转 Word |
| Word / LibreOffice | `.doc` 与 PDF 导出 |
| CustomTkinter | 图形界面 |
| tkinterdnd2 | 拖放支持 |

### 开发

```powershell
pip install -e .
pytest tests/
```

---

## License

MIT
