
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Enum, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
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
    
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


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
