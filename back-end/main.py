from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
import os
from dotenv import load_dotenv

from models import *
from auth import *
from chat_manager import chat_manager
from data_store import data_store

load_dotenv()

app = FastAPI(title="Reclaimr API", description="College Lost & Found Platform", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication endpoints
@app.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Verify college email
    if not verify_college_email(user_data.email):
        raise HTTPException(
            status_code=400,
            detail=f"Only {COLLEGE_EMAIL_DOMAIN} email addresses are allowed"
        )
    
    # Check if user already exists
    existing_user = data_store.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)
    
    user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        created_at=datetime.utcnow()
    )
    
    data_store.add_user(user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = data_store.get_user_by_email(user_data.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Note: In production, you'd verify the password here
    # For simplicity, we're skipping password verification in this example
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Item reporting endpoints
@app.post("/report", response_model=Item)
async def report_item(item_data: ItemCreate, current_user: User = Depends(get_current_user)):
    item_id = str(uuid.uuid4())
    
    item = Item(
        id=item_id,
        title=item_data.title,
        description=item_data.description,
        type=item_data.type,
        location=item_data.location,
        image_url=item_data.image_url,
        contact_info=item_data.contact_info,
        user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    
    data_store.add_item(item)
    return item

@app.get("/items", response_model=List[Item])
async def get_items(
    type: Optional[ItemType] = None,
    location: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    items = data_store.get_all_items()
    
    # Apply filters
    if type:
        items = [item for item in items if item.type == type]
    if location:
        items = [item for item in items if location.lower() in item.location.lower()]
    
    return items

@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: str, current_user: User = Depends(get_current_user)):
    item = data_store.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

# Image upload endpoint (mock)
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # Mock image upload - in production, you'd upload to cloud storage
    mock_url = f"https://storage.reclaimr.com/images/{uuid.uuid4()}.jpg"
    return {"image_url": mock_url}

# Chat endpoints
@app.post("/chat/create-session", response_model=ChatSession)
async def create_chat_session(item_id: str, current_user: User = Depends(get_current_user)):
    item = data_store.get_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot chat with yourself")
    
    session = chat_manager.create_chat_session(item_id, current_user.id, item.user_id)
    return session

@app.websocket("/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # Note: In production, you'd verify the user's token here
    # For simplicity, we're accepting any connection
    
    session = data_store.get_chat_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    if chat_manager.is_session_expired(session):
        await websocket.close(code=4003, reason="Session expired")
        return
    
    # For demo purposes, using a mock user_id
    user_id = "mock_user_id"
    
    await chat_manager.connect(websocket, session_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Create message
            message = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                sender_id=user_id,
                message=data,
                timestamp=datetime.utcnow()
            )
            
            data_store.add_message(message)
            await chat_manager.send_message(session_id, message)
            
            # Check if session should expire after this message
            if len(data_store.get_messages(session_id)) >= 25:
                session.is_active = False
                await websocket.close(code=4002, reason="Message limit reached")
                break
                
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, session_id, user_id)

# Admin endpoints
@app.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats():
    active_chats = len([s for s in data_store.chat_sessions.values() if s.is_active])
    
    return AdminStats(
        total_users=len(data_store.users),
        total_items=len(data_store.items),
        active_chats=active_chats
    )

@app.delete("/admin/reset")
async def reset_data():
    data_store.reset_all()
    return {"message": "All data has been reset"}

@app.get("/")
async def root():
    return {"message": "Reclaimr API is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
