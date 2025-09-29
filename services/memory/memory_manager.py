"""
记忆管理系统
"""
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import sqlite3
import aiosqlite
from dataclasses import dataclass

from interfaces.api.schemas import MemoryEntry
from core.foundation.config.config import settings


logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """对话轮次"""
    user_message: str
    ai_response: str
    timestamp: datetime
    metadata: Dict[str, Any] = None


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self):
        self.db_path = settings.database_url.replace("sqlite:///", "")
        self.cache: Dict[str, List[ConversationTurn]] = {}
        self.cache_size = settings.memory_cache_size
        self.similarity_threshold = settings.memory_similarity_threshold
        
        # 内存中的会话缓存
        self.session_cache: Dict[str, Dict[str, Any]] = {}
        self.initialized = False
    
    async def initialize(self):
        """初始化记忆系统"""
        try:
            await self._create_tables()
            self.initialized = True
            logger.info("记忆管理系统初始化完成")
        except Exception as e:
            logger.error(f"记忆系统初始化失败: {e}")
            raise
    
    async def _create_tables(self):
        """创建数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    importance_score REAL DEFAULT 0.5,
                    embedding BLOB
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_info (
                    session_id TEXT PRIMARY KEY,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_turns INTEGER DEFAULT 0,
                    user_profile TEXT,
                    preferences TEXT
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON conversations(session_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON conversations(timestamp)
            """)
            
            await db.commit()
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文"""
        try:
            # 首先检查缓存
            if session_id in self.session_cache:
                cached = self.session_cache[session_id]
                # 检查缓存是否过期（5分钟）
                if datetime.now() - cached.get("last_access", datetime.min) < timedelta(minutes=5):
                    cached["last_access"] = datetime.now()
                    return cached["context"]
            
            # 从数据库获取最近的对话记录
            recent_conversations = await self._get_recent_conversations(session_id, limit=10)
            
            # 获取会话信息
            session_info = await self._get_session_info(session_id)
            
            context = {
                "session_id": session_id,
                "recent_messages": [
                    {
                        "user": conv.user_message,
                        "ai": conv.ai_response,
                        "timestamp": conv.timestamp.isoformat()
                    }
                    for conv in recent_conversations
                ],
                "total_turns": len(recent_conversations),
                "session_info": session_info,
                "last_activity": datetime.now().isoformat()
            }
            
            # 缓存结果
            self.session_cache[session_id] = {
                "context": context,
                "last_access": datetime.now()
            }
            
            return context
            
        except Exception as e:
            logger.error(f"获取会话上下文失败: {e}")
            return {
                "session_id": session_id,
                "recent_messages": [],
                "total_turns": 0,
                "session_info": {},
                "last_activity": datetime.now().isoformat()
            }
    
    async def update_session(self, 
                           session_id: str, 
                           user_message: str, 
                           ai_response: str,
                           metadata: Dict[str, Any] = None):
        """更新会话记录"""
        try:
            # 计算重要性评分
            importance_score = self._calculate_importance(user_message, ai_response)
            
            # 存储到数据库
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO conversations 
                    (session_id, user_message, ai_response, metadata, importance_score)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    user_message,
                    ai_response,
                    json.dumps(metadata) if metadata else None,
                    importance_score
                ))
                
                # 更新会话信息
                await db.execute("""
                    INSERT OR REPLACE INTO session_info 
                    (session_id, last_activity, total_turns)
                    VALUES (?, ?, COALESCE(
                        (SELECT total_turns FROM session_info WHERE session_id = ?) + 1, 1)
                    )
                """, (session_id, datetime.now(), session_id))
                
                await db.commit()
            
            # 更新缓存
            if session_id in self.session_cache:
                context = self.session_cache[session_id]["context"]
                context["recent_messages"].append({
                    "user": user_message,
                    "ai": ai_response,
                    "timestamp": datetime.now().isoformat()
                })
                # 保持最近10条记录
                context["recent_messages"] = context["recent_messages"][-10:]
                context["total_turns"] += 1
                context["last_activity"] = datetime.now().isoformat()
            
            logger.debug(f"会话 {session_id} 记录已更新")
            
        except Exception as e:
            logger.error(f"更新会话记录失败: {e}")
    
    async def search_memory(self, 
                          query_text: str, 
                          session_id: Optional[str] = None,
                          limit: int = 10) -> List[MemoryEntry]:
        """搜索记忆内容"""
        try:
            # 简单的文本匹配搜索
            # 实际实现中可以使用向量相似度搜索
            
            conditions = ["(user_message LIKE ? OR ai_response LIKE ?)"]
            params = [f"%{query_text}%", f"%{query_text}%"]
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            sql = f"""
                SELECT id, session_id, user_message, ai_response, 
                       timestamp, metadata, importance_score
                FROM conversations 
                WHERE {' AND '.join(conditions)}
                ORDER BY importance_score DESC, timestamp DESC
                LIMIT ?
            """
            params.append(limit)
            
            results = []
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(sql, params) as cursor:
                    async for row in cursor:
                        results.append(MemoryEntry(
                            id=str(row[0]),
                            session_id=row[1],
                            content=f"用户: {row[2]}\nAI: {row[3]}",
                            content_type="conversation",
                            metadata=json.loads(row[5]) if row[5] else {},
                            created_at=datetime.fromisoformat(row[4]),
                            importance=row[6]
                        ))
            
            return results
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []
    
    async def get_active_session_count(self) -> int:
        """获取活跃会话数量"""
        try:
            # 统计最近1小时内有活动的会话
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT COUNT(DISTINCT session_id) 
                    FROM conversations 
                    WHERE timestamp > ?
                """, (cutoff_time,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"获取活跃会话数失败: {e}")
            return 0
    
    async def clear_session(self, session_id: str) -> bool:
        """清除会话记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
                await db.execute("DELETE FROM session_info WHERE session_id = ?", (session_id,))
                await db.commit()
            
            # 清除缓存
            if session_id in self.session_cache:
                del self.session_cache[session_id]
            
            logger.info(f"会话 {session_id} 的记忆已清除")
            return True
            
        except Exception as e:
            logger.error(f"清除会话记忆失败: {e}")
            return False
    
    async def _get_recent_conversations(self, session_id: str, limit: int = 10) -> List[ConversationTurn]:
        """获取最近的对话记录"""
        conversations = []
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_message, ai_response, timestamp, metadata
                    FROM conversations 
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit)) as cursor:
                    async for row in cursor:
                        conversations.append(ConversationTurn(
                            user_message=row[0],
                            ai_response=row[1],
                            timestamp=datetime.fromisoformat(row[2]),
                            metadata=json.loads(row[3]) if row[3] else {}
                        ))
            
            # 按时间正序返回
            return list(reversed(conversations))
            
        except Exception as e:
            logger.error(f"获取对话记录失败: {e}")
            return []
    
    async def _get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT created_at, last_activity, total_turns, user_profile, preferences
                    FROM session_info 
                    WHERE session_id = ?
                """, (session_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return {
                            "created_at": row[0],
                            "last_activity": row[1],
                            "total_turns": row[2],
                            "user_profile": json.loads(row[3]) if row[3] else {},
                            "preferences": json.loads(row[4]) if row[4] else {}
                        }
            
            return {}
            
        except Exception as e:
            logger.error(f"获取会话信息失败: {e}")
            return {}
    
    def _calculate_importance(self, user_message: str, ai_response: str) -> float:
        """计算对话重要性评分"""
        # 简单的重要性评分算法
        # 实际实现中可以使用更复杂的算法
        
        importance = 0.5  # 基础分数
        
        # 长度加分
        total_length = len(user_message) + len(ai_response)
        if total_length > 200:
            importance += 0.1
        if total_length > 500:
            importance += 0.1
        
        # 关键词加分
        keywords = ["重要", "记住", "注意", "关键", "问题", "帮助", "解决"]
        for keyword in keywords:
            if keyword in user_message or keyword in ai_response:
                importance += 0.1
                break
        
        # 问号加分（表示用户有疑问）
        if "?" in user_message or "？" in user_message:
            importance += 0.05
        
        return min(importance, 1.0)
    
    def is_healthy(self) -> bool:
        """健康检查"""
        return self.initialized
    
    async def cleanup(self):
        """清理资源"""
        self.session_cache.clear()
        logger.info("记忆管理器资源已清理")