"""
语言配置和检测模块

该模块定义了支持的编程语言配置，并提供语言检测功能。

核心功能:
    - LanguageConfig: 语言配置数据类
    - LANGUAGES: 支持的语言列表 (40+ 种)
    - detect_language(): 根据文件路径检测语言类型

支持的语言类型:
    - 主流编程语言: Python, JavaScript, TypeScript, Java, C/C++, Go, Rust 等
    - 脚本语言: Ruby, PHP, Shell, Lua 等
    - 标记语言: HTML, XML, CSS, Markdown 等
    - 配置文件: JSON, YAML, TOML, INI 等
    - 构建工具: Dockerfile, Makefile, CMake 等

使用方式:
    from code.core.language import detect_language, LanguageConfig

    lang = detect_language("main.py")
    if lang:
        print(f"语言: {lang.name}, 注释符: {lang.line_comments}")
"""

from dataclasses import dataclass, field


@dataclass
class LanguageConfig:
    """
    语言配置数据类

    定义每种编程语言的识别规则和注释格式。

    属性:
        name: 语言名称 (如 "Python", "JavaScript")
        extensions: 关联的文件扩展名列表 (如 [".py", ".pyw"])
        line_comments: 行注释前缀列表 (如 ["#"] 或 ["//"])
        block_comment_start: 块注释开始标记 (如 "/*" 或 "'''")
        block_comment_end: 块注释结束标记 (如 "*/" 或 "'''")

    示例:
        # Python 语言配置
        LanguageConfig("Python", [".py", ".pyw"], ["#"], "'''", "'''")

        # JavaScript 语言配置 (支持两种注释格式)
        LanguageConfig("JavaScript", [".js", ".jsx"], ["//"], "/*", "*/")

        # JSON 配置 (无注释)
        LanguageConfig("JSON", [".json"])
    """
    name: str
    extensions: list[str]
    line_comments: list[str] = field(default_factory=list)
    block_comment_start: str = ""
    block_comment_end: str = ""


# ==================== 支持的语言配置列表 ====================
# 每种语言定义了: 名称、扩展名、行注释符、块注释起止符

