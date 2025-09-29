"""
统一API适配器包
"""
from .base import (
    BaseAdapter, AdapterManager, UnifiedChatRequest, UnifiedChatResponse,
    UnifiedStreamChunk, ModelInfo, ProviderType, EngineType
)
from .openai_adapter import OpenAIAdapter
from .gemini_adapter import GeminiAdapter
from .claude_adapter import ClaudeAdapter
from .local_adapter import LlamaCppAdapter, OllamaAdapter

__all__ = [
    "BaseAdapter",
    "AdapterManager",
    "UnifiedChatRequest", 
    "UnifiedChatResponse",
    "UnifiedStreamChunk",
    "ModelInfo",
    "ProviderType",
    "EngineType",
    "OpenAIAdapter",
    "GeminiAdapter", 
    "ClaudeAdapter",
    "LlamaCppAdapter",
    "OllamaAdapter"
]