"""
CLI 模块

该模块提供命令行接口功能。

主要功能:
    - main(): 命令行主入口函数
    - create_parser(): 创建参数解析器

使用方式:
    # 作为命令行工具
    python -m code
    
    # 作为模块导入
    from code.cli import main
    
    # 直接调用 (用于测试)
    main(["./src", "--format", "json"])
"""

from .main import main, create_parser

__all__ = [
    "main",          # 命令行主入口
    "create_parser", # 参数解析器
]