"""
插件管理系统
"""
import os
import json
import asyncio
import logging
import importlib.util
from typing import Dict, Any, List, Optional
from pathlib import Path

from models.schemas import PluginInfo, PluginExecuteRequest, PluginExecuteResponse
from sdk.plugin_base import PluginBase
from core.config import settings


logger = logging.getLogger(__name__)


class PluginManager:
    """Python插件管理器"""
    
    def __init__(self):
        self.plugin_dir = Path(settings.plugin_dir)
        self.loaded_plugins: Dict[str, PluginBase] = {}
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        self.max_execution_time = settings.max_plugin_execution_time
        self.initialized = False
    
    async def initialize(self):
        """初始化插件管理器"""
        try:
            # 创建插件目录
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # 扫描并加载插件
            await self._scan_and_load_plugins()
            
            self.initialized = True
            logger.info(f"插件管理器初始化完成，已加载 {len(self.loaded_plugins)} 个插件")
            
        except Exception as e:
            logger.error(f"插件管理器初始化失败: {e}")
            raise
    
    async def _scan_and_load_plugins(self):
        """扫描并加载插件"""
        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir() and (plugin_path / "plugin.json").exists():
                try:
                    await self._load_plugin(plugin_path)
                except Exception as e:
                    logger.error(f"加载插件 {plugin_path.name} 失败: {e}")
    
    async def _load_plugin(self, plugin_path: Path):
        """加载单个插件"""
        plugin_name = plugin_path.name
        
        try:
            # 读取插件配置
            config_file = plugin_path / "plugin.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证配置
            if not self._validate_plugin_config(config):
                logger.error(f"插件 {plugin_name} 配置无效")
                return
            
            # 加载Python模块
            main_file = plugin_path / config.get("entry_point", "main.py")
            if not main_file.exists():
                logger.error(f"插件 {plugin_name} 入口文件不存在: {main_file}")
                return
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"plugin_{plugin_name}", 
                main_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取插件实例
            if hasattr(module, 'plugin_instance'):
                plugin_instance = module.plugin_instance
            else:
                logger.error(f"插件 {plugin_name} 没有 plugin_instance 属性")
                return
            
            # 验证插件实例
            if not isinstance(plugin_instance, PluginBase):
                logger.error(f"插件 {plugin_name} 实例不是 PluginBase 的子类")
                return
            
            # 初始化插件
            plugin_config = config.get("config", {})
            if await plugin_instance.initialize(plugin_config):
                self.loaded_plugins[plugin_name] = plugin_instance
                self.plugin_configs[plugin_name] = config
                
                # 如果配置中启用了插件，则启用它
                if config.get("enabled", False):
                    plugin_instance.enable()
                
                logger.info(f"插件 {plugin_name} 加载成功")
            else:
                logger.error(f"插件 {plugin_name} 初始化失败")
                
        except Exception as e:
            logger.error(f"加载插件 {plugin_name} 时发生错误: {e}")
    
    def _validate_plugin_config(self, config: Dict[str, Any]) -> bool:
        """验证插件配置"""
        required_fields = ["name", "version", "description", "author"]
        
        for field in required_fields:
            if field not in config:
                logger.error(f"插件配置缺少必需字段: {field}")
                return False
        
        return True
    
    async def get_available_plugins(self) -> List[PluginInfo]:
        """获取可用插件列表"""
        plugins = []
        
        for plugin_name, config in self.plugin_configs.items():
            plugin_instance = self.loaded_plugins.get(plugin_name)
            
            plugins.append(PluginInfo(
                name=config["name"],
                version=config["version"],
                description=config["description"],
                author=config["author"],
                capabilities=config.get("capabilities", []),
                enabled=plugin_instance.enabled if plugin_instance else False,
                config_schema=config.get("config_schema"),
                dependencies=config.get("dependencies", [])
            ))
        
        return plugins
    
    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        try:
            if plugin_name not in self.loaded_plugins:
                logger.error(f"插件 {plugin_name} 未加载")
                return False
            
            plugin = self.loaded_plugins[plugin_name]
            plugin.enable()
            
            # 更新配置文件
            await self._update_plugin_enabled_status(plugin_name, True)
            
            logger.info(f"插件 {plugin_name} 已启用")
            return True
            
        except Exception as e:
            logger.error(f"启用插件 {plugin_name} 失败: {e}")
            return False
    
    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        try:
            if plugin_name not in self.loaded_plugins:
                logger.error(f"插件 {plugin_name} 未加载")
                return False
            
            plugin = self.loaded_plugins[plugin_name]
            plugin.disable()
            
            # 更新配置文件
            await self._update_plugin_enabled_status(plugin_name, False)
            
            logger.info(f"插件 {plugin_name} 已禁用")
            return True
            
        except Exception as e:
            logger.error(f"禁用插件 {plugin_name} 失败: {e}")
            return False
    
    async def execute_plugin(self, 
                           plugin_name: str, 
                           command: str, 
                           params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行插件命令"""
        try:
            if plugin_name not in self.loaded_plugins:
                return {
                    "success": False,
                    "error": f"插件 {plugin_name} 未加载"
                }
            
            plugin = self.loaded_plugins[plugin_name]
            
            if not plugin.enabled:
                return {
                    "success": False,
                    "error": f"插件 {plugin_name} 未启用"
                }
            
            # 执行插件命令（带超时控制）
            try:
                result = await asyncio.wait_for(
                    plugin.safe_execute(command, params or {}),
                    timeout=self.max_execution_time
                )
                return result
                
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"插件 {plugin_name} 执行超时"
                }
            
        except Exception as e:
            logger.error(f"执行插件 {plugin_name} 失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """获取插件详细信息"""
        if plugin_name not in self.loaded_plugins:
            return None
        
        plugin = self.loaded_plugins[plugin_name]
        config = self.plugin_configs[plugin_name]
        
        info = plugin.get_info()
        info.update({
            "loaded": True,
            "enabled": plugin.enabled,
            "healthy": plugin.is_healthy(),
            "stats": plugin.get_stats(),
            "config": config
        })
        
        return info
    
    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            # 卸载现有插件
            if plugin_name in self.loaded_plugins:
                await self.loaded_plugins[plugin_name].cleanup()
                del self.loaded_plugins[plugin_name]
                del self.plugin_configs[plugin_name]
            
            # 重新加载插件
            plugin_path = self.plugin_dir / plugin_name
            if plugin_path.exists():
                await self._load_plugin(plugin_path)
                logger.info(f"插件 {plugin_name} 重新加载成功")
                return True
            else:
                logger.error(f"插件目录不存在: {plugin_path}")
                return False
                
        except Exception as e:
            logger.error(f"重新加载插件 {plugin_name} 失败: {e}")
            return False
    
    async def _update_plugin_enabled_status(self, plugin_name: str, enabled: bool):
        """更新插件启用状态到配置文件"""
        try:
            config_file = self.plugin_dir / plugin_name / "plugin.json"
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config["enabled"] = enabled
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 同时更新内存中的配置
            self.plugin_configs[plugin_name]["enabled"] = enabled
            
        except Exception as e:
            logger.error(f"更新插件配置失败: {e}")
    
    def get_enabled_plugins(self) -> List[str]:
        """获取已启用的插件列表"""
        enabled_plugins = []
        
        for plugin_name, plugin in self.loaded_plugins.items():
            if plugin.enabled:
                enabled_plugins.append(plugin_name)
        
        return enabled_plugins
    
    def is_healthy(self) -> bool:
        """健康检查"""
        if not self.initialized:
            return False
        
        # 检查所有启用的插件是否健康
        for plugin_name, plugin in self.loaded_plugins.items():
            if plugin.enabled and not plugin.is_healthy():
                logger.warning(f"插件 {plugin_name} 健康检查失败")
                return False
        
        return True
    
    async def cleanup(self):
        """清理资源"""
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                await plugin.cleanup()
            except Exception as e:
                logger.error(f"清理插件 {plugin_name} 失败: {e}")
        
        self.loaded_plugins.clear()
        self.plugin_configs.clear()
        logger.info("插件管理器资源已清理")