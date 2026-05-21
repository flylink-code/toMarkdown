# toMarkdown

**Word → Markdown Converter** — A desktop GUI tool to batch-convert `.doc` / `.docx` files to Markdown.

[English](#english) · [中文](#中文)

[![Release](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml/badge.svg)](https://github.com/flylink-code/toMarkdown/actions/workflows/release.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## English

### Overview

**toMarkdown** is a lightweight Windows desktop application that converts Microsoft Word documents (`.doc` and `.docx`) to clean Markdown files. Built with Python, [markitdown](https://github.com/microsoft/markitdown), and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), it offers a modern GUI with drag-and-drop support, batch processing, and real-time progress tracking.

### Features

- **Batch conversion** — Process multiple files or entire folders at once
- **Legacy `.doc` support** — Converts old Word format via Microsoft Word or LibreOffice
- **Drag & drop** — Drop files or folders directly into the window
- **Recursive scan** — Optionally include subdirectories
- **Dark / Light theme** — Toggle appearance with one click
- **Progress & logs** — Live progress bar and per-file success/failure log
- **Open output folder** — Quick access to converted files after completion

### Download (Windows)

Download the latest release from **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)**:

1. Download `toMarkdown-vX.X.X-windows-x64.zip`
2. Extract to any folder
3. Run `toMarkdown.exe`

> **Note:** Converting `.doc` files requires **Microsoft Word** or **LibreOffice** installed on your system. `.docx` files work out of the box.

### Run from Source

**Requirements:** Python 3.10+, Windows 10/11

```powershell
# Clone the repository
git clone https://github.com/flylink-code/toMarkdown.git
cd toMarkdown

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch GUI
python main.py
```

Or double-click `run.bat` (auto-activates `.venv`).

### Usage

1. **Add files** — Click "+ Add Files" / "+ Add Folder", or drag files into the window
2. **Set output directory** — Defaults to the same folder as input files
3. **Options** — Enable "Recursive subdirectories" or "Overwrite existing files" as needed
4. **Convert** — Click "Start Conversion" and wait for the summary dialog

### Project Structure

```
toMarkdown/
├── tomarkdown/
│   ├── converter.py      # Core conversion logic (no GUI)
│   └── app.py              # CustomTkinter GUI
├── tests/
├── main.py                 # Application entry point
├── run.bat                 # Windows quick-start script
├── tomarkdown.spec         # PyInstaller build config
└── requirements.txt
```

### Tech Stack

| Component | Purpose |
|-----------|---------|
| [markitdown](https://github.com/microsoft/markitdown) | Document → Markdown conversion |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Modern GUI framework |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | Drag-and-drop support |
| pywin32 | `.doc` conversion via Word COM (Windows) |

### Build Windows Release

```powershell
pip install pyinstaller
pyinstaller --noconfirm tomarkdown.spec
# Output: dist/toMarkdown/toMarkdown.exe
```

Push a version tag to trigger CI release:

```bash
git tag v0.2.0
git push origin v0.2.0
```

### Development

```powershell
pip install -e ".[dev]"
pytest tests/
```

---

## 中文

### 项目简介

**toMarkdown** 是一款轻量级 Windows 桌面工具，用于将 Microsoft Word 文档（`.doc` / `.docx`）批量转换为 Markdown 文件。基于 Python、[markitdown](https://github.com/microsoft/markitdown) 和 [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) 构建，提供现代化图形界面，支持拖放操作、批量处理和实时进度显示。

### 功能特性

- **批量转换** — 一次处理多个文件或整个文件夹
- **支持 `.doc` 旧格式** — 通过 Microsoft Word 或 LibreOffice 转换
- **拖放文件** — 直接将文件或文件夹拖入窗口
- **递归扫描** — 可选包含子目录中的 Word 文件
- **深色 / 浅色主题** — 一键切换界面风格
- **进度与日志** — 实时进度条及每个文件的转换结果
- **打开输出目录** — 转换完成后快速查看结果

### 下载（Windows 版）

从 **[GitHub Releases](https://github.com/flylink-code/toMarkdown/releases)** 下载最新版本：

1. 下载 `toMarkdown-vX.X.X-windows-x64.zip`
2. 解压到任意目录
3. 运行 `toMarkdown.exe`

> **说明：** 转换 `.doc` 文件需要系统已安装 **Microsoft Word** 或 **LibreOffice**；`.docx` 文件可直接转换。

### 从源码运行

**环境要求：** Python 3.10+，Windows 10/11

```powershell
# 克隆仓库
git clone https://github.com/flylink-code/toMarkdown.git
cd toMarkdown

# 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动 GUI
python main.py
```

也可直接双击 `run.bat`（自动激活虚拟环境）。

### 使用方法

1. **添加文件** — 点击「+ 添加文件」/「+ 添加文件夹」，或将文件拖入窗口
2. **设置输出目录** — 默认与输入文件同目录
3. **选项** — 按需勾选「递归子目录」「覆盖已有文件」
4. **开始转换** — 点击「开始转换」，等待摘要对话框弹出

### 项目结构

```
toMarkdown/
├── tomarkdown/
│   ├── converter.py      # 核心转换逻辑（无 GUI 依赖）
│   └── app.py              # CustomTkinter 图形界面
├── tests/
├── main.py                 # 程序入口
├── run.bat                 # Windows 一键启动
├── tomarkdown.spec         # PyInstaller 打包配置
└── requirements.txt
```

### 技术栈

| 组件 | 用途 |
|------|------|
| [markitdown](https://github.com/microsoft/markitdown) | 文档转 Markdown |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 GUI 框架 |
| [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2) | 拖放文件支持 |
| pywin32 | 通过 Word COM 转换 `.doc`（Windows） |

### 打包 Windows 发布版

```powershell
pip install pyinstaller
pyinstaller --noconfirm tomarkdown.spec
# 输出: dist/toMarkdown/toMarkdown.exe
```

推送版本标签即可触发 CI 自动发布：

```bash
git tag v0.2.0
git push origin v0.2.0
```

### 开发

```powershell
pip install -e .
pytest tests/
```

---

## License

MIT
