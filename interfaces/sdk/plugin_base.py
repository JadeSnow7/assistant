"""
Python插件基类 - 提供与C++插件系统交互的Python接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import json
import logging
import asyncio
from pathlib import Path


class PluginStatus(Enum):
    """插件状态枚举"""
    UNKNOWN = 0
    LOADED = 1
    INITIALIZED = 2
    RUNNING = 3
    PAUSED = 4
    ERROR = 5
    UNLOADING = 6


@dataclass
class PluginVersion:
    """插件版本信息"""
    major: int = 1
    minor: int = 0
    patch: int = 0
    suffix: str = ""

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.suffix:
            version += f"-{self.suffix}"
        return version

    def is_compatible(self, other: 'PluginVersion') -> bool:
        """检查版本兼容性"""
        return self.major == other.major and self.minor >= other.minor


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    display_name: str = ""
    description: str = ""
    version: PluginVersion = None
    author: str = ""
    license: str = ""
    website: str = ""
    dependencies: List[str] = None
    min_core_version: PluginVersion = None
    supported_platforms: List[str] = None
    default_config: Dict[str, Any] = None
    capabilities: Dict[str, str] = None

    def __post_init__(self):
        if self.version is None:
            self.version = PluginVersion()
        if self.dependencies is None:
            self.dependencies = []
        if self.min_core_version is None:
            self.min_core_version = PluginVersion()
        if self.supported_platforms is None:
            self.supported_platforms = ["linux", "windows", "macos"]
        if self.default_config is None:
            self.default_config = {}
        if self.capabilities is None:
            self.capabilities = {}
        if not self.display_name:
            self.display_name = self.name


@dataclass
class PluginError:
    """插件错误信息"""
    code: int = 0
    message: str = ""
    details: str = ""


class PluginContext:
    """插件上下文 - 提供与核心系统的交互接口"""
    
    def __init__(self, core_interface=None):
        self._core_interface = core_interface
        self._logger = logging.getLogger(f"plugin")
        
    def get_core_api(self, api_name: str) -> Any:
        """获取核心API接口"""
        if self._core_interface:
            return self._core_interface.get_api(api_name)
        return None
        
    def log(self, level: str, message: str):
        """记录日志"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(log_level, message)
        
    def get_config(self, key: str, default_value: str = "") -> str:
        """获取配置值"""
        if self._core_interface:
            return self._core_interface.get_config(key, default_value)
        return default_value
        
    def set_config(self, key: str, value: str):
        """设置配置值"""
        if self._core_interface:
            self._core_interface.set_config(key, value)
            
    def call_plugin(self, plugin_name: str, method: str, args: List[Any]) -> Any:
        """调用其他插件"""
        if self._core_interface:
            return self._core_interface.call_plugin(plugin_name, method, args)
        return None
        
    def register_event_listener(self, event_name: str, callback):
        """注册事件监听器"""
        if self._core_interface:
            self._core_interface.register_event_listener(event_name, callback)
            
    def emit_event(self, event_name: str, data: Any):
        """触发事件"""
        if self._core_interface:
            self._core_interface.emit_event(event_name, data)
            
    def get_plugin_data_dir(self) -> Path:
        """获取插件数据目录"""
        if self._core_interface:
            return Path(self._core_interface.get_plugin_data_dir())
        return Path.cwd() / "plugin_data"
        
    def get_temp_dir(self) -> Path:
        """获取临时目录"""
        if self._core_interface:
            return Path(self._core_interface.get_temp_dir())
        return Path.cwd() / "temp"


