"""
自定义异常模块

该模块定义了 CodeStat 工具的异常体系，用于统一错误处理。

异常层级:
    CodeStatError (基类)
        ├── InvalidDirectoryError  - 无效目录
        ├── FileReadError         - 文件读取错误
        └── ExportError           - 导出错误

使用方式:
    from code.exceptions import CodeStatError, InvalidDirectoryError

    try:
        ...
    except InvalidDirectoryError as e:
        print(f"目录错误: {e}")
"""


class CodeStatError(Exception):
    """
    CodeStat 基础异常类

    所有 CodeStat 相关异常的父类，便于统一捕获处理。

    属性:
        message: 错误信息
    """
    pass


class InvalidDirectoryError(CodeStatError):
    """
    无效目录异常

    当指定的目录路径不存在或无法访问时抛出。

    场景:
        - 目录不存在
        - 目录权限不足
        - 路径格式错误
    """
    pass


class FileReadError(CodeStatError):
    """
    文件读取错误异常

    当无法读取文件内容时抛出。

    场景:
        - 文件不存在
        - 文件编码错误
        - 文件权限不足
    """
    pass


class ExportError(CodeStatError):
    """
    导出错误异常

    当导出结果到文件时发生错误时抛出。

    场景:
        - 输出路径无效
        - 文件写入失败
        - 格式转换错误
    """
    pass
