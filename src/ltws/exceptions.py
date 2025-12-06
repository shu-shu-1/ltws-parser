"""小树壁纸源协议 v3.0 异常类
"""


class WallpaperSourceError(Exception):
    """壁纸源基础异常"""



class InvalidSourceError(WallpaperSourceError):
    """无效的壁纸源异常"""



class FileNotFoundError(WallpaperSourceError):
    """文件未找到异常"""



class ValidationError(WallpaperSourceError):
    """验证失败异常"""



class ParseError(WallpaperSourceError):
    """解析失败异常"""



class PackagingError(WallpaperSourceError):
    """打包失败异常"""



class VariableError(WallpaperSourceError):
    """变量处理异常"""

