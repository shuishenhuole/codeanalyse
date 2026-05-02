"""单元测试 - 行统计"""

import pytest

from codestat.core.stats import LineStats, count_lines
from codestat.core.language import detect_language


class TestLineStats:
    """LineStats 数据类测试"""

    def test_initial_values(self):
        """测试初始值"""
        stats = LineStats()
        assert stats.total == 0
        assert stats.code == 0
        assert stats.comment == 0
        assert stats.blank == 0

    def test_iadd_operator(self):
        """测试累加操作"""
        stats1 = LineStats(code=10, comment=2, blank=3, total=15)
        stats2 = LineStats(code=5, comment=1, blank=2, total=8)
        stats1 += stats2
        assert stats1.code == 15
        assert stats1.comment == 3
        assert stats1.blank == 5
        assert stats1.total == 23


class TestCountLines:
    """行统计测试"""

    def test_count_python_file(self, tmp_path):
        """测试 Python 文件行统计"""
        py_file = tmp_path / "test.py"
        py_file.write_text("""# 注释行
def hello():
    print("Hello")

# 另一个注释
x = 1
""")
        lang = detect_language(str(py_file))
        stats = count_lines(str(py_file), lang)

        assert stats.total >= 6
        assert stats.blank >= 1
        assert stats.comment >= 2
        assert stats.code >= 3

    def test_count_empty_file(self, tmp_path):
        """测试空文件"""
        empty_file = tmp_path / "empty.py"
        empty_file.write_text("")
        lang = detect_language(str(empty_file))
        stats = count_lines(str(empty_file), lang)

        assert stats.total == 0
        assert stats.code == 0
        assert stats.comment == 0
        assert stats.blank == 0

    def test_count_only_comments(self, tmp_path):
        """测试纯注释文件"""
        comment_file = tmp_path / "comments.py"
        comment_file.write_text("# comment 1\n# comment 2\n# comment 3\n")
        lang = detect_language(str(comment_file))
        stats = count_lines(str(comment_file), lang)

        assert stats.comment == 3
        assert stats.code == 0