"""小树壁纸源协议 v3.0 解析器
"""

import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import (
    FileNotFoundError,
    InvalidSourceError,
    ParseError,
    ValidationError,
    WallpaperSourceError,
)
from .models import Category, WallpaperAPI, WallpaperSource


class LTWSParser:
    """小树壁纸源解析器
    
    支持：
    - 从目录解析壁纸源
    - 从 .ltws 文件解析壁纸源
    - 验证配置完整性
    - 生成壁纸源对象
    """

    def __init__(self, strict: bool = True):
        """初始化解析器
        
        Args:
            strict: 严格模式，为True时遇到错误抛出异常

        """
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def parse(self, source_path: str) -> WallpaperSource:
        """解析壁纸源
        
        Args:
            source_path: 路径（目录或.ltws文件）
            
        Returns:
            WallpaperSource: 壁纸源对象
            
        Raises:
            InvalidSourceError: 源无效
            FileNotFoundError: 文件不存在

        """
        source_path = Path(source_path).resolve()

        if not source_path.exists():
            raise FileNotFoundError(f"路径不存在: {source_path}")

        self.errors.clear()
        self.warnings.clear()

        try:
            if source_path.is_file() and source_path.suffix == ".ltws":
                return self._parse_ltws_file(source_path)
            if source_path.is_dir():
                return self._parse_directory(source_path)
            raise InvalidSourceError(f"不支持的源类型: {source_path}")
        except Exception as e:
            if self.strict:
                raise
            # 在非严格模式下收集错误
            self.errors.append(f"解析失败: {e!s}")
            raise WallpaperSourceError(f"解析失败: {e!s}")

    def _parse_ltws_file(self, ltws_path: Path) -> WallpaperSource:
        """解析 .ltws 文件
        
        Args:
            ltws_path: .ltws 文件路径
            
        Returns:
            WallpaperSource: 壁纸源对象

        """
        # 验证 .ltws 文件格式
        if not self._validate_ltws_format(ltws_path):
            raise InvalidSourceError(f"无效的 .ltws 文件: {ltws_path}")

        # 创建临时目录并提取文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 提取 .ltws 文件
            with tarfile.open(ltws_path, "r") as tar:
                tar.extractall(temp_path)

            # 验证必需文件
            self._validate_required_files(temp_path)

            # 解析提取的目录
            source = self._parse_directory(temp_path)

            # 设置源路径
            source.source_path = str(ltws_path)

            return source

    def _parse_directory(self, dir_path: Path) -> WallpaperSource:
        """解析目录形式的壁纸源
        
        Args:
            dir_path: 目录路径
            
        Returns:
            WallpaperSource: 壁纸源对象

        """
        # 验证必需文件
        self._validate_required_files(dir_path)

        # 解析 source.toml
        source_metadata = self._parse_toml_file(dir_path / "source.toml")

        # 验证协议版本
        if source_metadata.get("scheme") != "littletree_wallpaper_source_v3":
            raise InvalidSourceError(
                f"不支持的协议版本: {source_metadata.get('scheme')}",
            )

        # 解析 config.toml (如果存在)
        config_path = dir_path / "config.toml"
        config = {}
        if config_path.exists():
            config = self._parse_toml_file(config_path)

        # 解析 categories.toml
        categories_data = self._parse_toml_file(dir_path / "categories.toml")
        categories = self._parse_categories(categories_data)

        # 解析 API 文件
        apis = self._parse_apis(dir_path, source_metadata)

        # 验证分类引用
        category_errors = self._validate_category_references(apis, categories)
        if category_errors and self.strict:
            raise ValidationError(f"分类引用错误: {', '.join(category_errors)}")

        # 创建壁纸源对象
        source = WallpaperSource(
            metadata=source_metadata,
            config=config,
            categories=categories,
            apis=apis,
            source_path=str(dir_path),
        )

        return source

    def _validate_required_files(self, dir_path: Path) -> None:
        """验证必需文件是否存在
        
        Args:
            dir_path: 目录路径
            
        Raises:
            FileNotFoundError: 必需文件不存在

        """
        required_files = ["source.toml", "categories.toml"]

        for file_name in required_files:
            file_path = dir_path / file_name
            if not file_path.exists():
                raise FileNotFoundError(f"必需文件不存在: {file_name}")

        # 检查 apis 目录
        apis_dir = dir_path / "apis"
        if not apis_dir.exists() or not apis_dir.is_dir():
            raise FileNotFoundError("缺少 apis 目录")

        # 检查至少一个 API 文件
        api_files = list(apis_dir.glob("*.toml"))
        if not api_files:
            raise FileNotFoundError("apis 目录中没有 .toml 文件")

    def _parse_toml_file(self, file_path: Path) -> Dict[str, Any]:
        """解析 TOML 文件
        
        Args:
            file_path: TOML 文件路径
            
        Returns:
            Dict[str, Any]: 解析后的数据
            
        Raises:
            ParseError: 解析失败

        """
        try:
            import rtoml
            with open(file_path, "r", encoding="utf-8") as f:
                return rtoml.load(f.read())
        except ImportError:
            raise ParseError("需要安装 rtoml 库: pip install rtoml")
        except Exception as e:
            raise ParseError(f"解析 TOML 文件失败 {file_path}: {e!s}")

    def _parse_categories(self, categories_data: Dict[str, Any]) -> List[Category]:
        """解析分类数据
        
        Args:
            categories_data: 分类 TOML 数据
            
        Returns:
            List[Category]: 分类对象列表

        """
        categories = []

        if "categories" in categories_data:
            for cat_data in categories_data["categories"]:
                try:
                    category = Category(**cat_data)
                    categories.append(category)
                except Exception as e:
                    if self.strict:
                        raise
                    self.errors.append(f"分类解析失败: {e!s}")

        return categories

    def _parse_apis(self, dir_path: Path, metadata: Dict[str, Any]) -> List[WallpaperAPI]:
        """解析所有 API 文件
        
        Args:
            dir_path: 目录路径
            metadata: source.toml 元数据
            
        Returns:
            List[WallpaperAPI]: API 对象列表

        """
        apis = []
        apis_dir = dir_path / "apis"

        # 获取 API 文件模式
        api_patterns = metadata.get("apis", [])
        api_files = []

        for pattern in api_patterns:
            pattern_path = dir_path / pattern
            if pattern_path.exists():
                if pattern_path.is_file():
                    api_files.append(pattern_path)
                else:
                    # 处理 glob 模式
                    for file_path in dir_path.glob(pattern):
                        if file_path.is_file():
                            api_files.append(file_path)

        # 如果没有指定模式，查找所有 .toml 文件
        if not api_files:
            api_files = list(apis_dir.glob("*.toml"))

        # 解析每个 API 文件
        for api_file in api_files:
            try:
                api_data = self._parse_toml_file(api_file)
                api = self._parse_api(api_data, str(api_file))
                apis.append(api)
            except Exception as e:
                if self.strict:
                    raise ParseError(f"解析 API 文件失败 {api_file}: {e!s}")
                self.errors.append(f"API 文件解析失败 {api_file}: {e!s}")

        return apis

    def _parse_api(self, api_data: Dict[str, Any], file_path: str) -> WallpaperAPI:
        """解析单个 API 数据
        
        Args:
            api_data: API TOML 数据
            file_path: API 文件路径
            
        Returns:
            WallpaperAPI: API 对象

        """
        # 处理继承
        if "inherit" in api_data:
            inherited_api = self._load_inherited_api(api_data["inherit"], file_path)
            if inherited_api:
                # 合并数据（当前 API 数据覆盖继承的数据）
                merged_data = {**inherited_api.dict(), **api_data}
                # 移除 inherit 字段
                merged_data.pop("inherit", None)
                api_data = merged_data

        try:
            return WallpaperAPI(**api_data)
        except Exception as e:
            raise ParseError(f"API 数据验证失败: {e!s}")

    def _load_inherited_api(self, inherit_path: str, current_file: str) -> Optional[Dict[str, Any]]:
        """加载继承的 API 数据
        
        Args:
            inherit_path: 继承文件路径
            current_file: 当前文件路径
            
        Returns:
            Optional[Dict[str, Any]]: 继承的 API 数据

        """
        try:
            # 构建继承文件的完整路径
            current_dir = Path(current_file).parent
            inherit_file = current_dir / inherit_path

            if inherit_file.exists():
                return self._parse_toml_file(inherit_file)
            self.warnings.append(f"继承文件不存在: {inherit_path}")
            return None
        except Exception as e:
            self.warnings.append(f"加载继承文件失败 {inherit_path}: {e!s}")
            return None

    def _validate_category_references(self, apis: List[WallpaperAPI], categories: List[Category]) -> List[str]:
        """验证 API 引用的分类是否存在
        
        Args:
            apis: API 列表
            categories: 分类列表
            
        Returns:
            List[str]: 错误消息列表

        """
        errors = []
        category_ids = {c.id for c in categories}

        for api in apis:
            for category_id in api.categories:
                if category_id not in category_ids:
                    errors.append(f"API '{api.name}' 引用了不存在的分类: {category_id}")

        return errors

    def _validate_ltws_format(self, ltws_path: Path) -> bool:
        """验证 .ltws 文件格式
        
        Args:
            ltws_path: .ltws 文件路径
            
        Returns:
            bool: 是否有效

        """
        try:
            # 检查文件扩展名
            if ltws_path.suffix != ".ltws":
                return False

            # 尝试打开为 tar 文件
            with tarfile.open(ltws_path, "r") as tar:
                members = tar.getmembers()

                # 检查必需文件
                member_names = {m.name for m in members}
                required_files = {"source.toml", "categories.toml"}

                if not required_files.issubset(member_names):
                    return False

                # 检查 apis 目录
                if not any(m.name.startswith("apis/") for m in members):
                    return False

            return True
        except Exception:
            return False

    def get_errors(self) -> List[str]:
        """获取所有错误"""
        return self.errors

    def get_warnings(self) -> List[str]:
        """获取所有警告"""
        return self.warnings

    def clear_messages(self):
        """清除错误和警告"""
        self.errors.clear()
        self.warnings.clear()
