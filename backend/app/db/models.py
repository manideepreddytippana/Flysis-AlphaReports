
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Enum, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    union_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    email = Column(String(320))
    avatar = Column(Text)
    role = Column(Enum("user", "admin", name="user_role"), default="user", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_sign_in_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(50), nullable=False)
    page_count = Column(Integer, default=0)
    python_doc_id = Column(String(100))
    status = Column(
        Enum("uploading", "processing", "ready", "error", name="document_status"),
        default="uploading"
    )
    extracted_summary = Column(Text)
    error_message = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="document", cascade="all, delete-orphan")
    extraction_tasks = relationship("ExtractionTask", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    chunk_type = Column(
        Enum("text", "table", "figure", "heading", name="chunk_type"),
        default="text"
    )
    section_title = Column(String(255))
    embedding = Column(Vector(384))  
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("Document", back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    model_used = Column(String(50), default="sarvam-108b")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    document = relationship("Document", back_populates="chat_sessions")
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer)
    sources = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")


class ExtractionTask(Base):
    __tablename__ = "extraction_tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    task_type = Column(
        Enum("full_text", "tables", "figures", "summary", "qa", name="task_type"),
        nullable=False
    )
    status = Column(
        Enum("queued", "running", "completed", "failed", name="task_status"),
        default="queued"
    )
    python_task_id = Column(String(100))
    result_data = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    document = relationship("Document", back_populates="extraction_tasks")
