from typing import Dict, Set
from fastapi import WebSocket
import json
from datetime import datetime, timedelta
import uuid
from models import ChatMessage, ChatSession
from data_store import data_store
import asyncio

class ChatManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def connect(self, websocket: WebSocket, session_id: str, user_id: str):
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        
        self.active_connections[session_id].add(websocket)
        self.user_sessions[user_id] = session_id
    
    def disconnect(self, websocket: WebSocket, session_id: str, user_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
    
    async def send_message(self, session_id: str, message: ChatMessage):
        if session_id in self.active_connections:
            message_data = {
                "id": message.id,
                "sender_id": message.sender_id,
                "message": message.message,
                "timestamp": message.timestamp.isoformat()
            }
            
            disconnected = set()
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(json.dumps(message_data))
                except:
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[session_id].discard(conn)
    
    def is_session_expired(self, session: ChatSession) -> bool:
        return datetime.utcnow() > session.expires_at or len(data_store.get_messages(session.id)) >= 25
    
    def create_chat_session(self, item_id: str, user_id: str, item_owner_id: str) -> ChatSession:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=30)
        
        session = ChatSession(
            id=session_id,
            item_id=item_id,
            participants=[user_id, item_owner_id],
            messages=[],
            created_at=now,
            expires_at=expires_at,
            is_active=True
        )
        
        data_store.add_chat_session(session)
        return session

chat_manager = ChatManager()

