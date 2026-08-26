# AGENTS.md

CodeStat —— 代码量统计 Python 命令行工具（统计各编程语言代码行数）。所有注释、docstring、用户可见字符串均为**中文**，新代码请保持一致。

## 常用命令（依赖 uv，环境 Python 3.13）

```bash
uv sync --all-extras   # 安装（含 dev：pytest / pytest-cov）
pytest                 # 跑全部测试（tests/unit + tests/integration）
pytest tests/unit/ -v  # 跑某个目录
pytest tests/unit/test_stats.py -v   # 跑单个文件
ruff check .           # lint（pyproject 已配置）
python -m codestat .   # 命令行运行（等效 codestat）
```

- 用 `uv` 管理依赖（`uv.lock` 已提交），不要用 pip 装包。
- Ruff 已配置：`select = E,F,W,I,UP`，`line-length=100`，`ignore=E501`。改动后跑 `ruff check .`。
- pytest 默认 `addopts = -v --tb=short`，无需额外参数。

## 结构要点

- 包 `codestat/`，入口 `codestat/cli/main.py`（`main()` 可接收 `args` 列表，用于测试）。
- `codestat/core/__init__.py` 重导出 `scan_directory` / `collect_code_files` / `detect_language` 等，CLI 和测试均通过 `codestat.core` 导入。新增 core 功能时记得在 `__init__.py` 的 `__all__` 里补上。
- 语言定义集中在 `codestat/core/language.py` 的 `LANGUAGES` 列表（扩展名 + 行/块注释符）。新增语言在此处加配置即可，`EXTENSION_MAP`/`SPECIAL_FILES` 会自动生成。
- 排除规则合并顺序：`DEFAULT_EXCLUDE`（config.py）→ `.codestatignore` → 命令行 `--exclude`。三者取并集。

## 关键依赖

- `python-docx` 是**运行时依赖**，仅 `word.py` 导出用到。改 Word 导出需保证该依赖可用。
- `pytest-cov` 只在 dev 依赖中，覆盖率需要 `--all-extras` 安装后运行。

## 潜在坑

- 默认会统计仓库自身，运行时若不想把 `.venv` 统计进去，默认 `DEFAULT_EXCLUDE` 已含 `.venv`。
- `count_lines` 对 UTF-8 解码失败文件静默跳过（`errors="ignore"`），二进制/编码异常文件不计入 —— 改统计逻辑时注意不要破坏此行为。
- 集成测试依赖 `conftest.py` 的 `sample_directory` fixture（临时目录中的 .py/.js 样例文件）。
