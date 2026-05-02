"""测试配置"""

import pytest


@pytest.fixture
def sample_directory(tmp_path):
    """
    创建示例目录结构用于测试

    参数:
        tmp_path: pytest 提供的临时目录

    返回:
        临时目录路径
    """
    # 创建 Python 文件
    py_file = tmp_path / "sample.py"
    py_file.write_text("""
# 这是注释
def hello():
    print("Hello, World!")

# 另一个注释
def add(a, b):
    return a + b
""")

    # 创建 JavaScript 文件
    js_file = tmp_path / "sample.js"
    js_file.write_text("""
// JavaScript comment
function greet() {
    console.log("Hello");
}
""")

    return tmp_path