# LTWS 解析器

用于解析和验证 LTWS (Little Tree Wallpaper Source) 协议 v3.0 的 Python 库。

## 特性

- 🚀 支持解析 `.ltws` 文件（不压缩的 TAR 格式）
- 📝 支持解析目录结构的壁纸源
- ✅ 完整的配置验证
- 🛠️ 提供打包工具
- 🔧 变量替换引擎
- 📊 详细的错误报告

## 安装

```bash
pip install ltws-parser
```


## 快速开始

### 1. 解析壁纸源

python

```
from ltws import LTWSParser

# 创建解析器
parser = LTWSParser()

# 解析 .ltws 文件
source = parser.parse("my_wallpaper_source.ltws")

# 或解析目录
source = parser.parse("my_wallpaper_source/")

# 使用壁纸源
print(f"名称: {source.name}")
print(f"版本: {source.version}")
print(f"API数量: {len(source.apis)}")
```



### 2. 验证壁纸源

python

```
from ltws import LTWSValidator

# 创建验证器
validator = LTWSValidator()

# 验证壁纸源
is_valid = validator.validate_source(source)

# 获取验证报告
report = validator.get_validation_report()
print(f"验证通过: {report['passed']}")
print(f"错误: {report['errors']}")
print(f"警告: {report['warnings']}")
```



### 3. 使用变量引擎

python

```
from ltws import VariableEngine

# 创建变量引擎
engine = VariableEngine()

# 替换变量
template = "https://api.example.com/wallpapers?date={{date_iso}}&random={{random_string:8}}"
result = engine.replace(template)
print(result)  # https://api.example.com/wallpapers?date=2024-01-15&random=abc123de
```



### 4. 打包壁纸源

python

```
from ltws import LTWSPackager

# 创建打包工具
packager = LTWSPackager()

# 打包目录为 .ltws 文件
packager.pack("my_wallpaper_source/", "output.ltws")
```



## 命令行工具

安装后可以使用 `ltws` 命令行工具：

bash

```
# 验证壁纸源
ltws validate my_wallpaper_source/

# 打包壁纸源
ltws pack my_wallpaper_source/ output.ltws

# 查看 .ltws 文件信息
ltws inspect output.ltws

# 测试壁纸源
ltws test my_wallpaper_source/
```



## API 参考

### LTWSParser

主要解析器类，用于解析壁纸源。

python

```
parser = LTWSParser(strict=True)
source = parser.parse(path)
errors = parser.get_errors()
warnings = parser.get_warnings()
```



### LTWSValidator

验证器类，用于验证壁纸源配置。

python

```
validator = LTWSValidator()
is_valid = validator.validate_source(source)
report = validator.get_validation_report()
```



### LTWSPackager

打包工具类，用于创建 `.ltws` 文件。

python

```
packager = LTWSPackager(strict=True)
packager.pack(source_dir, output_file, overwrite=False)
```



### VariableEngine

变量替换引擎，支持内置变量和自定义变量。

python

```
engine = VariableEngine()
result = engine.replace(template, context)
```



## 数据模型

库提供完整的数据模型：

- `WallpaperSource`: 壁纸源完整对象
- `WallpaperAPI`: API 定义
- `Category`: 分类定义
- `Parameter`: 参数定义
- `RequestConfig`: 请求配置
- `FieldMapping`: 字段映射