"""
CLI配置管理
"""
import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class CLIConfig:
    """CLI配置类"""
    
    # 显示设置
    max_width: int = 120
    show_timestamps: bool = True
    show_model_info: bool = True
    show_performance_stats: bool = True
    
    # 主题设置
    theme: str = "dark"  # dark, light, auto
    accent_color: str = "cyan"
    
    # 行为设置
    auto_save_history: bool = True
    stream_by_default: bool = True
    confirm_exit: bool = False
    
    # 调试设置
    debug: bool = False
    verbose: bool = False
    
    def __post_init__(self):
        """初始化后处理"""
        # 从环境变量读取配置
        self.debug = os.getenv("CLI_DEBUG", "false").lower() == "true"
        self.verbose = os.getenv("CLI_VERBOSE", "false").lower() == "true"
        
        # 从配置文件读取（如果存在）
        self._load_config_file()
    
    def _load_config_file(self):
        """从配置文件加载设置"""
        config_path = os.path.expanduser("~/.ai_assistant_cli.json")
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # 更新配置
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception:
                pass  # 忽略配置文件错误
    
    def save_config(self):
        """保存配置到文件"""
        config_path = os.path.expanduser("~/.ai_assistant_cli.json")
        try:
            import json
            config_data = {
                "max_width": self.max_width,
                "show_timestamps": self.show_timestamps,
                "show_model_info": self.show_model_info,
                "show_performance_stats": self.show_performance_stats,
                "theme": self.theme,
                "accent_color": self.accent_color,
                "auto_save_history": self.auto_save_history,
                "stream_by_default": self.stream_by_default,
                "confirm_exit": self.confirm_exit
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception:
            pass  # 忽略保存错误