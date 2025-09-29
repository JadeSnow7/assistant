"""
动态配置管理系统
"""
import os
import yaml
import json
import asyncio
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


logger = logging.getLogger(__name__)


@dataclass
class ConfigEvent:
    """配置变更事件"""
    timestamp: datetime
    config_path: str
    change_type: str  # modified, added, deleted
    changed_keys: List[str]
    old_value: Any = None
    new_value: Any = None


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件监听器"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        super().__init__()
    
    def on_modified(self, event):
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix in ['.yaml', '.yml', '.json']:
                asyncio.create_task(
                    self.config_manager._handle_file_change(str(file_path))
                )


class DynamicConfigManager:
    """动态配置管理器"""
    
    def __init__(self, config_paths: List[str] = None):
        self.config_paths = config_paths or []
        self.configs: Dict[str, Dict[str, Any]] = {}
        self.observers: List[Observer] = []
        self.change_callbacks: List[Callable] = []
        self.config_history: List[ConfigEvent] = []
        self.lock = threading.Lock()
        
        # 环境变量替换模式
        self.env_pattern = "${}"
    
    async def initialize(self, default_config_path: str = None):
        """初始化配置管理器"""
        try:
            logger.info("初始化动态配置管理器...")
            
            # 加载默认配置
            if default_config_path:
                await self.load_config_file(default_config_path, "default")
            
            # 加载所有指定的配置文件
            for config_path in self.config_paths:
                if os.path.exists(config_path):
                    await self.load_config_file(config_path)
            
            # 启动文件监听
            await self._start_file_watching()
            
            logger.info("配置管理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"配置管理器初始化失败: {e}")
            return False
    
    async def load_config_file(self, file_path: str, config_name: str = None):
        """加载配置文件"""
        try:
            config_name = config_name or Path(file_path).stem
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    raw_config = yaml.safe_load(f)
                elif file_path.endswith('.json'):
                    raw_config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {file_path}")
            
            # 环境变量替换
            processed_config = self._process_env_variables(raw_config)
            
            # 配置验证
            await self._validate_config(processed_config, config_name)
            
            with self.lock:
                old_config = self.configs.get(config_name, {})
                self.configs[config_name] = processed_config
                
                # 记录变更事件
                changed_keys = self._get_changed_keys(old_config, processed_config)
                if changed_keys:
                    event = ConfigEvent(
                        timestamp=datetime.now(),
                        config_path=file_path,
                        change_type="modified",
                        changed_keys=changed_keys,
                        old_value=old_config,
                        new_value=processed_config
                    )
                    self.config_history.append(event)
                    
                    # 触发回调
                    await self._trigger_callbacks(config_name, changed_keys, event)
            
            logger.info(f"已加载配置文件: {file_path}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
            raise
    
    def _process_env_variables(self, config: Any) -> Any:
        """处理环境变量替换"""
        if isinstance(config, dict):
            return {key: self._process_env_variables(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._process_env_variables(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # 提取环境变量名
            env_var = config[2:-1]
            default_value = None
            
            # 支持默认值语法 ${VAR:default}
            if ":" in env_var:
                env_var, default_value = env_var.split(":", 1)
            
            return os.getenv(env_var, default_value)
        else:
            return config
    
    async def _validate_config(self, config: Dict[str, Any], config_name: str):
        """验证配置"""
        if config_name == "unified_api":
            # 验证统一API配置
            await self._validate_unified_api_config(config)
        # 可以添加其他配置类型的验证
    
    async def _validate_unified_api_config(self, config: Dict[str, Any]):
        """验证统一API配置"""
        required_sections = ["api", "engines", "routing"]
        
        for section in required_sections:
            if section not in config:
                raise ValueError(f"缺少必需的配置段: {section}")
        
        # 验证引擎配置
        engines = config.get("engines", {})
        enabled_engines = [name for name, cfg in engines.items() if cfg.get("enabled", False)]
        
        if not enabled_engines:
            logger.warning("没有启用的引擎，系统可能无法正常工作")
        
        # 验证API密钥
        for engine_name, engine_config in engines.items():
            if engine_config.get("enabled", False):
                if engine_name in ["openai", "gemini", "claude"]:
                    api_key = engine_config.get("api_key")
                    if not api_key or api_key.startswith("${"):
                        logger.warning(f"引擎 {engine_name} 已启用但API密钥未配置")
    
    def _get_changed_keys(self, old_config: Dict, new_config: Dict, prefix: str = "") -> List[str]:
        """获取变更的配置键"""
        changed_keys = []
        
        # 检查新增和修改的键
        for key, new_value in new_config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if key not in old_config:
                changed_keys.append(full_key)
            elif isinstance(new_value, dict) and isinstance(old_config[key], dict):
                # 递归检查嵌套字典
                nested_changes = self._get_changed_keys(
                    old_config[key], new_value, full_key
                )
                changed_keys.extend(nested_changes)
            elif new_value != old_config[key]:
                changed_keys.append(full_key)
        
        # 检查删除的键
        for key in old_config:
            if key not in new_config:
                full_key = f"{prefix}.{key}" if prefix else key
                changed_keys.append(full_key)
        
        return changed_keys
    
    async def _start_file_watching(self):
        """启动文件监听"""
        try:
            # 为每个配置文件目录创建监听器
            watched_dirs = set()
            
            for config_path in self.config_paths:
                if os.path.exists(config_path):
                    watch_dir = str(Path(config_path).parent)
                    if watch_dir not in watched_dirs:
                        observer = Observer()
                        observer.schedule(
                            ConfigFileHandler(self),
                            watch_dir,
                            recursive=False
                        )
                        observer.start()
                        self.observers.append(observer)
                        watched_dirs.add(watch_dir)
            
            logger.info(f"已启动 {len(self.observers)} 个配置文件监听器")
            
        except Exception as e:
            logger.error(f"启动文件监听失败: {e}")
    
    async def _handle_file_change(self, file_path: str):
        """处理文件变更"""
        try:
            # 延迟一下，避免文件正在写入时读取
            await asyncio.sleep(0.1)
            
            if file_path in self.config_paths:
                await self.load_config_file(file_path)
                logger.info(f"配置文件已重新加载: {file_path}")
            
        except Exception as e:
            logger.error(f"处理文件变更失败 {file_path}: {e}")
    
    async def _trigger_callbacks(self, config_name: str, changed_keys: List[str], event: ConfigEvent):
        """触发变更回调"""
        for callback in self.change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(config_name, changed_keys, event)
                else:
                    callback(config_name, changed_keys, event)
            except Exception as e:
                logger.error(f"配置变更回调执行失败: {e}")
    
    def add_change_callback(self, callback: Callable):
        """添加配置变更回调"""
        self.change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable):
        """移除配置变更回调"""
        if callback in self.change_callbacks:
            self.change_callbacks.remove(callback)
    
    def get_config(self, config_name: str = "default") -> Dict[str, Any]:
        """获取配置"""
        with self.lock:
            return self.configs.get(config_name, {}).copy()
    
    def get_nested_config(self, path: str, config_name: str = "default") -> Any:
        """获取嵌套配置值"""
        config = self.get_config(config_name)
        
        keys = path.split('.')
        current = config
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    async def update_config(self, path: str, value: Any, config_name: str = "default"):
        """更新配置值"""
        try:
            with self.lock:
                if config_name not in self.configs:
                    self.configs[config_name] = {}
                
                config = self.configs[config_name]
                keys = path.split('.')
                
                # 导航到目标位置
                current = config
                for key in keys[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # 记录旧值
                old_value = current.get(keys[-1])
                
                # 设置新值
                current[keys[-1]] = value
                
                # 记录变更事件
                event = ConfigEvent(
                    timestamp=datetime.now(),
                    config_path="runtime",
                    change_type="modified",
                    changed_keys=[path],
                    old_value=old_value,
                    new_value=value
                )
                self.config_history.append(event)
                
                # 触发回调
                await self._trigger_callbacks(config_name, [path], event)
            
            logger.info(f"配置已更新: {path} = {value}")
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise
    
    async def save_config_to_file(self, config_name: str, file_path: str):
        """保存配置到文件"""
        try:
            config = self.get_config(config_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif file_path.endswith('.json'):
                    json.dump(config, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的文件格式: {file_path}")
            
            logger.info(f"配置已保存到文件: {file_path}")
            
        except Exception as e:
            logger.error(f"保存配置到文件失败: {e}")
            raise
    
    def get_config_history(self, limit: int = 100) -> List[ConfigEvent]:
        """获取配置变更历史"""
        with self.lock:
            return self.config_history[-limit:].copy()
    
    def export_config(self, config_name: str = "default") -> str:
        """导出配置为JSON字符串"""
        config = self.get_config(config_name)
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    async def import_config(self, config_json: str, config_name: str = "default"):
        """导入配置JSON"""
        try:
            config = json.loads(config_json)
            await self._validate_config(config, config_name)
            
            with self.lock:
                old_config = self.configs.get(config_name, {})
                self.configs[config_name] = config
                
                # 记录变更事件
                changed_keys = self._get_changed_keys(old_config, config)
                if changed_keys:
                    event = ConfigEvent(
                        timestamp=datetime.now(),
                        config_path="import",
                        change_type="modified",
                        changed_keys=changed_keys,
                        old_value=old_config,
                        new_value=config
                    )
                    self.config_history.append(event)
                    
                    # 触发回调
                    await self._trigger_callbacks(config_name, changed_keys, event)
            
            logger.info(f"配置导入成功: {config_name}")
            
        except Exception as e:
            logger.error(f"配置导入失败: {e}")
            raise
    
    def get_available_configs(self) -> List[str]:
        """获取可用的配置名称列表"""
        with self.lock:
            return list(self.configs.keys())
    
    async def reload_all_configs(self):
        """重新加载所有配置文件"""
        try:
            for config_path in self.config_paths:
                if os.path.exists(config_path):
                    await self.load_config_file(config_path)
            
            logger.info("所有配置文件已重新加载")
            
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            raise
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 停止文件监听器
            for observer in self.observers:
                observer.stop()
                observer.join()
            
            self.observers.clear()
            logger.info("配置管理器资源已清理")
            
        except Exception as e:
            logger.error(f"清理配置管理器资源失败: {e}")


# 全局配置管理器实例
config_manager = DynamicConfigManager()


async def initialize_config_manager(config_paths: List[str] = None):
    """初始化全局配置管理器"""
    global config_manager
    
    if config_paths:
        config_manager.config_paths = config_paths
    
    # 默认配置文件路径
    default_paths = [
        "configs/unified_api.yaml",
        "configs/app.yaml",
        "configs/logging.yaml"
    ]
    
    if not config_manager.config_paths:
        config_manager.config_paths = [
            path for path in default_paths if os.path.exists(path)
        ]
    
    success = await config_manager.initialize()
    return success


def get_config(path: str = None, config_name: str = "unified_api") -> Any:
    """获取配置值的便捷函数"""
    if path:
        return config_manager.get_nested_config(path, config_name)
    else:
        return config_manager.get_config(config_name)


async def update_config(path: str, value: Any, config_name: str = "unified_api"):
    """更新配置值的便捷函数"""
    await config_manager.update_config(path, value, config_name)