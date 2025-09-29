"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    app_name: str = "AI Assistant"
    version: str = "1.0.0"
    debug: bool = False
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # gRPC配置
    grpc_server_address: str = "localhost:50051"
    grpc_timeout: int = 30
    
    # 安全配置
    allowed_origins: List[str] = ["*"]
    api_keys: List[str] = []
    
    # 数据库配置
    database_url: str = "sqlite:///./ai_assistant.db"
    redis_url: str = "redis://localhost:6379"
    
    # AI模型配置
    local_model_path: str = "./models"
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "qwen2.5:4b"
    
    # 云端模型配置 
    cloud_api_key: Optional[str] = None
    cloud_api_endpoint: str = "https://api.openai.com/v1"
    cloud_model_type: str = "openai"  # 支持: openai, gemini
    
    # Google Gemini配置
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro"
    gemini_generation_config: dict = {
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": 2048,
    }
    
    # 插件配置
    plugin_dir: str = "./plugins"
    max_plugin_execution_time: int = 30
    
    # 记忆系统配置
    memory_cache_size: int = 1000
    memory_similarity_threshold: float = 0.7
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()