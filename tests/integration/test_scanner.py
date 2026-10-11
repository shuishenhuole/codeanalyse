"""集成测试 - 目录扫描"""

from codestat.core.scanner import scan_directory


class TestScanDirectory:
    """目录扫描测试"""

    def test_scan_basic(self, sample_directory):
        """测试基本扫描"""
        results = scan_directory(str(sample_directory))

        assert "Python" in results
        assert "JavaScript" in results

        py_count, py_stats = results["Python"]
        assert py_count == 1
        assert py_stats.total > 0

    def test_scan_with_exclude(self, sample_directory):
        """测试排除目录"""
        # 创建应被排除的目录
        excluded_dir = sample_directory / "test_excluded"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "excluded.py"
        excluded_file.write_text("def excluded(): pass")

        results = scan_directory(str(sample_directory), extra_excludes={"test_excluded"})

        # 排除目录中的文件不应被统计
        assert results.get("Python", (0, None))[0] == 1

    def test_scan_empty_directory(self, tmp_path):
        """测试空目录"""
        results = scan_directory(str(tmp_path))
        assert len(results) == 0

    def test_scan_exclude_by_suffix(self, sample_directory):
        """测试按文件后缀排除 (小写)"""
        results = scan_directory(str(sample_directory), extra_excludes={"js"})

        # .js 文件应被排除, .py 保留
        assert "JavaScript" not in results
        assert "Python" in results

    def test_scan_exclude_by_suffix_with_dot(self, sample_directory):
        """测试带点后缀和大小写不敏感"""
        results = scan_directory(str(sample_directory), extra_excludes={"PY"})

        assert "Python" not in results
        assert "JavaScript" in results
