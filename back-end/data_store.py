from typing import Dict, List
import threading

class DataStore:
    def __init__(self):
        self.users: Dict[str, "User"] = {}
        self.items: Dict[str, "Item"] = {}
        self.chat_sessions: Dict[str, "ChatSession"] = {}
        self.messages: Dict[str, List["ChatMessage"]] = {}
        self.lock = threading.Lock()
    
    def add_user(self, user) -> None:
        self.users[user.id] = user
    
    def get_user_by_email(self, email: str):
        from models import User  # moved here
        with self.lock:
            for user in self.users.values():
                if user.email == email:
                    return user
            return None
    
    def get_user_by_id(self, user_id: str):
        with self.lock:
            return self.users.get(user_id)
    
    def add_item(self, item) -> None:
        with self.lock:
            self.items[item.id] = item
    
    def get_all_items(self) -> List:
        with self.lock:
            return list(self.items.values())
    
    def get_item_by_id(self, item_id: str):
        with self.lock:
            return self.items.get(item_id)
    
    def add_chat_session(self, session) -> None:
        with self.lock:
            self.chat_sessions[session.id] = session
            self.messages[session.id] = []
    
    def get_chat_session(self, session_id: str):
        with self.lock:
            return self.chat_sessions.get(session_id)
    
    def add_message(self, message) -> None:
        with self.lock:
            if message.session_id in self.messages:
                self.messages[message.session_id].append(message)
    
    def get_messages(self, session_id: str) -> List:
        with self.lock:
            return self.messages.get(session_id, [])
    
    def reset_all(self) -> None:
        with self.lock:
            self.users.clear()
            self.items.clear()
            self.chat_sessions.clear()
            self.messages.clear()

# Global data store instance
data_store = DataStore()