class IPlugin(ABC):
    """插件接口基类"""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        pass
        
    @abstractmethod
    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        pass
        
    @abstractmethod
    def start(self) -> bool:
        """启动插件"""
        pass
        
    @abstractmethod
    def stop(self) -> bool:
        """停止插件"""
        pass
        
    @abstractmethod
    def cleanup(self) -> bool:
        """清理插件"""
        pass
        
    @abstractmethod
    def get_status(self) -> PluginStatus:
        """获取插件状态"""
        pass
        
    @abstractmethod
    def is_healthy(self) -> bool:
        """检查插件健康状态"""
        pass
        
    @abstractmethod
    def get_last_error(self) -> Optional[PluginError]:
        """获取最后的错误信息"""
        pass
        
    @abstractmethod
    def call_method(self, method_name: str, args: List[Any]) -> Any:
        """调用插件方法"""
        pass
        
    @abstractmethod
    def get_supported_methods(self) -> List[str]:
        """获取插件支持的方法列表"""
        pass
        
    @abstractmethod
    def get_method_signature(self, method_name: str) -> str:
        """获取方法签名"""
        pass
        
    @abstractmethod
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新配置"""
        pass
        
    @abstractmethod
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        pass
        
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        pass


class PluginBase(IPlugin):
    """插件基类实现"""
    
    def __init__(self, metadata: PluginMetadata):
        self._metadata = metadata
        self._status = PluginStatus.UNKNOWN
        self._context: Optional[PluginContext] = None
        self._last_error: Optional[PluginError] = None
        self._config: Dict[str, Any] = metadata.default_config.copy()
        self._registered_methods: Dict[str, callable] = {}
        self._logger = logging.getLogger(f"plugin.{metadata.name}")
        
    def get_metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        return self._metadata
        
    def get_status(self) -> PluginStatus:
        """获取插件状态"""
        return self._status
        
    def is_healthy(self) -> bool:
        """检查插件健康状态"""
        return self._status in [PluginStatus.INITIALIZED, PluginStatus.RUNNING]
        
    def get_last_error(self) -> Optional[PluginError]:
        """获取最后的错误信息"""
        return self._last_error
        
    def get_supported_methods(self) -> List[str]:
        """获取插件支持的方法列表"""
        return list(self._registered_methods.keys())
        
    def get_method_signature(self, method_name: str) -> str:
        """获取方法签名"""
        if method_name in self._registered_methods:
            method = self._registered_methods[method_name]
            return f"{method.__name__}{method.__annotations__}"
        return ""
        
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()
        
    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        self._context = context
        self._status = PluginStatus.LOADED
        
        try:
            result = self.on_initialize(context)
            if result:
                self._status = PluginStatus.INITIALIZED
            return result
        except Exception as e:
            self._set_error(1, "Initialize failed", str(e))
            return False
            
    def start(self) -> bool:
        """启动插件"""
        if self._status != PluginStatus.INITIALIZED:
            self._set_error(2, "Plugin not initialized", "")
            return False
            
        try:
            result = self.on_start()
            if result:
                self._status = PluginStatus.RUNNING
            return result
        except Exception as e:
            self._set_error(3, "Start failed", str(e))
            return False
            
    def stop(self) -> bool:
        """停止插件"""
        if self._status != PluginStatus.RUNNING:
            return True
            
        try:
            result = self.on_stop()
            if result:
                self._status = PluginStatus.INITIALIZED
            return result
        except Exception as e:
            self._set_error(4, "Stop failed", str(e))
            return False
            
    def cleanup(self) -> bool:
        """清理插件"""
        try:
            result = self.on_cleanup()
            self._status = PluginStatus.UNKNOWN
            return result
        except Exception as e:
            self._set_error(5, "Cleanup failed", str(e))
            return False
            
    def call_method(self, method_name: str, args: List[Any]) -> Any:
        """调用插件方法"""
        if method_name not in self._registered_methods:
            raise ValueError(f"Method '{method_name}' not found")
            
        try:
            method = self._registered_methods[method_name]
            return method(*args)
        except Exception as e:
            self._set_error(6, f"Method call failed: {method_name}", str(e))
            raise
            
    def update_config(self, config: Dict[str, Any]) -> bool:
        """更新配置"""
        try:
            if not self.validate_config(config):
                return False
                
            self._config.update(config)
            return self.on_config_updated(self._config)
        except Exception as e:
            self._set_error(7, "Config update failed", str(e))
            return False
            
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        return self.on_validate_config(config)
        
    # ========== 子类需要实现的方法 ==========
    
    @abstractmethod
    def on_initialize(self, context: PluginContext) -> bool:
        """初始化回调"""
        pass
        
    @abstractmethod
    def on_start(self) -> bool:
        """启动回调"""
        pass
        
    @abstractmethod
    def on_stop(self) -> bool:
        """停止回调"""
        pass
        
    @abstractmethod
    def on_cleanup(self) -> bool:
        """清理回调"""
        pass
        
    @abstractmethod
    def on_config_updated(self, config: Dict[str, Any]) -> bool:
        """配置更新回调"""
        pass
        
    @abstractmethod
    def on_validate_config(self, config: Dict[str, Any]) -> bool:
        """配置验证回调"""
        pass
        
    # ========== 工具方法 ==========
    
    def _set_error(self, code: int, message: str, details: str = ""):
        """设置错误信息"""
        self._last_error = PluginError(code=code, message=message, details=details)
        self._status = PluginStatus.ERROR
        
    def _register_method(self, method_name: str, method: callable):
        """注册方法"""
        self._registered_methods[method_name] = method
        
    def _log_info(self, message: str):
        """记录信息日志"""
        self._logger.info(message)
        if self._context:
            self._context.log("info", message)
            
    def _log_warning(self, message: str):
        """记录警告日志"""
        self._logger.warning(message)
        if self._context:
            self._context.log("warning", message)
            
    def _log_error(self, message: str):
        """记录错误日志"""
        self._logger.error(message)
        if self._context:
            self._context.log("error", message)
            
    def _get_config_value(self, key: str, default_value: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default_value)


class AsyncPluginBase(PluginBase):
    """异步插件基类"""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self._async_loop = None
        
    def initialize(self, context: PluginContext) -> bool:
        """初始化插件"""
        self._context = context
        self._status = PluginStatus.LOADED
        
        try:
            # 创建异步事件循环
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
            
            # 运行异步初始化
            result = self._async_loop.run_until_complete(self.on_initialize_async(context))
            if result:
                self._status = PluginStatus.INITIALIZED
            return result
        except Exception as e:
            self._set_error(1, "Async initialize failed", str(e))
            return False
            
    def start(self) -> bool:
        """启动插件"""
        if self._status != PluginStatus.INITIALIZED:
            return False
            
        try:
            result = self._async_loop.run_until_complete(self.on_start_async())
            if result:
                self._status = PluginStatus.RUNNING
            return result
        except Exception as e:
            self._set_error(2, "Async start failed", str(e))
            return False
            
    def stop(self) -> bool:
        """停止插件"""
        if self._status != PluginStatus.RUNNING:
            return True
            
        try:
            result = self._async_loop.run_until_complete(self.on_stop_async())
            if result:
                self._status = PluginStatus.INITIALIZED
            return result
        except Exception as e:
            self._set_error(3, "Async stop failed", str(e))
            return False
            
    def cleanup(self) -> bool:
        """清理插件"""
        try:
            if self._async_loop:
                result = self._async_loop.run_until_complete(self.on_cleanup_async())
                self._async_loop.close()
                self._async_loop = None
            else:
                result = True
                
            self._status = PluginStatus.UNKNOWN
            return result
        except Exception as e:
            self._set_error(4, "Async cleanup failed", str(e))
            return False
            
    # ========== 异步方法 ==========
    
    @abstractmethod
    async def on_initialize_async(self, context: PluginContext) -> bool:
        """异步初始化回调"""
        pass
        
    @abstractmethod
    async def on_start_async(self) -> bool:
        """异步启动回调"""
        pass
        
    @abstractmethod
    async def on_stop_async(self) -> bool:
        """异步停止回调"""
        pass
        
    @abstractmethod
    async def on_cleanup_async(self) -> bool:
        """异步清理回调"""
        pass
        
    async def call_method_async(self, method_name: str, args: List[Any]) -> Any:
        """异步方法调用"""
        if method_name in self._registered_methods:
            method = self._registered_methods[method_name]
            if asyncio.iscoroutinefunction(method):
                return await method(*args)
            else:
                return method(*args)
        else:
            raise ValueError(f"Method '{method_name}' not found")


class SimplePluginBase(PluginBase):
    """简化的插件基类"""
    
    def __init__(self, name: str, version: str = "1.0.0", description: str = ""):
        metadata = PluginMetadata(
            name=name,
            description=description,
            version=PluginVersion(*map(int, version.split('.')))
        )
        super().__init__(metadata)
        
    def on_initialize(self, context: PluginContext) -> bool:
        """默认初始化实现"""
        return True
        
    def on_start(self) -> bool:
        """默认启动实现"""
        return True
        
    def on_stop(self) -> bool:
        """默认停止实现"""
        return True
        
    def on_cleanup(self) -> bool:
        """默认清理实现"""
        return True
        
    def on_config_updated(self, config: Dict[str, Any]) -> bool:
        """默认配置更新实现"""
        return True
        
    def on_validate_config(self, config: Dict[str, Any]) -> bool:
        """默认配置验证实现"""
        return True


# ========== 插件注册装饰器 ==========

def register_plugin_method(method_name: str = None):
    """插件方法注册装饰器"""
    def decorator(func):
        func._is_plugin_method = True
        func._method_name = method_name or func.__name__
        return func
    return decorator


def auto_register_methods(plugin_class):
    """自动注册插件方法的类装饰器"""
    original_init = plugin_class.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        
        # 自动注册标记的方法
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_plugin_method'):
                method_name = getattr(attr, '_method_name', attr_name)
                self._register_method(method_name, attr)
                
    plugin_class.__init__ = new_init
    return plugin_class


# ========== 示例插件 ==========

@auto_register_methods
class ExamplePlugin(SimplePluginBase):
    """示例插件"""
    
    def __init__(self):
        super().__init__(
            name="example_plugin",
            version="1.0.0",
            description="An example plugin for demonstration"
        )
        
    @register_plugin_method("hello")
    def say_hello(self, name: str = "World") -> str:
        """打招呼方法"""
        return f"Hello, {name}!"
        
    @register_plugin_method("add")
    def add_numbers(self, a: int, b: int) -> int:
        """加法方法"""
        return a + b
        
    @register_plugin_method("get_info")
    def get_plugin_info(self) -> Dict[str, Any]:
        """获取插件信息"""
        return {
            "name": self._metadata.name,
            "version": str(self._metadata.version),
            "status": self._status.name,
            "methods": self.get_supported_methods()
        }


if __name__ == "__main__":
    # 测试示例
    plugin = ExamplePlugin()
    context = PluginContext()
    
    print("初始化插件...")
    plugin.initialize(context)
    
    print("启动插件...")
    plugin.start()
    
    print("调用插件方法...")
    print(plugin.call_method("hello", ["Hushell"]))
    print(plugin.call_method("add", [10, 20]))
    print(plugin.call_method("get_info", []))
    
    print("停止插件...")
    plugin.stop()
    plugin.cleanup()