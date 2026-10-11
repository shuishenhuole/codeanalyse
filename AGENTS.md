# AGENTS.md

This file provides guidance to the AI agent when working with code in this repository.

CodeStat —— 基于 Flet 的代码量统计桌面应用（统计各编程语言代码行数）。所有注释、docstring、用户可见字符串均为**中文**，新代码请保持一致。

## 常用命令（依赖 uv）

```bash
uv sync                      # 安装依赖
uv run flet run              # 启动桌面应用（--web 启动网页版）
uv run pytest tests/unit tests/integration -v   # 核心逻辑测试
uv run ruff check .          # lint（pyproject 已配置）
```

- 用 `uv` 管理依赖（`uv.lock` 已提交），不要用 pip 装包。
- `tests/test_main.py` 是 Flet 冒烟测试，需要 Flutter 环境构建 headless runner；构建失败时可用上面的 pytest 命令跳过它。
- Ruff 已配置：`select = E,F,W,I,UP`，`line-length=100`，`ignore=E501`。
- Flet 版本为 1.x，API 与旧版 0.2x 差异较大（服务用 `page.services`，`ft.run(main)` 同步入口，控件字段名如 `horizontal_lines` 而非 `divider_color`），改动前先 introspect 已安装的 flet。

## 结构要点

- Flet 入口 `src/main.py`（`[tool.flet.app] path = "src"`），业务逻辑在 `src/codestat/` 包，测试靠 `pythonpath = ["src"]` 导入 `codestat.*`。
- `src/codestat/core/__init__.py` 重导出 `scan_directory` / `collect_code_files` / `detect_language` 等，UI 和测试均通过 `codestat.core` 导入。新增 core 功能时记得在 `__all__` 里补上。
- 语言定义集中在 `src/codestat/core/language.py` 的 `LANGUAGES` 列表（扩展名 + 行/块注释符），`EXTENSION_MAP`/`SPECIAL_FILES` 会自动生成。
- 排除规则合并顺序：`DEFAULT_EXCLUDE`（config.py）→ `.codestatignore` → 界面"排除项"输入。三者取并集。

## 潜在坑

- 本项目自身会被统计：`DEFAULT_EXCLUDE` 已含 `.venv`、`build` 等。
- `count_lines` 对 UTF-8 解码失败文件静默跳过（`errors="ignore"`），二进制/编码异常文件不计入 —— 改统计逻辑时注意不要破坏此行为。
- `python-docx` 是运行时依赖，仅 Word 导出用到。
- 集成测试依赖 `conftest.py` 的 `sample_directory` fixture（临时目录中的 .py/.js 样例文件）。
- 扫描在 `threading.Thread` 中执行，UI 更新必须经 `page.run_thread()` 回主线程。
