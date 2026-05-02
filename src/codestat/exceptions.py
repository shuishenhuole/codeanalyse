"""自定义异常"""


class CodeStatError(Exception):
    """基础异常"""
    pass


class InvalidDirectoryError(CodeStatError):
    """无效目录"""
    pass


class FileReadError(CodeStatError):
    """文件读取错误"""
    pass


class ExportError(CodeStatError):
    """导出错误"""
    pass