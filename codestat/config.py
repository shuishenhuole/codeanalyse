"""
配置管理模块

该模块定义了 CodeStat 工具的全局配置常量，包括:
    - 默认排除的目录集合
    - 排除规则文件名
    - Word 文档导出的页数限制

使用方式:
    from code.config import DEFAULT_EXCLUDE, IGNORE_FILE_NAME
"""

# 默认排除的目录集合
# 包含版本控制、依赖管理、IDE 配置、编译产物等常见无需统计的目录
DEFAULT_EXCLUDE = {
    # 版本控制系统
    ".git", ".svn", ".hg",
    # Node.js / JavaScript 依赖
    "node_modules",
    # Python 相关
    "__pycache__", ".pytest_cache",
    "venv", "env", ".env", ".venv", ".tox", ".eggs",
    # IDE / 编辑器配置
    ".idea", ".vscode", ".vs",
    # 编译产物目录
    "dist", "build", "out", "target",
    # Java 构建工具
    ".gradle", ".maven",
    # 其他语言依赖
    "vendor", "Pods",
    # 测试覆盖率报告
    "coverage", ".nyc_output",
}

# 排除规则文件名
# 在项目根目录创建此文件可自定义排除规则
IGNORE_FILE_NAME = ".codestatignore"

# Word 文档最大页数限制
# 防止生成的文档过大
MAX_WORD_PAGES = 60

# 每页预估行数
# 用于计算 Word 文档内容截断点
# 按 A4 页面、Noto Sans SC 9pt、单倍行距实测每页约 37 行
# (每个文件另有固定开销折算，见 FILE_OVERHEAD_LINES)
LINES_PER_PAGE = 37

# Word 文档使用的中文字体
# 同时设置东亚字体，确保中文正确渲染
WORD_FONT_NAME = "Noto Sans SC"

# 每个文件在 Word 文档中的固定开销 (标题 + 语言标签 + 段落间距)
# 折算为等效代码行数，用于页数控制估算
FILE_OVERHEAD_LINES = 7