LANGUAGES = [
    # -------------------- 主流编程语言 --------------------
    LanguageConfig("Python", [".py", ".pyw"], ["#"], "'''", "'''"),
    LanguageConfig("JavaScript", [".js", ".jsx", ".mjs", ".cjs"], ["//"], "/*", "*/"),
    LanguageConfig("TypeScript", [".ts", ".tsx"], ["//"], "/*", "*/"),
    LanguageConfig("Java", [".java"], ["//"], "/*", "*/"),
    LanguageConfig("C", [".c", ".h"], ["//"], "/*", "*/"),
    LanguageConfig("C++", [".cpp", ".cxx", ".cc", ".hpp", ".hxx", ".hh"], ["//"], "/*", "*/"),
    LanguageConfig("C#", [".cs"], ["//"], "/*", "*/"),
    LanguageConfig("Go", [".go"], ["//"], "/*", "*/"),
    LanguageConfig("Rust", [".rs"], ["//"], "/*", "*/"),
    LanguageConfig("Swift", [".swift"], ["//"], "/*", "*/"),
    LanguageConfig("Kotlin", [".kt", ".kts"], ["//"], "/*", "*/"),
    LanguageConfig("Scala", [".scala"], ["//"], "/*", "*/"),

    # -------------------- 脚本语言 --------------------
    LanguageConfig("Ruby", [".rb", ".rake"], ["#"]),
    LanguageConfig("PHP", [".php", ".phtml"], ["//", "#"], "/*", "*/"),
    LanguageConfig("Perl", [".pl", ".pm", ".t"], ["#"]),
    LanguageConfig("Shell", [".sh", ".bash", ".zsh"], ["#"]),
    LanguageConfig("PowerShell", [".ps1", ".psm1"], ["#"], "<#", "#>"),
    LanguageConfig("Lua", [".lua"], ["--"], "--[[", "]]"),
    LanguageConfig("R", [".r", ".R"], ["#"]),
    LanguageConfig("Dart", [".dart"], ["//"], "/*", "*/"),

    # -------------------- 函数式语言 --------------------
    LanguageConfig("Elixir", [".ex", ".exs"], ["#"]),
    LanguageConfig("Erlang", [".erl", ".hrl"], ["%"]),
    LanguageConfig("Haskell", [".hs", ".lhs"], ["--"], "{-", "-}"),
    LanguageConfig("Clojure", [".clj", ".cljs"], [";;"]),
    LanguageConfig("Lisp", [".lisp", ".lsp"], [";", "#|", "|#"]),

    # -------------------- 数据库/查询 --------------------
    LanguageConfig("SQL", [".sql"], ["--"], "/*", "*/"),
    LanguageConfig("GraphQL", [".graphql", ".gql"], ["#"]),

    # -------------------- 标记语言 --------------------
    LanguageConfig("HTML", [".html", ".htm"], [], "<!--", "-->"),
    LanguageConfig("XML", [".xml", ".svg", ".xaml"], [], "<!--", "-->"),
    LanguageConfig("CSS", [".css", ".scss", ".sass", ".less"], ["//"], "/*", "*/"),
    LanguageConfig("Markdown", [".md", ".markdown"], [], "<!--", "-->"),

    # -------------------- 前端框架 --------------------
    LanguageConfig("Vue", [".vue"], ["//", "<!--", "-->"], "/*", "*/"),

    # -------------------- 鸿蒙开发 --------------------
    LanguageConfig("Harmony", [".ets", ".har"], ["//"], "/*", "*/"),

    # -------------------- 配置/数据格式 --------------------
    # JSON 无注释格式
    LanguageConfig("JSON", [".json"]),
    LanguageConfig("YAML", [".yaml", ".yml"], ["#"]),
    LanguageConfig("TOML", [".toml"], ["#"]),
    LanguageConfig("INI", [".ini", ".cfg", ".conf"], ["#", ";"]),

    # -------------------- 构建/工具 --------------------
    LanguageConfig("Assembly", [".asm", ".s"], [";", "#", "//"]),
    LanguageConfig("Dockerfile", ["Dockerfile", ".dockerfile"], ["#"]),
    LanguageConfig("Makefile", ["Makefile", "makefile", ".mk"], ["#"]),
    LanguageConfig("CMake", ["CMakeLists.txt", ".cmake"], ["#"]),
    LanguageConfig("Protobuf", [".proto"], ["//"], "/*", "*/"),
    LanguageConfig("YARA", [".yara"], ["//"], "/*", "*/"),
]


# ==================== 快速查找映射表 ====================

# 扩展名 -> 语言配置 映射表
# 用于快速根据文件扩展名查找语言配置
# 例如: EXTENSION_MAP[".py"] -> LanguageConfig("Python", ...)
EXTENSION_MAP: dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        EXTENSION_MAP[ext.lower()] = lang

# 特殊文件名映射表
# 用于识别无扩展名的特殊文件 (如 Dockerfile, Makefile)
# 例如: SPECIAL_FILES["dockerfile"] -> LanguageConfig("Dockerfile", ...)
SPECIAL_FILES: dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        if not ext.startswith("."):
            SPECIAL_FILES[ext.lower()] = lang


def detect_language(filepath: str) -> LanguageConfig | None:
    """
    根据文件路径检测语言类型

    检测顺序:
        1. 先检查特殊文件名 (如 Dockerfile, Makefile)
        2. 再检查文件扩展名 (如 .py, .js)

    参数:
        filepath: 文件路径 (绝对路径或相对路径)

    返回:
        LanguageConfig 对象 (识别成功时)
        None (无法识别时)

    示例:
        >>> lang = detect_language("main.py")
        >>> lang.name
        'Python'

        >>> lang = detect_language("Dockerfile")
        >>> lang.name
        'Dockerfile'

        >>> detect_language("unknown.xyz")
        None
    """
    import os

    # 获取文件名并转为小写 (大小写不敏感)
    basename = os.path.basename(filepath).lower()

    # 优先匹配特殊文件名
    if basename in SPECIAL_FILES:
        return SPECIAL_FILES[basename]

    # 通过扩展名匹配
    _, ext = os.path.splitext(basename)
    return EXTENSION_MAP.get(ext)
