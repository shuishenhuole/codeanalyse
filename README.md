# CodeStat - 代码量统计工具

一个轻量级的 Python 命令行工具，用于统计项目中各编程语言的代码行数。

## 项目结构

```
codestat/
├── codestat/
│   ├── __init__.py          # 包入口
│   ├── __main__.py          # 模块入口
│   ├── config.py            # 配置常量
│   ├── exceptions.py        # 自定义异常
│   ├── core/                # 核心模块
│   │   ├── language.py      # 语言检测
│   │   ├── stats.py         # 行统计
│   │   └── scanner.py       # 目录扫描
│   ├── exporters/           # 导出模块
│   │   ├── table.py         # 终端表格
│   │   ├── json.py          # JSON 导出
│   │   ├── csv.py           # CSV 导出
│   │   └── word.py          # Word 导出
│   └── cli/                 # 命令行
│       └── main.py          # CLI 入口
│   └── gui/                 # 图形界面 (PySide6)
│       ├── main.py          # GUI 主窗口
│       └── __main__.py      # GUI 模块入口
├── gui_run.py               # GUI 独立入口脚本
├── tests/                   # 测试
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── conftest.py          # pytest 配置
├── pyproject.toml           # 项目配置
└── README.md
```

## 特性

- 支持 40+ 种编程语言和文件格式
- 区分代码行、注释行、空行
- 支持终端表格、JSON、CSV、Word 四种输出格式
- 自动排除 `.git`、`node_modules` 等常见目录
- 支持 `.codestatignore` 文件自定义排除规则
- Word 导出支持最多60页代码内容

## 快速开始

```bash
# 安装项目
uv sync

# 统计当前目录
python -m codestat

# 统计指定目录
python -m codestat src/

# 或直接使用命令 (安装后)
codestat
codestat src/

# 启动图形界面 (GUI)
python gui_run.py

# 或作为模块启动 GUI
python -m codestat.gui
```

## 运行测试

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ --cov=codestat
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `directory` | - | 要统计的目录路径 | 当前目录 |
| `--exclude` | `-e` | 排除的目录或文件名 | - |
| `--format` | `-f` | 输出格式: `table` / `json` / `csv` / `word` | `table` |
| `--output` | `-o` | 输出文件路径 | `codestat.json` / `codestat.csv` / `codestat.docx` |

## 使用示例

```bash
# 统计当前目录，终端表格输出
python -m codestat

# 统计 src 目录
python -m codestat src/

# 排除 test 和 docs 目录
python -m codestat . --exclude test docs

# 导出为 JSON 文件
python -m codestat . --format json -o stats.json

# 导出为 CSV 文件
python -m codestat . --format csv -o stats.csv

# 导出为 Word 文档 (最多60页)
python -m codestat . --format word -o code.docx
```

## 输出示例

### 终端表格

```
+------------+--------+--------+---------+-------+-------+
| Language   |  Files |   Code | Comment | Blank | Total |
+------------+--------+--------+---------+-------+-------+
| Python     |     12 |    856 |     120 |    89 |  1065 |
| TypeScript |      8 |    432 |      56 |    45 |   533 |
| HTML       |      3 |    210 |       0 |    12 |   222 |
+------------+--------+--------+---------+-------+-------+
| Total      |     23 |   1498 |     176 |   146 |  1820 |
+------------+--------+--------+---------+-------+-------+
```

### JSON

```json
[
  {
    "language": "Python",
    "files": 12,
    "code": 856,
    "comment": 120,
    "blank": 89,
    "total": 1065
  }
]
```

### CSV

```csv
Language,Files,Code,Comment,Blank,Total
Python,12,856,120,89,1065
```

### Word 文档

Word 导出会生成包含以下内容的文档：
- 项目路径和统计概览表格
- 按语言分组的代码内容
- 每个文件包含文件路径和语言标签
- 使用等宽字体 (Courier New) 格式化代码
- 自动限制最多60页内容

## 排除规则

### 默认排除目录

以下目录会被自动排除：

```
.git  .svn  .hg  node_modules  __pycache__  .pytest_cache
venv  env  .env  .venv  .idea  .vscode  .vs  dist  build
out  target  .gradle  .maven  vendor  Pods  coverage
.nyc_output  .tox  .eggs
```

### 自定义排除

在项目根目录创建 `.codestatignore` 文件，每行一个排除项：

```
# 这是注释
test
fixtures
mock_data
```

也可以通过命令行参数排除：

```bash
python codestat.py . --exclude test fixtures mock_data
```

## 支持的语言

| 类别 | 语言 |
|------|------|
| 编程语言 | Python, JavaScript, TypeScript, Java, C, C++, C#, Go, Rust, Swift, Kotlin, Scala |
| 脚本语言 | Ruby, PHP, Perl, Shell, PowerShell, Lua, R, Dart |
| 函数式 | Elixir, Erlang, Haskell, Clojure, Lisp |
| 标记语言 | HTML, XML, CSS, Markdown, Vue |
| 数据格式 | JSON, YAML, TOML, INI |
| 数据库 | SQL, GraphQL |
| 鸿蒙开发 | ETS, HAR |
| 构建工具 | Dockerfile, Makefile, CMake, Protobuf, Assembly |

## 许可证

MIT
