import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text, select, delete
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.db.models import DocumentChunk

logger = logging.getLogger(__name__)


@lru_cache()
def get_embedding_model():
    """Lazy-load the embedding model."""
    settings = get_settings()
    model_name = settings.embedding_model
    logger.info(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


class PgVectorStore:
    """Manages document embeddings in PostgreSQL using pgvector."""
    
    def __init__(self):
        self._embedding_model = None
    
    @property
    def embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = get_embedding_model()
        return self._embedding_model
    
    def index_document(
        self,
        db: Session,
        doc_id: int,
        chunks: List[Dict[str, Any]],
        chunk_size: int = 512,
        overlap: int = 128
    ) -> Dict[str, Any]:
        """
        Index document chunks into PostgreSQL with pgvector embeddings.
        
        Args:
            db: SQLAlchemy session
            doc_id: Document database ID
            chunks: List of chunk dicts with 'text', 'page', 'type', 'section'
            chunk_size: Target chunk size in characters
            overlap: Overlap between chunks in characters
        """
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
        db.flush()
        
        prepared_chunks = self._prepare_chunks(chunks, chunk_size, overlap)
        
        if not prepared_chunks:
            db.commit()
            return {"indexed_chunks": 0, "document_id": doc_id}
        
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(prepared_chunks), batch_size):
            batch = prepared_chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            all_embeddings.extend(embeddings.tolist())
        
        for i, chunk in enumerate(prepared_chunks):
            db_chunk = DocumentChunk(
                document_id=doc_id,
                chunk_index=i,
                content=chunk["text"],
                page_number=chunk.get("page", 0),
                chunk_type=chunk.get("type", "text"),
                section_title=chunk.get("section", ""),
                embedding=all_embeddings[i],
            )
            db.add(db_chunk)
        
        db.commit()
        
        logger.info(f"Indexed {len(prepared_chunks)} chunks for document {doc_id}")
        
        return {
            "indexed_chunks": len(prepared_chunks),
            "document_id": doc_id,
            "message": f"Successfully indexed {len(prepared_chunks)} chunks"
        }
    
    def search(
        self,
        db: Session,
        doc_id: int,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search within a document using pgvector cosine distance.
        """
        query_embedding = self.embedding_model.encode([query])[0].tolist()
        
        results = db.execute(
            text("""
                SELECT id, content, page_number, chunk_type, section_title,
                       1 - (embedding <=> CAST(:query_embedding AS vector)) AS score
                FROM document_chunks
                WHERE document_id = :doc_id
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """),
            {
                "query_embedding": str(query_embedding),
                "doc_id": doc_id,
                "top_k": top_k,
            }
        ).fetchall()
        
        formatted_results = []
        for row in results:
            formatted_results.append({
                "chunk": row.content,
                "score": float(row.score) if row.score else 0.0,
                "page": row.page_number,
                "metadata": {
                    "chunk_type": row.chunk_type,
                    "section_title": row.section_title,
                },
                "context": self._get_context(row.content),
            })
        
        return formatted_results
    
    def delete_document_chunks(self, db: Session, doc_id: int) -> bool:
        """Delete all chunks for a document."""
        try:
            db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete chunks for doc {doc_id}: {e}")
            db.rollback()
            return False
    
    def _prepare_chunks(
        self,
        chunks: List[Dict[str, Any]],
        chunk_size: int,
        overlap: int
    ) -> List[Dict[str, Any]]:
        """Prepare and merge chunks with overlap."""
        if not chunks:
            return []
        
        prepared = []
        current_text = ""
        current_pages = []
        current_type = "text"
        current_section = ""
        
        for chunk in chunks:
            text_content = chunk.get("text", "")
            if not text_content.strip():
                continue
            
            if len(current_text) + len(text_content) > chunk_size and current_text:
                prepared.append({
                    "text": current_text.strip(),
                    "page": min(current_pages) if current_pages else 0,
                    "type": current_type,
                    "section": current_section,
                })

                if overlap > 0:
                    words = current_text.split()
                    overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else current_text
                    current_text = overlap_text + " " + text_content
                else:
                    current_text = text_content
                current_pages = [chunk.get("page", 0)]
            else:
                current_text += " " + text_content
                current_pages.append(chunk.get("page", 0))
            
            current_type = chunk.get("type", "text")
            if chunk.get("section"):
                current_section = chunk["section"]
        
        if current_text.strip():
            prepared.append({
                "text": current_text.strip(),
                "page": min(current_pages) if current_pages else 0,
                "type": current_type,
                "section": current_section,
            })
        
        return prepared
    
    def _get_context(self, chunk_text: str, window_size: int = 100) -> str:
        """Get surrounding context for a chunk."""
        if len(chunk_text) <= window_size * 2:
            return chunk_text
        start = chunk_text[:window_size]
        end = chunk_text[-window_size:]
        return f"{start}...{end}"
    
    def get_stats(self, db: Session, doc_id: int) -> Dict[str, Any]:
        """Get chunk statistics for a document."""
        count = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc_id
        ).count()
        
        return {
            "exists": count > 0,
            "count": count,
            "document_id": doc_id,
        }
