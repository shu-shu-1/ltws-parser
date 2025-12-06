"""小树壁纸源协议 v3.0 数据模型
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator


class ParameterType(str, Enum):
    """参数类型枚举"""

    CHOICE = "choice"
    TEXT = "text"
    BOOLEAN = "boolean"


class ResponseFormat(str, Enum):
    """响应格式枚举"""

    JSON = "json"
    TOML = "toml"
    IMAGE_URL = "image_url"
    IMAGE_RAW = "image_raw"
    STATIC_LIST = "static_list"
    STATIC_DICT = "static_dict"


class Parameter(BaseModel):
    """参数定义模型"""

    key: str = Field(..., min_length=1, max_length=50)
    type: ParameterType
    label: str = Field(..., min_length=1, max_length=50)
    default: str = ""
    choices: Optional[List[str]] = None
    placeholder: Optional[str] = None
    hidden: bool = False
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    description: Optional[str] = None

    @validator("key")
    def validate_key(cls, v):
        """验证参数键名"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("参数键名只能包含小写字母、数字和下划线，且必须以字母开头")
        return v

    @root_validator
    def validate_parameter(cls, values):
        """验证参数完整性"""
        if values.get("type") == ParameterType.CHOICE:
            if not values.get("choices"):
                raise ValueError("choice类型必须提供choices列表")
        return values


class Category(BaseModel):
    """分类定义模型"""

    id: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=50)
    subcategory: Optional[str] = None
    subsubcategory: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None

    @validator("id")
    def validate_id(cls, v):
        """验证分类ID格式"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("分类ID只能包含小写字母、数字和下划线，且必须以字母开头")
        return v


class RequestConfig(BaseModel):
    """请求配置模型"""

    url: str
    method: str = Field(default="GET", regex="^(GET|POST)$")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    interval_seconds: Optional[int] = Field(default=None, ge=-1)
    max_concurrent: Optional[int] = Field(default=None, ge=1, le=10)
    skip_ssl_verify: Optional[bool] = None
    user_agent: Optional[str] = None

    headers: Optional[Dict[str, str]] = None
    body: Optional[Union[Dict[str, Any], str]] = None

    @validator("url")
    def validate_url(cls, v):
        """验证URL格式"""
        if not re.match(r"^https?://", v):
            raise ValueError("URL必须以http://或https://开头")
        return v


class FieldMapping(BaseModel):
    """字段映射模型"""

    # 单图模式字段
    image: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[str] = None
    date: Optional[str] = None

    # 多图模式字段
    items: Optional[str] = None
    item_mapping: Optional[Dict[str, str]] = None

    @root_validator
    def validate_mapping(cls, values):
        """验证字段映射"""
        has_single_fields = any(values.get(field) for field in ["image", "title", "description"])
        has_multi_fields = values.get("items") is not None

        if has_single_fields and has_multi_fields:
            raise ValueError("单图模式和多图模式字段不能同时存在")

        if has_multi_fields and not values.get("item_mapping"):
            raise ValueError("多图模式必须提供item_mapping")

        if values.get("item_mapping") and "image" not in values["item_mapping"]:
            raise ValueError("item_mapping必须包含image字段")

        return values


class ValidationRule(BaseModel):
    """验证规则模型"""

    path: str
    regex: Optional[str] = None
    max_length: Optional[int] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    message: Optional[str] = None


class CacheConfig(BaseModel):
    """缓存配置模型"""

    enabled: bool = True
    ttl_seconds: int = Field(default=300, ge=1)
    key_template: Optional[str] = None
    exclude_params: Optional[List[str]] = None


class WallpaperAPI(BaseModel):
    """API定义模型"""

    # 基本信息
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    logo: Optional[str] = None

    # 分类绑定
    categories: List[str] = Field(..., min_items=1)

    # 参数定义
    parameters: List[Parameter] = Field(default_factory=list)

    # 请求配置
    request: RequestConfig

    # 响应配置
    response: Dict[str, Any] = Field(default_factory=dict)

    # 字段映射
    mapping: FieldMapping

    # 验证配置
    validation: Optional[Dict[str, Any]] = None

    # 错误处理
    error_handling: Optional[Dict[str, Any]] = None

    # 缓存配置
    cache: Optional[CacheConfig] = None

    # 继承配置
    inherit: Optional[str] = None

    class Config:
        """Pydantic配置"""

        extra = "allow"  # 允许额外字段


class WallpaperSource(BaseModel):
    """壁纸源完整模型"""

    # 元数据
    metadata: Dict[str, Any]

    # 全局配置
    config: Dict[str, Any]

    # 分类定义
    categories: List[Category]

    # API列表
    apis: List[WallpaperAPI]

    # 原始文件路径（用于调试）
    source_path: Optional[str] = None
    loaded_at: datetime = Field(default_factory=datetime.now)

    @property
    def identifier(self) -> str:
        """获取壁纸源标识符"""
        return self.metadata.get("identifier", "")

    @property
    def name(self) -> str:
        """获取壁纸源名称"""
        return self.metadata.get("name", "")

    @property
    def version(self) -> str:
        """获取壁纸源版本"""
        return self.metadata.get("version", "")

    def get_api_by_name(self, name: str) -> Optional[WallpaperAPI]:
        """根据名称获取API"""
        for api in self.apis:
            if api.name == name:
                return api
        return None

    def get_category_by_id(self, category_id: str) -> Optional[Category]:
        """根据ID获取分类"""
        for category in self.categories:
            if category.id == category_id:
                return category
        return None

    def validate_categories(self) -> List[str]:
        """验证API引用的分类是否存在"""
        errors = []
        category_ids = {c.id for c in self.categories}

        for api in self.apis:
            for category_id in api.categories:
                if category_id not in category_ids:
                    errors.append(f"API '{api.name}' 引用了不存在的分类: {category_id}")

        return errors
