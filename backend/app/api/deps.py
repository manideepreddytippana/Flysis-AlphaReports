from app.pdf.service import HybridPDFExtractionService
from app.vector.pgvector_store import PgVectorStore
from app.llm.sarvam_client import SarvamAIClient, RAGPipeline
from app.core.config import get_settings

settings = get_settings()

pdf_pipeline = HybridPDFExtractionService()
vector_store = PgVectorStore()
llm_client = SarvamAIClient()
rag_pipeline = RAGPipeline(vector_store, llm_client)

extraction_cache: dict = {}

