#!/usr/bin/env python3
"""LTWS 命令行工具"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import LTWSPackager, LTWSParser, LTWSValidator


@click.group()
@click.version_option()
def cli():
    """LTWS 工具"""


@cli.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--strict/--no-strict", default=True, help="严格模式")
@click.option("--verbose", "-v", is_flag=True, help="详细输出")
def validate(source: str, strict: bool, verbose: bool):
    """验证壁纸源"""
    source_path = Path(source)

    try:
        # 创建解析器
        parser = LTWSParser(strict=strict)

        # 解析壁纸源
        click.echo(f"正在解析: {source_path}")
        wallpaper_source = parser.parse(source)

        # 创建验证器
        validator = LTWSValidator()

        # 验证壁纸源
        click.echo("正在验证...")
        is_valid = validator.validate_source(wallpaper_source)

        # 输出结果
        if is_valid:
            click.echo(click.style("✓ 验证通过", fg="green"))
            click.echo(f"壁纸源: {wallpaper_source.name} v{wallpaper_source.version}")
            click.echo(f"标识符: {wallpaper_source.identifier}")
            click.echo(f"分类数: {len(wallpaper_source.categories)}")
            click.echo(f"API数量: {len(wallpaper_source.apis)}")
        else:
            click.echo(click.style("✗ 验证失败", fg="red"))

        # 输出错误和警告
        errors = parser.get_errors() + validator.get_errors()
        warnings = parser.get_warnings() + validator.get_warnings()

        if errors:
            click.echo("\n错误:")
            for error in errors:
                click.echo(f"  {click.style('✗', fg='red')} {error}")

        if warnings:
            click.echo("\n警告:")
            for warning in warnings:
                click.echo(f"  {click.style('!', fg='yellow')} {warning}")

        if verbose:
            click.echo("\n详细信息:")
            click.echo(f"  解析器错误: {len(parser.get_errors())}")
            click.echo(f"  解析器警告: {len(parser.get_warnings())}")
            click.echo(f"  验证器错误: {len(validator.get_errors())}")
            click.echo(f"  验证器警告: {len(validator.get_warnings())}")

        sys.exit(0 if is_valid else 1)

    except Exception as e:
        click.echo(click.style(f"错误: {e!s}", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("source_dir", type=click.Path(exists=True, file_okay=False))
@click.argument("output_file", type=click.Path())
@click.option("--overwrite", "-f", is_flag=True, help="覆盖已存在的文件")
@click.option("--strict/--no-strict", default=True, help="严格模式")
def pack(source_dir: str, output_file: str, overwrite: bool, strict: bool):
    """打包壁纸源为 .ltws 文件"""
    try:
        # 创建打包工具
        packager = LTWSPackager(strict=strict)

        # 执行打包
        click.echo(f"正在打包: {source_dir}")
        result = packager.pack(source_dir, output_file, overwrite)

        click.echo(click.style(f"✓ 打包成功: {result}", fg="green"))

        # 输出打包信息
        file_size = Path(result).stat().st_size
        click.echo(f"文件大小: {file_size:,} 字节")

        # 输出错误和警告
        # errors = packager.get_errors()
        warnings = packager.get_warnings()

        if warnings:
            click.echo("\n警告:")
            for warning in warnings:
                click.echo(f"  {click.style('!', fg='yellow')} {warning}")

        sys.exit(0)

    except Exception as e:
        click.echo(click.style(f"错误: {e!s}", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("ltws_file", type=click.Path(exists=True))
@click.option("--extract-dir", type=click.Path(), help="提取目录")
def inspect(ltws_file: str, extract_dir: Optional[str]):
    """查看 .ltws 文件信息"""
    try:
        # 创建解析器
        parser = LTWSParser(strict=False)

        # 解析 .ltws 文件
        click.echo(f"正在解析: {ltws_file}")
        wallpaper_source = parser.parse(ltws_file)

        # 输出基本信息
        click.echo(click.style("\n基本信息", fg="cyan", bold=True))
        click.echo(f"  名称: {wallpaper_source.name}")
        click.echo(f"  标识符: {wallpaper_source.identifier}")
        click.echo(f"  版本: {wallpaper_source.version}")
        click.echo(f"  加载时间: {wallpaper_source.loaded_at}")

        # 输出分类信息
        click.echo(click.style("\n分类信息", fg="cyan", bold=True))
        for category in wallpaper_source.categories:
            click.echo(f"  {category.id}: {category.name}")

        # 输出API信息
        click.echo(click.style("\nAPI信息", fg="cyan", bold=True))
        for api in wallpaper_source.apis:
            click.echo(f"  {api.name}: {len(api.categories)}个分类")

        # 输出错误和警告
        errors = parser.get_errors()
        warnings = parser.get_warnings()

        if errors:
            click.echo(click.style("\n解析错误", fg="red", bold=True))
            for error in errors:
                click.echo(f"  ✗ {error}")

        if warnings:
            click.echo(click.style("\n解析警告", fg="yellow", bold=True))
            for warning in warnings:
                click.echo(f"  ! {warning}")

        # 提取文件（如果需要）
        if extract_dir:
            extract_path = Path(extract_dir)
            extract_path.mkdir(parents=True, exist_ok=True)

            # 这里需要实现提取逻辑
            click.echo(f"\n提取到: {extract_dir}")
            # 注意：实际提取需要调用tarfile库

        sys.exit(0)

    except Exception as e:
        click.echo(click.style(f"错误: {e!s}", fg="red"))
        sys.exit(1)


@cli.command()
@click.argument("source", type=click.Path(exists=True))
def test(source: str):
    """测试壁纸源"""
    try:
        click.echo(f"测试壁纸源: {source}")

        # 创建解析器
        parser = LTWSParser(strict=False)

        # 解析
        click.echo("1. 解析配置...")
        wallpaper_source = parser.parse(source)

        # 验证
        click.echo("2. 验证配置...")
        validator = LTWSValidator()
        is_valid = validator.validate_source(wallpaper_source)

        # 输出结果
        click.echo("\n" + "="*50)

        if is_valid:
            click.echo(click.style("测试通过 ✓", fg="green", bold=True))
            click.echo(f"壁纸源: {wallpaper_source.name}")
            click.echo(f"API数量: {len(wallpaper_source.apis)}")
        else:
            click.echo(click.style("测试失败 ✗", fg="red", bold=True))

        # 统计信息
        total_errors = len(parser.get_errors()) + len(validator.get_errors())
        total_warnings = len(parser.get_warnings()) + len(validator.get_warnings())

        click.echo(f"错误数: {total_errors}")
        click.echo(f"警告数: {total_warnings}")

        sys.exit(0 if is_valid else 1)

    except Exception as e:
        click.echo(click.style(f"测试失败: {e!s}", fg="red"))
        sys.exit(1)


def main():
    """主函数入口"""
    cli()


if __name__ == "__main__":
    cli()