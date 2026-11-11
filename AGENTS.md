# AGENTS.md

toMarkdown：Windows 桌面工具，Word / PDF ↔ Markdown 双向批量转换（Python 3.10+，PySide6 GUI + CLI）。当前版本 `0.6.3`（单一来源：`tomarkdown/__init__.py` 的 `__version__`，需与 `pyproject.toml` 同步）。

先读 [doc/code-graph.md](doc/code-graph.md)（模块依赖、调用链、符号索引、测试映射），再定点读源码，避免全仓扫描。

## 目录

| 路径 | 说明 |
| --- | --- |
| `main.py` | GUI 入口 → `tomarkdown.app.run_app` |
| `tomarkdown/` | 主包（见下表） |
| `tests/` | pytest 用例与 `sample.docx` / `sample.pdf` |
| `installer/` | NSIS 脚本与图标 |
| `tomarkdown.spec` | PyInstaller 配置 |
| `.github/workflows/release.yml` | tag 触发的发布流程 |
| `build.bat` / `run.bat` | 本地构建 / 运行 |
| `doc/` | 文档（`code-graph.md` 为手工维护的工程图谱） |
| `example/`、`_batch_test/`、`build/`、`dist/` | 样例与产物，已 gitignore，勿提交 |
| `task_plan.md`、`findings.md`、`progress.md` | 发布过程记录（未跟踪） |

## 包结构（`tomarkdown/`）

| 模块 | 职责 |
| --- | --- |
| `app.py` | 主窗口 `ConverterApp`、`ConvertWorker` 等 QThread 工作线程、拖拽 |
| `cli.py` | 命令行批量转换（`-o -d -f -r --overwrite -v --error-log`） |
| `converter.py` | 转换编排：`convert_batch` / `convert_file` / `collect_files`，`Direction`、`OutputFormat` |
| `docx_outline.py`、`md_outline.py` | 从 docx 编号/样式恢复标题层级并修正 Markdown |
| `md_export.py` | Markdown → docx（样式、代码高亮、表格、页眉页脚）→ PDF |
| `export_settings.py` | `ExportSettings` 模型、预设、JSON 持久化（Windows：`%APPDATA%\toMarkdown\export_settings.json`） |
| `settings_dialog.py` | 导出设置对话框 |
| `theme.py` | 深浅主题 |
| `updater.py` | 检查 GitHub Releases，下载并安装便携 zip |

## 常用命令

```powershell
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt
python main.py                 # 运行 GUI（或 run.bat）
python -m pytest               # 测试；用 python -m 以保证能导入 tomarkdown
build.bat                      # 本地 PyInstaller 打包 zip，检测到 makensis 时再生成安装包
```

## 约定与硬约束

- 转换方向：`to_md`（`.doc/.docx/.pdf` → md）与 `from_md`（`.md/.markdown` → `md/docx/pdf`）。
- `.doc` 转换与 md → PDF 依赖本机 Microsoft Word（pywin32）或 LibreOffice；`.docx` ↔ md 不依赖。
- `md_export.py` 顶层导入 `converter`；`converter.py` 必须在 `_convert_from_md` 内**延迟导入** `md_export`，勿改成顶层导入（循环依赖）。
- 修改 `converter.py` 时保留向后兼容别名（如 `convert_docx_to_md`、`collect_docx_files`、`SUPPORTED_EXTENSIONS`），测试仍在使用。
- 更新器依赖发布的便携 zip 资产名 `toMarkdown-vX.X.X-windows-x64.zip`；改动打包/发布命名需同步 `updater.py`、`build.bat`、`release.yml`、`installer/toMarkdown.nsi`。
- 发布版本时同步更新：`tomarkdown/__init__.py`、`pyproject.toml`；通过推送 `vX.Y.Z` tag 触发发布，禁止改写或删除已有 tag / release。
- 不提交生成产物（`build/`、`dist/`、`.venv/`）、本地助手配置（`.claude/` 等）与测试临时输出。
- GUI 耗时操作必须放在 QThread 工作线程，通过信号回主线程更新界面。
- 最小改动；保留与任务无关的用户修改。

## 改动后检查

1. 运行相关测试：`python -m pytest tests/<对应文件>`（对应关系见 `doc/code-graph.md` 第 6 节）。
2. 新增/删除/重命名模块、改变依赖关系时，同步更新 `doc/code-graph.md`。
3. 汇报实际验证结果与未覆盖项（如无 Word / LibreOffice / NSIS 环境）。

## 说明

- `doc/codemap-guide.md` 描述的 `pnpm codemap` / `CODE_MAP.md` 方案面向其他（Rust/TS）项目；本仓库没有 `codemap.mjs`、`package.json`，不要执行这些命令。
