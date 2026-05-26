from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(String(36), primary_key=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(255), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions   = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id            = Column(String(128), primary_key=True)
    user_id       = Column(String(36), ForeignKey("users.id"), nullable=False)
    title         = Column(String(120), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    user          = relationship("User", back_populates="sessions")
    messages      = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id         = Column(String(36), primary_key=True)
    session_id = Column(String(128), ForeignKey("sessions.id"), nullable=False)
    role       = Column(String(10), nullable=False)   # user | assistant
    content    = Column(Text, nullable=False)
    agent_used = Column(String(20), nullable=True)    # knowledge | web | both | none
    created_at = Column(DateTime, default=datetime.utcnow)
    session    = relationship("Session", back_populates="messages")
