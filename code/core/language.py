"""语言配置和检测"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LanguageConfig:
    """
    语言配置类

    属性:
        name: 语言名称
        extensions: 文件扩展名列表
        line_comments: 行注释前缀
        block_comment_start: 块注释开始标记
        block_comment_end: 块注释结束标记
    """
    name: str
    extensions: List[str]
    line_comments: List[str] = field(default_factory=list)
    block_comment_start: str = ""
    block_comment_end: str = ""


LANGUAGES = [
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
    LanguageConfig("Ruby", [".rb", ".rake"], ["#"]),
    LanguageConfig("PHP", [".php", ".phtml"], ["//", "#"], "/*", "*/"),
    LanguageConfig("Perl", [".pl", ".pm", ".t"], ["#"]),
    LanguageConfig("Shell", [".sh", ".bash", ".zsh"], ["#"]),
    LanguageConfig("PowerShell", [".ps1", ".psm1"], ["#"], "<#", "#>"),
    LanguageConfig("Lua", [".lua"], ["--"], "--[[", "]]"),
    LanguageConfig("SQL", [".sql"], ["--"], "/*", "*/"),
    LanguageConfig("HTML", [".html", ".htm"], [], "<!--", "-->"),
    LanguageConfig("XML", [".xml", ".svg", ".xaml"], [], "<!--", "-->"),
    LanguageConfig("CSS", [".css", ".scss", ".sass", ".less"], ["//"], "/*", "*/"),
    LanguageConfig("Vue", [".vue"], ["//", "<!--", "-->"], "/*", "*/"),
    LanguageConfig("Harmony", [".ets", ".har"], ["//"], "/*", "*/"),
    LanguageConfig("JSON", [".json"]),
    LanguageConfig("YAML", [".yaml", ".yml"], ["#"]),
    LanguageConfig("TOML", [".toml"], ["#"]),
    LanguageConfig("INI", [".ini", ".cfg", ".conf"], ["#", ";"]),
    LanguageConfig("Markdown", [".md", ".markdown"], [], "<!--", "-->"),
    LanguageConfig("R", [".r", ".R"], ["#"]),
    LanguageConfig("Dart", [".dart"], ["//"], "/*", "*/"),
    LanguageConfig("Elixir", [".ex", ".exs"], ["#"]),
    LanguageConfig("Erlang", [".erl", ".hrl"], ["%"]),
    LanguageConfig("Haskell", [".hs", ".lhs"], ["--"], "{-", "-}"),
    LanguageConfig("Clojure", [".clj", ".cljs"], [";;"]),
    LanguageConfig("Lisp", [".lisp", ".lsp"], [";", "#|", "|#"]),
    LanguageConfig("Assembly", [".asm", ".s"], [";", "#", "//"]),
    LanguageConfig("Dockerfile", ["Dockerfile", ".dockerfile"], ["#"]),
    LanguageConfig("Makefile", ["Makefile", "makefile", ".mk"], ["#"]),
    LanguageConfig("CMake", ["CMakeLists.txt", ".cmake"], ["#"]),
    LanguageConfig("Protobuf", [".proto"], ["//"], "/*", "*/"),
    LanguageConfig("GraphQL", [".graphql", ".gql"], ["#"]),
    LanguageConfig("YARA", [".yara"], ["//"], "/*", "*/"),
]

EXTENSION_MAP: Dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        EXTENSION_MAP[ext.lower()] = lang

SPECIAL_FILES: Dict[str, LanguageConfig] = {}
for lang in LANGUAGES:
    for ext in lang.extensions:
        if not ext.startswith("."):
            SPECIAL_FILES[ext.lower()] = lang


def detect_language(filepath: str) -> Optional[LanguageConfig]:
    """检测文件语言类型"""
    import os
    basename = os.path.basename(filepath).lower()

    if basename in SPECIAL_FILES:
        return SPECIAL_FILES[basename]

    _, ext = os.path.splitext(basename)
    return EXTENSION_MAP.get(ext)