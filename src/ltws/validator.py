"""小树壁纸源协议 v3.0 验证器
"""

import re
from typing import Any, Dict, List

from .models import ParameterType, WallpaperAPI, WallpaperSource


class LTWSValidator:
    """小树壁纸源验证器
    
    功能：
    - 验证壁纸源配置完整性
    - 验证字段格式和约束
    - 验证图标格式
    - 提供详细的错误报告
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_source(self, source: WallpaperSource) -> bool:
        """验证壁纸源完整性
        
        Args:
            source: 壁纸源对象
            
        Returns:
            bool: 是否验证通过

        """
        self.errors.clear()
        self.warnings.clear()

        # 验证元数据
        self._validate_metadata(source.metadata)

        # 验证分类
        self._validate_categories(source.categories)

        # 验证 API
        for api in source.apis:
            self._validate_api(api, source.categories)

        # 验证分类引用
        category_errors = source.validate_categories()
        self.errors.extend(category_errors)

        return len(self.errors) == 0

    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """验证元数据"""
        # 必需字段检查
        required_fields = ["scheme", "identifier", "name", "version"]
        for field in required_fields:
            if field not in metadata:
                self.errors.append(f"缺少必需字段: {field}")

        # 协议版本检查
        if metadata.get("scheme") != "littletree_wallpaper_source_v3":
            self.errors.append("不支持的协议版本")

        # 标识符格式检查
        identifier = metadata.get("identifier", "")
        if not re.match(r"^com\.[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", identifier):
            self.errors.append(f"标识符格式错误: {identifier}")

        # 版本格式检查
        version = metadata.get("version", "")
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            self.errors.append(f"版本格式错误: {version}")

        # 名称长度检查
        name = metadata.get("name", "")
        if len(name) < 2 or len(name) > 32:
            self.warnings.append(f"名称长度建议在2-32字符之间: {len(name)}字符")

        # 图标格式检查
        if metadata.get("logo"):
            self._validate_icon(metadata["logo"], "metadata.logo")

    def _validate_categories(self, categories: List[Any]) -> None:
        """验证分类"""
        seen_ids = set()

        for i, category in enumerate(categories):
            # 分类ID唯一性检查
            if category.id in seen_ids:
                self.errors.append(f"分类ID重复: {category.id}")
            seen_ids.add(category.id)

            # 图标格式检查
            if category.icon:
                self._validate_icon(category.icon, f"categories[{i}].icon")

    def _validate_api(self, api: WallpaperAPI, all_categories: List[Any]) -> None:
        """验证 API"""
        # 名称检查
        if not api.name or len(api.name) > 100:
            self.errors.append(f"API名称无效: {api.name}")

        # 分类引用检查
        if not api.categories:
            self.errors.append(f"API '{api.name}' 没有绑定任何分类")

        # 图标格式检查
        if api.logo:
            self._validate_icon(api.logo, f"API '{api.name}'.logo")

        # 参数验证
        self._validate_parameters(api.parameters, api.name)

        # 请求配置验证
        self._validate_request(api.request, api.name)

        # 字段映射验证
        self._validate_mapping(api.mapping, api.name)

    def _validate_parameters(self, parameters: List[Any], api_name: str) -> None:
        """验证参数"""
        seen_keys = set()

        for i, param in enumerate(parameters):
            # 参数键唯一性
            if param.key in seen_keys:
                self.errors.append(f"API '{api_name}' 参数键重复: {param.key}")
            seen_keys.add(param.key)

            # 参数键格式
            if not re.match(r"^[a-z][a-z0-9_]*$", param.key):
                self.errors.append(f"API '{api_name}' 参数键格式错误: {param.key}")

            # choice类型必须有choices
            if param.type == ParameterType.CHOICE and not param.choices:
                self.errors.append(f"API '{api_name}' choice类型参数必须提供choices: {param.key}")

            # hidden参数必须有默认值
            if param.hidden and not param.default:
                self.warnings.append(f"API '{api_name}' 隐藏参数建议设置默认值: {param.key}")

    def _validate_request(self, request: Any, api_name: str) -> None:
        """验证请求配置"""
        # URL格式检查
        if not request.url:
            self.errors.append(f"API '{api_name}' 缺少URL")
        elif not re.match(r"^https?://", request.url):
            self.errors.append(f"API '{api_name}' URL必须以http://或https://开头")

        # 方法检查
        if request.method not in ["GET", "POST"]:
            self.errors.append(f"API '{api_name}' 请求方法必须是GET或POST")

        # 超时检查
        if request.timeout_seconds and (request.timeout_seconds < 1 or request.timeout_seconds > 300):
            self.warnings.append(f"API '{api_name}' 超时时间建议在1-300秒之间")

    def _validate_mapping(self, mapping: Any, api_name: str) -> None:
        """验证字段映射"""
        has_single = any([
            mapping.image, mapping.title, mapping.description,
            mapping.thumbnail, mapping.width, mapping.height,
        ])

        has_multi = mapping.items is not None

        if not has_single and not has_multi:
            self.errors.append(f"API '{api_name}' 字段映射配置不完整")

        if has_single and has_multi:
            self.errors.append(f"API '{api_name}' 不能同时配置单图和多图字段映射")

        if has_multi and not mapping.item_mapping:
            self.errors.append(f"API '{api_name}' 多图模式必须提供item_mapping")

        if mapping.item_mapping and "image" not in mapping.item_mapping:
            self.errors.append(f"API '{api_name}' item_mapping必须包含image字段")

    def _validate_icon(self, icon: str, context: str) -> None:
        """验证图标格式"""
        # 检查是否是Base64编码
        if icon.startswith("data:image/"):
            # Base64格式检查
            if ";base64," not in icon:
                self.errors.append(f"{context}: Base64图标格式错误")
        # 检查是否是URL
        elif not re.match(r"^https?://", icon):
            self.errors.append(f"{context}: 图标必须是Base64编码或URL")

    def get_errors(self) -> List[str]:
        """获取所有错误"""
        return self.errors

    def get_warnings(self) -> List[str]:
        """获取所有警告"""
        return self.warnings

    def get_validation_report(self) -> Dict[str, List[str]]:
        """获取验证报告"""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": len(self.errors) == 0,
        }
