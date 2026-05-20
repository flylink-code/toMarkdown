# toMarkdown

使用 Python + [markitdown](https://github.com/microsoft/markitdown) 批量将 `.docx` 文件转换为 Markdown 的 CLI 工具。

## 安装

```bash
pip install -r requirements.txt
```

或以可编辑模式安装（注册 `tomd` 命令）：

```bash
pip install -e .
```

## 用法

### 直接运行

```bash
python main.py input.docx
python main.py docs/ -o output/ -r
```

### 安装后使用 `tomd` 命令

```bash
tomd input.docx
tomd docs/ -o output/ -r --overwrite -v
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `input` | 输入文件或目录（必填） |
| `-o, --output` | 输出目录（默认与输入同目录） |
| `-r, --recursive` | 递归处理子目录中的 `.docx` 文件 |
| `--overwrite` | 覆盖已存在的 `.md` 文件 |
| `-v, --verbose` | 显示详细处理日志 |
| `--error-log` | 失败记录日志路径（默认 `errors.log`） |

## 示例

```bash
# 单文件转换
tomd report.docx -o output/

# 批量递归转换
tomd docs/ -o output/ -r

# 覆盖已有输出并显示详细日志
tomd docs/ -o output/ -r --overwrite -v
```

转换完成后会打印汇总，例如：

```
汇总: 成功 9 / 失败 1 (共 10 个文件)
```

## 开发

```bash
pip install -e ".[dev]"  # 可选：若添加了 dev 依赖
pytest tests/
```

## 项目结构

```
toMarkdown/
├── tomarkdown/
│   ├── __init__.py
│   ├── converter.py      # 核心转换逻辑
│   └── cli.py              # CLI 入口
├── tests/
│   ├── sample.docx
│   └── test_converter.py
├── main.py
├── pyproject.toml
├── requirements.txt
└── README.md
```
