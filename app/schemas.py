from pydantic import BaseModel, EmailStr
from typing import Optional, Literal, List
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        from_attributes = True


# ── Chat ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent_used: Literal["knowledge", "web", "both", "none"]
    session_id: str
    message_id: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    agent_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class SessionDetail(SessionOut):
    messages: List[MessageOut] = []
