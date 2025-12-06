"""小树壁纸源协议 v3.0 变量引擎
"""

import random
import re
import string
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from urllib.parse import quote


class VariableEngine:
    """变量替换引擎
    
    支持：
    - 内置变量（时间、随机数等）
    - 参数变量
    - 环境变量
    - 自定义变量
    """

    def __init__(self):
        self._variables: Dict[str, Any] = {}
        self._functions: Dict[str, Callable] = {}

        # 注册内置变量函数
        self._register_builtin_functions()

    def register_variable(self, name: str, value: Any) -> None:
        """注册变量"""
        self._variables[name] = value

    def register_function(self, name: str, func: Callable) -> None:
        """注册函数"""
        self._functions[name] = func

    def replace(self, template: str, context: Optional[Dict[str, Any]] = None) -> str:
        """替换模板中的变量
        
        Args:
            template: 包含变量的模板字符串
            context: 上下文变量
            
        Returns:
            str: 替换后的字符串

        """
        if context is None:
            context = {}

        # 合并变量：上下文 > 注册变量
        all_vars = {**self._variables, **context}

        # 替换变量
        result = template

        # 替换 {{variable}} 格式
        result = re.sub(
            r"\{\{(\w+)(?::([^}]+))?\}\}",
            lambda m: self._replace_variable(m, all_vars),
            result,
        )

        return result

    def _replace_variable(self, match, variables: Dict[str, Any]) -> str:
        """替换单个变量"""
        name = match.group(1)
        params = match.group(2)

        # 首先检查内置函数
        if name in self._functions:
            func = self._functions[name]
            if params:
                # 解析参数
                args = self._parse_function_params(params)
                return str(func(*args))
            return str(func())

        # 然后检查变量
        if name in variables:
            value = variables[name]
            if callable(value):
                return str(value(params) if params else value())
            return str(value)

        # 变量未找到，返回原样
        return match.group(0)

    def _parse_function_params(self, params: str) -> list:
        """解析函数参数"""
        # 简单的参数解析，支持逗号分隔
        return [p.strip() for p in params.split(",")]

    def _register_builtin_functions(self) -> None:
        """注册内置函数"""
        # 时间相关函数
        self.register_function("timestamp_ms", lambda: int(datetime.now().timestamp() * 1000))
        self.register_function("timestamp_s", lambda: int(datetime.now().timestamp()))
        self.register_function("date_iso", lambda: datetime.now().strftime("%Y-%m-%d"))
        self.register_function("date_cn", lambda: datetime.now().strftime("%Y年%m月%d日"))
        self.register_function("year", lambda: datetime.now().year)
        self.register_function("month", lambda: datetime.now().month)
        self.register_function("day", lambda: datetime.now().day)
        self.register_function("hour", lambda: datetime.now().hour)
        self.register_function("minute", lambda: datetime.now().minute)
        self.register_function("second", lambda: datetime.now().second)

        # 随机数函数
        self.register_function("random_string", self._random_string)
        self.register_function("random_int", self._random_int)
        self.register_function("random_hex", self._random_hex)

        # 编码函数
        self.register_function("url_encode", lambda s: quote(s) if s else "")

        # UUID函数
        import uuid
        self.register_function("uuid", lambda: str(uuid.uuid4()))

    def _random_string(self, length: str = "8") -> str:
        """生成随机字符串"""
        try:
            n = int(length)
            return "".join(random.choices(string.ascii_letters + string.digits, k=n))
        except Exception:
            return "".join(random.choices(string.ascii_letters + string.digits, k=8))

    def _random_int(self, min_val: str = "1", max_val: str = "100") -> str:
        """生成随机整数"""
        try:
            min_int = int(min_val)
            max_int = int(max_val)
            return str(random.randint(min_int, max_int))
        except Exception:
            return str(random.randint(1, 100))

    def _random_hex(self, length: str = "6") -> str:
        """生成随机十六进制字符串"""
        try:
            n = int(length)
            return "".join(random.choices("0123456789abcdef", k=n))
        except Exception:
            return "".join(random.choices("0123456789abcdef", k=6))

    def create_context(self, **kwargs) -> Dict[str, Any]:
        """创建变量上下文
        
        Args:
            **kwargs: 上下文变量
            
        Returns:
            Dict[str, Any]: 变量上下文

        """
        context = {}

        # 添加设备信息变量（模拟）
        context.update({
            "screen_width": kwargs.get("screen_width", 1920),
            "screen_height": kwargs.get("screen_height", 1080),
            "screen_ratio": kwargs.get("screen_ratio", 1.777),
            "device_id": kwargs.get("device_id", ""),
            "locale": kwargs.get("locale", "zh-CN"),
        })

        # 添加参数变量
        context.update(kwargs.get("params", {}))

        return context


class URLTemplateEngine(VariableEngine):
    """URL模板引擎"""

    def __init__(self):
        super().__init__()

    def build_url(self, template: str, params: Dict[str, Any] = None, **kwargs) -> str:
        """构建URL
        
        Args:
            template: URL模板
            params: 参数
            **kwargs: 其他上下文变量
            
        Returns:
            str: 构建后的URL

        """
        if params is None:
            params = {}

        # 创建上下文
        context = self.create_context(**kwargs)
        context.update(params)

        # 替换变量
        return self.replace(template, context)
