"""
认证模块
"""
import hashlib
import secrets
from typing import Optional, List
from datetime import datetime, timedelta

from core.config import settings


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.api_keys = set(settings.api_keys)
        self.session_tokens: dict = {}  # 临时会话token
        self.token_expiry = timedelta(hours=24)
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证API密钥"""
        if not self.api_keys:
            return True  # 没有配置API密钥时允许所有请求
        
        return api_key in self.api_keys
    
    def generate_session_token(self, user_id: str) -> str:
        """生成会话token"""
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + self.token_expiry
        
        self.session_tokens[token] = {
            "user_id": user_id,
            "created_at": datetime.now(),
            "expires_at": expiry
        }
        
        return token
    
    def verify_session_token(self, token: str) -> Optional[str]:
        """验证会话token"""
        if token not in self.session_tokens:
            return None
        
        token_info = self.session_tokens[token]
        
        # 检查是否过期
        if datetime.now() > token_info["expires_at"]:
            del self.session_tokens[token]
            return None
        
        return token_info["user_id"]
    
    def revoke_session_token(self, token: str) -> bool:
        """撤销会话token"""
        if token in self.session_tokens:
            del self.session_tokens[token]
            return True
        return False
    
    def cleanup_expired_tokens(self):
        """清理过期token"""
        now = datetime.now()
        expired_tokens = [
            token for token, info in self.session_tokens.items()
            if now > info["expires_at"]
        ]
        
        for token in expired_tokens:
            del self.session_tokens[token]
        
        return len(expired_tokens)


# 全局认证管理器实例
auth_manager = AuthManager()