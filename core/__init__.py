"""
NEX Core Module
核心模块，包含推理引擎、Shell系统和基础服务
"""

__version__ = "0.1.0"

# 导出核心组件
from . import inference
from . import shell  
from . import foundation

__all__ = ["inference", "shell", "foundation"]