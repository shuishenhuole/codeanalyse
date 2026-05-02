"""配置管理"""

DEFAULT_EXCLUDE = {
    ".git", ".svn", ".hg",
    "node_modules",
    "__pycache__", ".pytest_cache",
    "venv", "env", ".env", ".venv", ".tox", ".eggs",
    ".idea", ".vscode", ".vs",
    "dist", "build", "out", "target",
    ".gradle", ".maven",
    "vendor", "Pods",
    "coverage", ".nyc_output",
}

IGNORE_FILE_NAME = ".codestatignore"
MAX_WORD_PAGES = 60
LINES_PER_PAGE = 30