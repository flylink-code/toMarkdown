# toMarkdown

**文档 ↔ Markdown 双向转换器** — Windows 桌面工具，支持 Word / PDF 与 Markdown 互相转换。

[English](#english) · [中文](#中文)

[![Release](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml/badge.svg)](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## English

### Overview

**toMarkdown** is a lightweight Windows desktop app for bidirectional conversion between Microsoft Word / PDF and Markdown. Built with Python, [markitdown](https://github.com/microsoft/markitdown), [python-docx](https://python-docx.readthedocs.io/), [markdown-it-py](https://github.com/executablebooks/markdown-it-py), and [PySide6](https://doc.qt.io/qtforpython/).

### Features

- **Word / PDF → Markdown** — Batch convert `.doc`, `.docx`, and `.pdf`
- **Markdown → Word / PDF** — Export `.md` to `.docx` or `.pdf`
- **Export settings** — Output format, header/footer, document properties, and style presets (Typora / GitHub / classic / custom); quick **Config** button next to the conversion direction
- **Batch conversion** — Process multiple files or entire folders
- **Legacy `.doc` support** — Via Microsoft Word or LibreOffice
- **PDF export** — Via Microsoft Word or LibreOffice (from Markdown)
- **Drag & drop** — Native Qt drag-and-drop for files or folders
- **Recursive scan** — Optionally include subdirectories
- **Dark / Light theme** — Toggle appearance with one click
- **In-app updates** — Check GitHub Releases and install newer builds
- **Progress & logs** — Live progress bar and per-file result log

### Download (Windows)

Download the latest release from **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)**:

| Package | Use |
|---------|-----|
| `toMarkdown-vX.X.X-windows-x64.zip` | Portable: extract and run `toMarkdown.exe` |
| `toMarkdown-vX.X.X-windows-x64-setup.exe` | Installer (selectable directory, Start Menu and desktop shortcuts) |

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
| [Pygments](https://pygments.org/) | Code highlighting in exported Word |
| Microsoft Word / LibreOffice | `.doc` handling and PDF export |
| [PySide6](https://doc.qt.io/qtforpython/) | Desktop GUI (Qt) |

### Build Windows Release

```powershell
pip install pyinstaller
pyinstaller --noconfirm tomarkdown.spec
# Output: dist/toMarkdown/toMarkdown.exe
makensis /DAPP_VERSION=0.6.2 installer/toMarkdown.nsi
# Output: dist/toMarkdown-v0.6.2-windows-x64-setup.exe
```

Tagged releases (`v*`) are built by GitHub Actions (portable zip + NSIS installer).

### Development

```powershell
pip install -e .
pytest tests/
```

---

## 中文

### 项目简介

**toMarkdown** 是一款轻量级 Windows 桌面工具，支持 **Word / PDF ↔ Markdown** 双向批量转换。基于 Python、[markitdown](https://github.com/microsoft/markitdown)、[python-docx](https://python-docx.readthedocs.io/)、[markdown-it-py](https://github.com/executablebooks/markdown-it-py) 与 [PySide6](https://doc.qt.io/qtforpython/) 构建。

### 功能特性

- **文档 → Markdown** — 批量转换 `.doc` / `.docx` / `.pdf`
- **Markdown → 文档** — 导出为 `.docx` 或 `.pdf`
- **导出配置** — 输出格式、页眉页脚、文档属性、样式预设（Typora / GitHub / 经典 / 自定义）；转换方向右侧提供快捷 **配置** 按钮
- **批量处理** — 支持多文件与整个文件夹
- **旧版 `.doc`** — 通过 Microsoft Word 或 LibreOffice 转换
- **PDF 导出** — Markdown 转 PDF 同样依赖 Word 或 LibreOffice
- **拖放文件** — Qt 原生拖放，直接将文件或文件夹拖入窗口
- **递归扫描** — 可选包含子目录
- **深色 / 浅色主题** — 一键切换
- **应用内更新** — 检查 GitHub Releases 并安装新版本
- **进度与日志** — 实时进度条及每个文件的结果

### 下载（Windows 版）

从 **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)** 下载最新版本：

| 包 | 用途 |
|----|------|
| `toMarkdown-vX.X.X-windows-x64.zip` | 绿色版：解压后运行 `toMarkdown.exe` |
| `toMarkdown-vX.X.X-windows-x64-setup.exe` | 安装包（可选安装目录、开始菜单和桌面快捷方式） |

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
2. 若为 **Markdown → 文档**，可点击右侧 **配置** 设置导出格式、样式、页眉页脚等
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
│   ├── converter.py         # 文档 → Markdown
│   ├── md_export.py         # Markdown → Word / PDF
│   ├── export_settings.py   # 导出设置持久化
│   ├── settings_dialog.py   # 导出设置对话框
│   ├── app.py               # GUI（PySide6）
│   ├── theme.py             # 深色 / 浅色主题
│   ├── updater.py           # 应用内更新
│   └── cli.py               # 命令行
├── installer/               # NSIS 安装脚本与图标
├── tests/
├── main.py
└── requirements.txt
```

### 技术栈

| 组件 | 用途 |
|------|------|
| markitdown | 文档转 Markdown |
| markdown-it-py + python-docx | Markdown 转 Word |
| Pygments | 导出 Word 中的代码高亮 |
| Word / LibreOffice | `.doc` 与 PDF 导出 |
| PySide6 | 图形界面（Qt） |

### 开发

```powershell
pip install -e .
pytest tests/
```

推送 `v*` 标签后，GitHub Actions 会自动构建 zip 与 NSIS 安装程序并发布 Release。

---

## License

MIT
