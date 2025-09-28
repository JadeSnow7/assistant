"""
现代化Shell语法系统
"""

from .parser import ModernShellParser
from .executor import ModernShellExecutor, ShellType, Result
from .objects import *
from .functions import *
from .pipeline import Pipeline, StreamProcessor
# 注意：ModernShellCommand需要额外依赖，按需导入

__version__ = "1.0.0"
__all__ = [
    "ModernShellParser",
    "ModernShellExecutor", 
    "Pipeline",
    "StreamProcessor",
    "ShellType",
    "Result"
]