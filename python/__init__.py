"""
AI Assistant Python应用层
"""

__version__ = "1.0.0"
__author__ = "AI Assistant Team"
__description__ = "智能AI助手系统Python应用层"

from .core.config import settings
from .agent.orchestrator import AgentOrchestrator

__all__ = ["settings", "AgentOrchestrator"]