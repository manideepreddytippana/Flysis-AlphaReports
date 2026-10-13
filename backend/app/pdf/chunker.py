import logging
from typing import List, Optional
from transformers import AutoTokenizer
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc.document import DoclingDocument

from app.pdf.legacy_compat import AdvancedChunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FlysisHybridChunker:

    def __init__(self, max_tokens: Optional[int] = None):
        settings = get_settings()
        self.max_tokens = max_tokens or getattr(settings, "docling_max_tokens", 250)
        self.model_name = getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        self._chunker: Optional[HybridChunker] = None

    def _get_chunker(self) -> HybridChunker:
        if self._chunker is None:
            logger.info(f"Initializing HybridChunker with tokenizer for {self.model_name}...")
            hf_model_path = (
                f"sentence-transformers/{self.model_name}"
                if not self.model_name.startswith("sentence-transformers/")
                and not "/" in self.model_name
                else self.model_name
            )
            hf_tokenizer = AutoTokenizer.from_pretrained(hf_model_path)
            docling_tokenizer = HuggingFaceTokenizer(tokenizer=hf_tokenizer)
            self._chunker = HybridChunker(
                tokenizer=docling_tokenizer,
                max_tokens=self.max_tokens,
                merge_peers=True,
            )
            logger.info("FlysisHybridChunker initialized successfully.")
        return self._chunker

    def pre_warm(self) -> None:
        try:
            logger.info(f"Pre-warming HybridChunker tokenizer for {self.model_name}...")
            _ = self._get_chunker()
            logger.info("HybridChunker tokenizer pre-warmed successfully.")
        except Exception as e:
            logger.warning(f"HybridChunker pre-warming encountered an issue (will load on demand): {e}")

    def chunk_docling_document(self, doc: DoclingDocument) -> List[AdvancedChunk]:

        chunker = self._get_chunker()
        raw_chunks = chunker.chunk(doc)
        advanced_chunks: List[AdvancedChunk] = []

        for idx, chunk in enumerate(raw_chunks, start=1):
            try:
                contextualized_text = chunker.contextualize(chunk)
            except Exception as e:
                logger.debug(f"Contextualize failed for chunk {idx}: {e}")
                contextualized_text = chunk.text

            pages = set()
            if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items"):
                for item in chunk.meta.doc_items:
                    if hasattr(item, "prov") and item.prov:
                        for prov in item.prov:
                            if hasattr(prov, "page_no"):
                                pages.add(prov.page_no)

            page_start = min(pages) if pages else 1
            page_end = max(pages) if pages else page_start

            heading_path = []
            if hasattr(chunk, "meta") and hasattr(chunk.meta, "headings") and chunk.meta.headings:
                heading_path = [str(h) for h in chunk.meta.headings if h]

            token_estimate = len(contextualized_text.split())

            is_table = False
            if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items"):
                for item in chunk.meta.doc_items:
                    item_str = str(type(item)).lower()
                    label_str = str(getattr(item, "label", "")).lower()
                    if "table" in item_str or "table" in label_str:
                        is_table = True
                        break
            if not is_table and ("\n| " in contextualized_text or contextualized_text.startswith("| ")):
                is_table = True

            c_type = "table" if is_table else "text"

            advanced_chunks.append(
                AdvancedChunk(
                    chunk_id=idx,
                    text=contextualized_text,
                    page_start=page_start,
                    page_end=page_end,
                    heading_path=heading_path,
                    chunk_type=c_type,
                    token_estimate=token_estimate,
                    boundary_reason="hybrid_structure",
                )
            )

        logger.info(f"[FlysisHybridChunker] Generated {len(advanced_chunks)} structure-aware chunks.")
        return advanced_chunks
