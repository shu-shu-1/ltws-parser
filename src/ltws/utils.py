"""小树壁纸源协议 v3.0 工具函数
"""

import base64
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def validate_identifier(identifier: str) -> bool:
    """验证标识符格式
    
    Args:
        identifier: 标识符
        
    Returns:
        bool: 是否有效

    """
    pattern = r"^com\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"
    return bool(re.match(pattern, identifier))


def validate_version(version: str) -> bool:
    """验证版本格式
    
    Args:
        version: 版本号
        
    Returns:
        bool: 是否有效

    """
    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, version))


def is_base64_image(data: str) -> bool:
    """检查字符串是否是Base64编码的图片
    
    Args:
        data: 待检查的字符串
        
    Returns:
        bool: 是否是Base64图片

    """
    if not data.startswith("data:image/"):
        return False

    if ";base64," not in data:
        return False

    try:
        # 尝试解码Base64部分
        base64_part = data.split(";base64,", 1)[1]
        base64.b64decode(base64_part, validate=True)
        return True
    except Exception:
        return False


def is_valid_url(url: str) -> bool:
    """检查是否是有效的URL
    
    Args:
        url: URL字符串
        
    Returns:
        bool: 是否是有效URL

    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """计算文件哈希值
    
    Args:
        file_path: 文件路径
        algorithm: 哈希算法
        
    Returns:
        str: 哈希值

    """
    hash_func = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        # 分块读取大文件
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def extract_base64_icon(icon_data: str) -> Optional[bytes]:
    """从Base64字符串提取图标数据
    
    Args:
        icon_data: Base64编码的图标数据
        
    Returns:
        Optional[bytes]: 解码后的图标数据，失败返回None

    """
    if not is_base64_image(icon_data):
        return None

    try:
        base64_part = icon_data.split(";base64,", 1)[1]
        return base64.b64decode(base64_part)
    except Exception:
        return None


def json_pointer_get(data: Dict[str, Any], pointer: str) -> Any:
    """使用JSON Pointer语法获取数据
    
    Args:
        data: JSON数据
        pointer: JSON Pointer路径
        
    Returns:
        Any: 获取到的数据

    """
    if not pointer.startswith("/"):
        raise ValueError(f"无效的JSON Pointer: {pointer}")

    parts = pointer.split("/")[1:]  # 移除开头的空部分

    current = data
    for part in parts:
        if isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                raise KeyError(f"数组索引无效: {part}")
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                raise KeyError(f"键不存在: {part}")
        else:
            raise TypeError(f"无法遍历类型: {type(current)}")

    return current


def dot_path_get(data: Dict[str, Any], path: str) -> Any:
    """使用点号路径语法获取数据
    
    Args:
        data: 数据
        path: 点号路径
        
    Returns:
        Any: 获取到的数据

    """
    parts = path.split(".")

    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(f"路径不存在: {path}")

    return current


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小
    
    Args:
        size_bytes: 字节大小
        
    Returns:
        str: 格式化后的字符串

    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
