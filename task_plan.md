# Task Plan: Word to Markdown Converter (GUI)

## Goal
使用 Python + markitdown + customtkinter 实现带图形界面的 .docx 转 Markdown 工具，运行于虚拟 Python 环境。

## Tech Stack
- Python 3.10+（虚拟环境 `.venv`）
- [markitdown](https://github.com/microsoft/markitdown) — Word/PDF 转 Markdown
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — 现代风格 GUI（深色/浅色主题）
- pathlib — 文件路径处理

---

## Phases

### Phase 1: 虚拟环境搭建 `[ ]`
- [ ] 在项目根目录创建虚拟环境：`python -m venv .venv`
- [ ] 创建 `requirements.txt`：
  ```
  markitdown[docx]
  customtkinter
  ```
- [ ] 激活虚拟环境并安装依赖
- [ ] 验证 `markitdown` 和 `customtkinter` 均可 import

**验收**: `.venv` 目录存在，依赖安装无报错

---

### Phase 2: 核心转换模块 `[ ]`
- [ ] 创建 `tomarkdown/converter.py`
- [ ] 实现 `convert_file(src: Path, dst: Path) -> bool` 单文件转换
- [ ] 实现 `convert_batch(files, out_dir, callback) -> dict` 批量转换（支持进度回调）
- [ ] 统一异常处理，返回成功/失败状态

**验收**: 给定 .docx 文件，输出合法 .md 文件

---

### Phase 3: GUI 主界面 `[ ]`
- [ ] 创建 `tomarkdown/app.py`，基于 `customtkinter.CTk`
- [ ] 界面布局：
  - **顶部**: 主题切换按钮（深色/浅色）
  - **输入区**: 点击选择文件/文件夹，显示已选文件列表（文件名、大小、状态）
  - **输出区**: 选择输出目录（默认与输入同目录）
  - **选项区**: "递归子目录" 复选框、"覆盖已有文件" 复选框
  - **操作区**: "开始转换" 按钮、进度条
  - **日志区**: 滚动文本框，实时显示转换日志
- [ ] 转换在后台线程执行，不阻塞 GUI
- [ ] 转换完成弹出结果摘要对话框

**验收**: 界面可正常打开，按钮/布局无错位

---

### Phase 4: 结果与日志 `[ ]`
- [ ] 进度条实时更新（已完成数/总数）
- [ ] 日志区显示每个文件转换结果（成功/失败标记）
- [ ] 转换结束后显示摘要：成功 N 个 / 失败 N 个
- [ ] "打开输出目录" 按钮，转换完成后快速浏览结果

**验收**: 批量转换后，日志区和摘要信息正确显示

---

### Phase 5: 启动脚本 `[ ]`
- [ ] 创建 `run.bat`（Windows 一键启动，自动激活虚拟环境并运行 `main.py`）

**验收**: 双击 `run.bat` 可直接打开 GUI

---

## Directory Structure (目标)
```
toMarkdown/
├── .venv/                  # 虚拟 Python 环境
├── tomarkdown/
│   ├── __init__.py
│   ├── converter.py        # 核心转换逻辑（纯功能，无 GUI）
│   └── app.py              # customtkinter GUI 主窗口
├── main.py                 # 入口：启动 GUI
├── run.bat                 # Windows 一键启动脚本
└── requirements.txt
```

---

## UI Wireframe（界面草图）
```
┌─────────────────────────────────────────────┐
│  Word → Markdown 转换器          [🌙 深色] │
├─────────────────────────────────────────────┤
│  输入文件                                   │
│  ┌─────────────────────────────────────┐   │
│  │ 文件名          大小    状态         │   │
│  │ report.docx     120KB   待处理       │   │
│  │ manual.docx     350KB   待处理       │   │
│  └─────────────────────────────────────┘   │
│  [+ 添加文件]  [+ 添加文件夹]  [清空]      │
├─────────────────────────────────────────────┤
│  输出目录: C:\output\         [浏览...]     │
│  ☑ 递归子目录   ☐ 覆盖已有文件             │
├─────────────────────────────────────────────┤
│  [████████░░░░░░░░░░] 4 / 10               │
│  [        开始转换        ]                 │
├─────────────────────────────────────────────┤
│  日志:                                      │
│  ✅ report.docx → report.md                │
│  ❌ broken.docx → 解析失败                 │
└─────────────────────────────────────────────┘
```

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| — | — | — |

---

## Decisions Log
| Decision | Reason |
|----------|--------|
| customtkinter 替代原生 tkinter | 现代 UI 风格，内置深色模式，无需系统依赖 |
| 虚拟环境隔离依赖 | 避免污染系统 Python，便于分发和复现 |
| 转换逻辑与 GUI 分离 | converter.py 可独立测试，不依赖 GUI |
| 后台线程执行转换 | 防止长时间转换冻结界面 |

---

## Status
- 当前阶段: Phase 1 未开始
- 最后更新: 2026-05-20
