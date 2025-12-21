"""小树壁纸源协议 v3.0 打包工具
"""

import hashlib
import json
import re
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from .exceptions import PackagingError, ValidationError


class LTWSPackager:
    """小树壁纸源打包工具

    功能：
    - 将壁纸源目录打包为 .ltws 文件
    - 验证打包内容
    - 生成清单文件
    - 检查资源文件
    """

    def __init__(self, strict: bool = True):
        """初始化打包工具

        Args:
            strict: 严格模式，为True时遇到错误抛出异常

        """
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def pack(self, source_dir: str, output_file: str, overwrite: bool = False) -> str:
        """打包壁纸源目录

        Args:
            source_dir: 源目录路径
            output_file: 输出文件路径
            overwrite: 是否覆盖已存在的文件

        Returns:
            str: 打包后的文件路径

        Raises:
            PackagingError: 打包失败
            ValidationError: 验证失败

        """
        source_dir = Path(source_dir).resolve()
        output_file = Path(output_file).resolve()

        # 检查输出文件
        if output_file.exists() and not overwrite:
            raise PackagingError(f"输出文件已存在: {output_file}")

        # 验证源目录
        if not self._validate_source_directory(source_dir):
            if self.strict:
                raise ValidationError(f"源目录验证失败: {', '.join(self.errors)}")

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 准备打包内容
            self._prepare_package_content(source_dir, temp_path)

            # 生成清单文件
            self._generate_manifest(source_dir, temp_path)

            # 创建 .ltws 文件
            self._create_ltws_file(temp_path, output_file)

            # 验证打包文件
            if not self._validate_ltws_file(output_file):
                raise PackagingError("打包文件验证失败")

            return str(output_file)

    def _validate_source_directory(self, source_dir: Path) -> bool:
        """验证源目录

        Args:
            source_dir: 源目录路径

        Returns:
            bool: 是否有效

        """
        self.errors.clear()
        self.warnings.clear()

        source_file = source_dir / "source.toml"
        if not source_file.exists():
            self.errors.append("缺少必需文件: source.toml")
            return False

        # 读取 source.toml，以确定 categories/config/apis 路径
        source_data = {}
        try:
            import rtoml

            source_data = rtoml.loads(source_file.read_text(encoding="utf-8"))
        except Exception as e:
            self.errors.append(f"读取 source.toml 失败: {e!s}")
            return False

        categories_rel = source_data.get("categories")
        if not categories_rel:
            self.errors.append("source.toml 缺少必需字段: categories")
        else:
            categories_path = source_dir / str(categories_rel)
            if not categories_path.exists():
                self.errors.append(f"缺少必需文件: {categories_rel}")

        # API 文件（按 apis 字段的 glob/路径数组）
        api_patterns = source_data.get("apis") or []
        if isinstance(api_patterns, str):
            api_patterns = [api_patterns]

        api_files: list[Path] = []
        for pattern in api_patterns:
            for file_path in source_dir.glob(str(pattern)):
                if file_path.is_file() and file_path.suffix.lower() == ".toml":
                    api_files.append(file_path)
        if not api_files:
            # 兼容：未配置 apis 时默认 apis/*.toml
            api_files = list((source_dir / "apis").glob("*.toml")) if (source_dir / "apis").exists() else []
        if not api_files:
            self.errors.append("未找到任何 API 配置文件（apis/*.toml）")

        # 检查资源文件（不允许）
        self._check_resource_files(source_dir)

        # 检查图标格式
        self._check_icon_files(source_dir)

        return len(self.errors) == 0

    def _check_resource_files(self, source_dir: Path) -> None:
        """检查资源文件

        Args:
            source_dir: 源目录路径

        """
        # 不允许的文件扩展名
        forbidden_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".ico",
            ".svg",
            ".webp",
            ".tiff",
            ".tif",
            ".ttf",
            ".otf",
            ".woff",
            ".woff2",
            ".mp3",
            ".mp4",
            ".wav",
            ".avi",
            ".mov",
            ".zip",
            ".rar",
            ".7z",
            ".gz",
            ".bz2",
        }

        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                # 检查文件扩展名
                if file_path.suffix.lower() in forbidden_extensions:
                    self.errors.append(
                        f"不允许的资源文件: {file_path.relative_to(source_dir)}",
                    )

                # 检查文件大小（TOML文件不应太大）
                if file_path.suffix.lower() == ".toml":
                    file_size = file_path.stat().st_size
                    if file_size > 1024 * 1024:  # 1MB
                        self.warnings.append(
                            f"TOML文件过大: {file_path.relative_to(source_dir)} ({file_size}字节)",
                        )

    def _check_icon_files(self, source_dir: Path) -> None:
        """检查图标文件引用

        Args:
            source_dir: 源目录路径

        """
        icon_pattern = re.compile(r'logo\s*=\s*"([^"]+)"|icon\s*=\s*"([^"]+)"')

        for toml_file in source_dir.rglob("*.toml"):
            try:
                content = toml_file.read_text(encoding="utf-8")
                for match in icon_pattern.finditer(content):
                    icon_value = match.group(1) or match.group(2)
                    if icon_value:
                        # 协议要求：仅允许 Base64 data URL 或外部 URL，不允许本地路径（无论是否存在）
                        if (
                            not icon_value.startswith("data:")
                            and not icon_value.startswith("http://")
                            and not icon_value.startswith("https://")
                        ):
                            self.errors.append(
                                f"不允许的本地图标引用: {toml_file.relative_to(source_dir)} -> {icon_value}",
                            )
            except Exception as e:
                self.warnings.append(f"检查图标文件失败 {toml_file}: {e!s}")

    def _prepare_package_content(self, source_dir: Path, temp_dir: Path) -> None:
        """准备打包内容

        Args:
            source_dir: 源目录路径
            temp_dir: 临时目录路径

        """
        # source.toml
        temp_dir.joinpath("source.toml").write_bytes((source_dir / "source.toml").read_bytes())

        source_data = {}
        try:
            import rtoml

            source_data = rtoml.loads((source_dir / "source.toml").read_text(encoding="utf-8"))
        except Exception as e:
            if self.strict:
                raise ValidationError(f"读取 source.toml 失败: {e!s}")

        # categories（按 source.toml 指向路径复制）
        categories_rel = source_data.get("categories") or "categories.toml"
        categories_src = source_dir / str(categories_rel)
        if categories_src.exists():
            dst = temp_dir / str(categories_rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(categories_src.read_bytes())

        # config（可选，按 source.toml 指向路径复制；默认 config.toml）
        config_rel = source_data.get("config") or "config.toml"
        config_src = source_dir / str(config_rel)
        if config_src.exists():
            dst = temp_dir / str(config_rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(config_src.read_bytes())

        # API 文件（按 apis 字段的 glob/路径数组复制；兼容缺省 apis/*.toml）
        api_patterns = source_data.get("apis") or []
        if isinstance(api_patterns, str):
            api_patterns = [api_patterns]

        api_files: list[Path] = []
        for pattern in api_patterns:
            for file_path in source_dir.glob(str(pattern)):
                if file_path.is_file() and file_path.suffix.lower() == ".toml":
                    api_files.append(file_path)
        if not api_files:
            api_files = list((source_dir / "apis").glob("*.toml")) if (source_dir / "apis").exists() else []

        for api_file in api_files:
            rel = api_file.relative_to(source_dir)
            dst = temp_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(api_file.read_bytes())

    def _generate_manifest(self, source_dir: Path, temp_dir: Path) -> None:
        """生成清单文件

        Args:
            source_dir: 源目录路径
            temp_dir: 临时目录路径

        """
        manifest = {
            "format_version": "1.0",
            "source_schema": "littletree_wallpaper_source_v3",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "tool": {"name": "littletree-wallpaper-source", "version": "1.0.0"},
            "files": [],
            "statistics": {},
            "metadata": {},
        }

        # 收集文件信息
        total_size = 0
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file():
                content = file_path.read_bytes()
                size = len(content)
                sha256 = hashlib.sha256(content).hexdigest()

                rel_path = file_path.relative_to(temp_dir)
                manifest["files"].append(
                    {
                        "path": str(rel_path),
                        "size": size,
                        "sha256": sha256,
                        "modified": file_path.stat().st_mtime,
                    },
                )

                total_size += size

        # 读取源元数据
        try:
            import rtoml

            source_data = rtoml.loads((source_dir / "source.toml").read_text(encoding="utf-8"))
            manifest["metadata"] = {
                "identifier": source_data.get("identifier", ""),
                "name": source_data.get("name", ""),
                "version": source_data.get("version", ""),
                "description": source_data.get("description", ""),
            }
        except Exception:
            pass

        # 统计信息
        manifest["statistics"] = {
            "total_files": len(manifest["files"]),
            "total_size": total_size,
            "api_count": len(list((temp_dir / "apis").glob("*.toml")))
            if (temp_dir / "apis").exists()
            else 0,
        }

        # 写入清单文件
        manifest_file = temp_dir / "manifest.json"
        manifest_file.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
        )

    def _create_ltws_file(self, temp_dir: Path, output_file: Path) -> None:
        """创建 .ltws 文件

        Args:
            temp_dir: 临时目录路径
            output_file: 输出文件路径

        """
        # 确保输出目录存在
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 创建不压缩的 TAR 文件
        with tarfile.open(output_file, "w") as tar:
            for file_path in temp_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    tar.add(file_path, arcname=str(arcname))

    def _validate_ltws_file(self, ltws_file: Path) -> bool:
        """验证 .ltws 文件

        Args:
            ltws_file: .ltws 文件路径

        Returns:
            bool: 是否有效

        """
        try:
            # 检查文件扩展名
            if ltws_file.suffix != ".ltws":
                return False

            # 检查文件大小
            if ltws_file.stat().st_size == 0:
                return False

            # 检查是否为有效的 TAR 文件
            with tarfile.open(ltws_file, "r") as tar:
                members = tar.getmembers()

                member_names = {m.name for m in members}
                if "source.toml" not in member_names:
                    return False

                # 至少应存在一个 API TOML（默认约束 apis/*.toml）
                if not any(m.name.startswith("apis/") and m.name.endswith(".toml") for m in members):
                    return False

                # 按 source.toml 指向检查 categories 文件是否存在
                try:
                    import rtoml

                    source_f = tar.extractfile("source.toml")
                    if source_f is None:
                        return False
                    source_data = rtoml.loads(source_f.read().decode("utf-8"))
                    categories_rel = source_data.get("categories") or "categories.toml"
                    if str(categories_rel) not in member_names:
                        return False
                except Exception:
                    # 读失败时不强行判 false，交由解析阶段报错
                    pass

            return True
        except Exception:
            return False

    def get_errors(self) -> List[str]:
        """获取所有错误"""
        return self.errors

    def get_warnings(self) -> List[str]:
        """获取所有警告"""
        return self.warnings
