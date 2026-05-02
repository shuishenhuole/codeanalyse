"""单元测试 - 语言检测"""

import pytest

from codestat.core.language import detect_language, LanguageConfig, LANGUAGES


class TestDetectLanguage:
    """语言检测测试类"""

    def test_detect_python(self):
        """测试 Python 文件检测"""
        result = detect_language("test.py")
        assert result is not None
        assert result.name == "Python"

    def test_detect_javascript(self):
        """测试 JavaScript 文件检测"""
        result = detect_language("app.js")
        assert result is not None
        assert result.name == "JavaScript"

    def test_detect_typescript(self):
        """测试 TypeScript 文件检测"""
        result = detect_language("component.tsx")
        assert result is not None
        assert result.name == "TypeScript"

    def test_detect_dockerfile(self):
        """测试 Dockerfile 检测"""
        result = detect_language("Dockerfile")
        assert result is not None
        assert result.name == "Dockerfile"

    def test_detect_unknown(self):
        """测试未知文件类型"""
        result = detect_language("unknown.xyz")
        assert result is None

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        result1 = detect_language("Test.PY")
        result2 = detect_language("test.py")
        assert result1.name == result2.name


class TestLanguageConfig:
    """语言配置测试类"""

    def test_python_has_block_comment(self):
        """测试 Python 块注释配置"""
        for lang in LANGUAGES:
            if lang.name == "Python":
                assert lang.block_comment_start == "'''"
                assert lang.block_comment_end == "'''"
                assert "#" in lang.line_comments

    def test_json_no_comments(self):
        """测试 JSON 无注释配置"""
        for lang in LANGUAGES:
            if lang.name == "JSON":
                assert len(lang.line_comments) == 0
                assert lang.block_comment_start == ""