# CodeStat - 代码量统计工具

一个轻量级的 Python 命令行工具，用于统计项目中各编程语言的代码行数。

## 特性

- 支持 40+ 种编程语言和文件格式
- 区分代码行、注释行、空行
- 支持终端表格、JSON、CSV 三种输出格式
- 自动排除 `.git`、`node_modules` 等常见目录
- 支持 `.codestatignore` 文件自定义排除规则
- 纯标准库实现，无需安装第三方依赖

## 快速开始

```bash
# 统计当前目录
python codestat.py

# 统计指定目录
python codestat.py src/
```

## 命令行参数

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `directory` | - | 要统计的目录路径 | 当前目录 |
| `--exclude` | `-e` | 排除的目录或文件名 | - |
| `--format` | `-f` | 输出格式: `table` / `json` / `csv` | `table` |
| `--output` | `-o` | 输出文件路径 (json/csv 格式) | `codestat.json` / `codestat.csv` |

## 使用示例

```bash
# 统计当前目录，终端表格输出
python codestat.py

# 统计 src 目录
python codestat.py src/

# 排除 test 和 docs 目录
python codestat.py . --exclude test docs

# 导出为 JSON 文件
python codestat.py . --format json -o stats.json

# 导出为 CSV 文件
python codestat.py . --format csv -o stats.csv
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
