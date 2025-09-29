"""
插件SDK基类
"""
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class PluginBase(ABC):
    """插件基础类 - 所有插件必须继承此类"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"plugin.{self.__class__.__name__}")
        self.config: Dict[str, Any] = {}
        self.enabled = False
        self.initialized = False
        self.last_error: Optional[str] = None
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "avg_execution_time": 0.0,
            "last_called": None
        }
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        初始化插件
        
        Args:
            config: 插件配置字典
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def execute(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行插件命令
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        
        Returns:
            Dict[str, Any]: 插件信息
        """
        pass
    
    @abstractmethod
    async def cleanup(self):
        """清理插件资源"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        健康检查
        
        Returns:
            bool: 插件是否健康
        """
        pass
    
    async def safe_execute(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        安全执行命令 - 带错误处理和统计
        
        Args:
            command: 命令名称
            params: 命令参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        start_time = datetime.now()
        self.stats["total_calls"] += 1
        self.stats["last_called"] = start_time.isoformat()
        
        try:
            if not self.enabled:
                return {
                    "success": False,
                    "error": "插件未启用"
                }
            
            if not self.initialized:
                return {
                    "success": False,
                    "error": "插件未初始化"
                }
            
            # 执行命令
            result = await self.execute(command, params)
            
            # 更新统计
            if result.get("success", False):
                self.stats["successful_calls"] += 1
                self.last_error = None
            else:
                self.stats["failed_calls"] += 1
                self.last_error = result.get("error", "未知错误")
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            self.stats["failed_calls"] += 1
            self.last_error = str(e)
            
            return {
                "success": False,
                "error": str(e)
            }
        
        finally:
            # 更新执行时间统计
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            total_calls = self.stats["total_calls"]
            old_avg = self.stats["avg_execution_time"]
            self.stats["avg_execution_time"] = (old_avg * (total_calls - 1) + execution_time) / total_calls
    
    def enable(self):
        """启用插件"""
        self.enabled = True
        self.logger.info("插件已启用")
    
    def disable(self):
        """禁用插件"""
        self.enabled = False
        self.logger.info("插件已禁用")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取插件统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return self.stats.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取插件状态
        
        Returns:
            Dict[str, Any]: 插件状态
        """
        return {
            "enabled": self.enabled,
            "initialized": self.initialized,
            "healthy": self.is_healthy(),
            "last_error": self.last_error,
            "stats": self.get_stats()
        }
    
    def validate_params(self, params: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证参数
        
        Args:
            params: 输入参数
            schema: 参数架构
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        errors = []
        
        for param_name, param_config in schema.items():
            required = param_config.get("required", False)
            param_type = param_config.get("type", "string")
            
            if required and param_name not in params:
                errors.append(f"缺少必需参数: {param_name}")
                continue
            
            if param_name in params:
                value = params[param_name]
                
                # 类型检查
                if param_type == "string" and not isinstance(value, str):
                    errors.append(f"参数 {param_name} 应为字符串类型")
                elif param_type == "integer" and not isinstance(value, int):
                    errors.append(f"参数 {param_name} 应为整数类型")
                elif param_type == "float" and not isinstance(value, (int, float)):
                    errors.append(f"参数 {param_name} 应为数字类型")
                elif param_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"参数 {param_name} 应为布尔类型")
                elif param_type == "array" and not isinstance(value, list):
                    errors.append(f"参数 {param_name} 应为数组类型")
                elif param_type == "object" and not isinstance(value, dict):
                    errors.append(f"参数 {param_name} 应为对象类型")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class PluginError(Exception):
    """插件异常类"""
    
    def __init__(self, message: str, error_code: str = "PLUGIN_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.message,
            "error_code": self.error_code
        }


class PluginTimeout(PluginError):
    """插件超时异常"""
    
    def __init__(self, timeout_seconds: float):
        super().__init__(f"插件执行超时: {timeout_seconds}秒", "PLUGIN_TIMEOUT")
        self.timeout_seconds = timeout_seconds


class PluginConfigError(PluginError):
    """插件配置错误"""
    
    def __init__(self, message: str):
        super().__init__(f"插件配置错误: {message}", "PLUGIN_CONFIG_ERROR")


class PluginPermissionError(PluginError):
    """插件权限错误"""
    
    def __init__(self, permission: str):
        super().__init__(f"插件缺少权限: {permission}", "PLUGIN_PERMISSION_ERROR")
        self.permission = permission


# 插件装饰器
def plugin_command(command_name: str, 
                  params_schema: Optional[Dict[str, Any]] = None,
                  timeout_seconds: Optional[float] = None):
    """
    插件命令装饰器
    
    Args:
        command_name: 命令名称
        params_schema: 参数架构
        timeout_seconds: 超时时间
    """
    def decorator(func):
        async def wrapper(self, command: str, params: Dict[str, Any]):
            if command != command_name:
                return await func(self, command, params)
            
            # 参数验证
            if params_schema:
                validation = self.validate_params(params, params_schema)
                if not validation["valid"]:
                    return {
                        "success": False,
                        "error": f"参数验证失败: {', '.join(validation['errors'])}"
                    }
            
            # 超时控制
            if timeout_seconds:
                try:
                    result = await asyncio.wait_for(
                        func(self, command, params), 
                        timeout=timeout_seconds
                    )
                    return result
                except asyncio.TimeoutError:
                    raise PluginTimeout(timeout_seconds)
            else:
                return await func(self, command, params)
        
        return wrapper
    return decorator


def require_permission(permission: str):
    """
    权限检查装饰器
    
    Args:
        permission: 所需权限
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            # 这里应该检查插件是否有所需权限
            # 简化实现，实际应该与权限系统集成
            plugin_info = self.get_info()
            permissions = plugin_info.get("permissions", [])
            
            if permission not in permissions:
                raise PluginPermissionError(permission)
            
            return await func(self, *args, **kwargs)
        
        return wrapper
    return decorator