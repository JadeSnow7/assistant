"""
会话管理器 - 管理CLI会话状态和历史
"""
import json
import uuid
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import sqlite3
import aiosqlite



class SessionManager:
    """会话管理器"""
    
    def __init__(self, db_path: str = "~/.ai_assistant_sessions.db"):
        self.db_path = Path(db_path).expanduser()
        self.current_session: Optional[Session] = None
        self.sessions_cache: Dict[str, Session] = {}
        
    async def initialize(self):
        """初始化数据库"""
        await self._create_tables()
    
    async def _create_tables(self):
        """创建数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            
            await db.commit()
    
    async def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        if not title:
            title = f"会话 {now.strftime('%Y-%m-%d %H:%M')}"
        
        session = Session(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now
        )
        
        # 保存到数据库
        await self._save_session_to_db(session)
        
        # 缓存会话
        self.sessions_cache[session_id] = session
        self.current_session = session
        
        return {
            "session_id": session_id,
            "title": title,
            "created_at": now.isoformat()
        }
    
    async def get_session(self, session_id: str) -> Optional['Session']:
        """获取会话"""
        # 先检查缓存
        if session_id in self.sessions_cache:
            return self.sessions_cache[session_id]
        
        # 从数据库加载
        return await self._load_session_from_db(session_id)
    
    async def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, title, created_at, updated_at, metadata
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            async for row in cursor:
                sessions.append({
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "updated_at": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {}
                })
            
            return sessions
    
    async def add_message(self, session_id: str, role: str, content: str, 
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """添加消息到会话"""
        try:
            now = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO messages (session_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    role,
                    content,
                    now,
                    json.dumps(metadata) if metadata else None
                ))
                
                await db.commit()
            
            # 更新会话的最后更新时间
            await self._update_session_timestamp(session_id, now)
            
            return True
            
        except Exception:
            return False
    
    async def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取会话消息"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT role, content, timestamp, metadata
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (session_id, limit))
            
            messages = []
            async for row in cursor:
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {}
                })
            
            return messages
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 删除消息
                await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                
                # 删除会话
                await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                
                await db.commit()
            
            # 从缓存中移除
            if session_id in self.sessions_cache:
                del self.sessions_cache[session_id]
            
            return True
            
        except Exception:
            return False
    
    async def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题"""
        try:
            now = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE sessions 
                    SET title = ?, updated_at = ?
                    WHERE id = ?
                """, (title, now, session_id))
                
                await db.commit()
            
            # 更新缓存
            if session_id in self.sessions_cache:
                self.sessions_cache[session_id].title = title
                self.sessions_cache[session_id].updated_at = now
            
            return True
            
        except Exception:
            return False
    
    async def cleanup(self):
        """清理资源"""
        # 保存当前会话状态
        if self.current_session:
            await self._save_session_to_db(self.current_session)
        
        # 清空缓存
        self.sessions_cache.clear()
        self.current_session = None
    
    async def _save_session_to_db(self, session: 'Session'):
        """保存会话到数据库"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO sessions (id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session.id,
                session.title,
                session.created_at,
                session.updated_at,
                json.dumps(session.metadata)
            ))
            
            await db.commit()
    
    async def _load_session_from_db(self, session_id: str) -> Optional['Session']:
        """从数据库加载会话"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, title, created_at, updated_at, metadata
                FROM sessions
                WHERE id = ?
            """, (session_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            session = Session(
                id=row[0],
                title=row[1],
                created_at=datetime.fromisoformat(row[2]),
                updated_at=datetime.fromisoformat(row[3]),
                metadata=json.loads(row[4]) if row[4] else {}
            )
            
            # 缓存会话
            self.sessions_cache[session_id] = session
            
            return session
    
    async def _update_session_timestamp(self, session_id: str, timestamp: datetime):
        """更新会话时间戳"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions 
                SET updated_at = ?
                WHERE id = ?
            """, (timestamp, session_id))
            
            await db.commit()
        
        # 更新缓存
        if session_id in self.sessions_cache:
            self.sessions_cache[session_id].updated_at = timestamp

        self.id = id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata or {}
        self.messages: List[Dict[str, Any]] = []
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加消息到会话"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """获取会话上下文"""
        return self.messages[-max_messages:] if self.messages else []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "message_count": len(self.messages)
        }