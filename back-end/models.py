from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class ItemType(str, Enum):
    LOST = "lost"
    FOUND = "found"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str
    email: str
    name: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class ItemCreate(BaseModel):
    title: str
    description: str
    type: ItemType
    location: str
    image_url: Optional[str] = None
    contact_info: str

class Item(BaseModel):
    id: str
    title: str
    description: str
    type: ItemType
    location: str
    image_url: Optional[str] = None
    contact_info: str
    user_id: str
    created_at: datetime

class ChatMessage(BaseModel):
    id: str
    session_id: str
    sender_id: str
    message: str
    timestamp: datetime

class ChatSession(BaseModel):
    id: str
    item_id: str
    participants: List[str]
    messages: List[ChatMessage]
    created_at: datetime
    expires_at: datetime
    is_active: bool

class AdminStats(BaseModel):
    total_users: int
    total_items: int
    active_chats: int

