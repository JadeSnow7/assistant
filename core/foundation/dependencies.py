"""
依赖注入
"""
from fastapi import Depends, HTTPException, Header
from typing import Optional

from services.agent.orchestrator import AgentOrchestrator
from core.foundation.config.config import settings


async def get_orchestrator():
    """获取Agent调度器实例"""
    # 这里应该从应用状态中获取
    # 在实际实现中，orchestrator会在应用启动时创建并存储在app.state中
    from main import app
    if hasattr(app.state, 'orchestrator'):
        return app.state.orchestrator
    else:
        raise HTTPException(status_code=503, detail="服务未就绪")


async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前用户"""
    # 简单的API密钥验证
    if not settings.api_keys:
        # 如果没有配置API密钥，则允许所有请求
        return "anonymous"
    
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="认证格式错误")
    
    token = authorization[7:]  # 去掉 "Bearer " 前缀
    
    if token not in settings.api_keys:
        raise HTTPException(status_code=401, detail="认证信息无效")
    
    return token[:8]  # 返回部分token作为用户标识


def verify_api_key(api_key: str) -> bool:
    """验证API密钥"""
    if not settings.api_keys:
        return True
    
    return api_key in settings.api_keys