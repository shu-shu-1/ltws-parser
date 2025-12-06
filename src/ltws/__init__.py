"""LTWS (Little Tree Wallpaper Source) 协议 v3.0 解析器
"""

from .exceptions import (
    FileNotFoundError,
    InvalidSourceError,
    PackagingError,
    ParseError,
    ValidationError,
    VariableError,
    WallpaperSourceError,
)
from .models import (
    CacheConfig,
    Category,
    FieldMapping,
    Parameter,
    ParameterType,
    RequestConfig,
    ResponseFormat,
    ValidationRule,
    WallpaperAPI,
    WallpaperSource,
)
from .packager import LTWSPackager
from .parser import LTWSParser
from .utils import (
    calculate_file_hash,
    dot_path_get,
    extract_base64_icon,
    format_file_size,
    is_base64_image,
    is_valid_url,
    json_pointer_get,
    validate_identifier,
    validate_version,
)
from .validator import LTWSValidator
from .variables import URLTemplateEngine, VariableEngine

__version__ = "1.0.0"
__all__ = [
    # 主要类
    "LTWSParser",
    "LTWSValidator",
    "LTWSPackager",
    "VariableEngine",
    "URLTemplateEngine",

    # 数据模型
    "WallpaperSource",
    "WallpaperAPI",
    "Category",
    "Parameter",
    "ParameterType",
    "ResponseFormat",
    "RequestConfig",
    "FieldMapping",
    "ValidationRule",
    "CacheConfig",

    # 异常类
    "WallpaperSourceError",
    "InvalidSourceError",
    "FileNotFoundError",
    "ValidationError",
    "ParseError",
    "PackagingError",
    "VariableError",

    # 工具函数
    "validate_identifier",
    "validate_version",
    "is_base64_image",
    "is_valid_url",
    "calculate_file_hash",
    "extract_base64_icon",
    "json_pointer_get",
    "dot_path_get",
    "format_file_size",
]
