"""小树壁纸源协议 v3.0 数据模型
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict


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

    @field_validator("key")
    def validate_key(cls, v):
        """验证参数键名"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("参数键名只能包含小写字母、数字和下划线，且必须以字母开头")
        return v

    @model_validator(mode='after')
    def validate_parameter(self):
        """验证参数完整性"""
        if self.type == ParameterType.CHOICE:
            if not self.choices:
                raise ValueError("choice类型必须提供choices列表")
        return self


class Category(BaseModel):
    """分类定义模型"""

    id: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=50)
    category: str = Field(..., min_length=1, max_length=50)
    subcategory: Optional[str] = None
    subsubcategory: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None

    @field_validator("id")
    def validate_id(cls, v):
        """验证分类ID格式"""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("分类ID只能包含小写字母、数字和下划线，且必须以字母开头")
        return v


class RequestConfig(BaseModel):
    """请求配置模型"""

    url: Optional[str] = None
    method: str = Field(default="GET", pattern="^(GET|POST)$")
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    interval_seconds: Optional[int] = Field(default=None, ge=-1)
    max_concurrent: Optional[int] = Field(default=None, ge=1, le=10)
    skip_ssl_verify: Optional[bool] = None
    user_agent: Optional[str] = None

    headers: Optional[Dict[str, str]] = None
    body: Optional[Union[Dict[str, Any], str]] = None

    @field_validator("url")
    def validate_url(cls, v):
        """验证URL格式"""
        if v is None or v == "":
            return v
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

    @model_validator(mode='after')
    def validate_mapping(self):
        """验证字段映射"""
        # 静态响应场景可以完全为空，此处只在有值时做互斥校验
        if not any(
            getattr(self, field)
            for field in [
                "image",
                "title",
                "description",
                "thumbnail",
                "width",
                "height",
                "author",
                "source",
                "tags",
                "date",
                "items",
            ]
        ) and not self.item_mapping:
            return self

        has_single_fields = any(getattr(self, field) for field in ["image", "title", "description"])
        has_multi_fields = self.items is not None

        if has_single_fields and has_multi_fields:
            raise ValueError("单图模式和多图模式字段不能同时存在")

        if has_multi_fields and not self.item_mapping:
            raise ValueError("多图模式必须提供item_mapping")

        if self.item_mapping and "image" not in self.item_mapping:
            raise ValueError("item_mapping必须包含image字段")

        return self


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

    model_config = ConfigDict(extra="allow")  # 允许额外字段

    # 基本信息
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    logo: Optional[str] = None

    # 分类绑定
    categories: List[str] = Field(..., min_length=1)

    # 分类 API 图标（按分类覆盖默认 API 图标）
    category_icons: Optional[Dict[str, str]] = None

    # 参数定义
    parameters: List[Parameter] = Field(default_factory=list)

    # 请求配置
    request: Optional[RequestConfig] = None

    # 响应配置
    response: Dict[str, Any] = Field(default_factory=dict)

    # 字段映射
    mapping: Optional[FieldMapping] = None

    # 验证配置
    validation: Optional[Dict[str, Any]] = None

    # 错误处理
    error_handling: Optional[Dict[str, Any]] = None

    # 缓存配置
    cache: Optional[CacheConfig] = None

    # 继承配置
    inherit: Optional[str] = None

    @model_validator(mode='after')
    def validate_request_presence(self):
        """当响应为静态类型时允许省略 request，静态缺mapping时填充空映射"""
        response_cfg = self.response or {}
        # 协议：response.format = json|toml|image_url|image_raw|static_list|static_dict
        #      response.type = single|multi
        # 兼容旧写法：若仅提供 type 且其值像 format，再回退
        response_format = response_cfg.get("format")
        if not response_format:
            response_format = response_cfg.get("type")

        if isinstance(response_format, ResponseFormat):
            response_format = response_format.value
        if isinstance(response_format, str):
            response_format = response_format.lower()

        is_static = response_format in {
            ResponseFormat.STATIC_LIST.value,
            ResponseFormat.STATIC_DICT.value,
        }

        if self.request is None and not is_static:
            raise ValueError("request 配置缺失")

        if self.mapping is None and is_static:
            self.mapping = FieldMapping()

        if self.mapping is None and not is_static:
            raise ValueError("mapping 配置缺失")

        return self


class WallpaperSource(BaseModel):
    """壁纸源完整模型"""

    # 元数据
    metadata: Dict[str, Any]

    # 全局配置
    config: Dict[str, Any]

    # 分类定义
    categories: List[Category]

    # categories.toml 的可选扩展段（协议 v3.0 支持）
    categories_template: Optional[Dict[str, Any]] = None
    categories_level_icons: Optional[Dict[str, str]] = None
    category_groups: Optional[List[Dict[str, Any]]] = None

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