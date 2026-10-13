import time
import pytest
from app.pdf.fast_engine import FastPyMuPDFEngine
from app.pdf.legacy_compat import ExtractionResult


def test_fast_engine_extraction(sample_text_pdf):
    """Test FastPyMuPDFEngine extracts text blocks and chunks accurately and quickly."""
    engine = FastPyMuPDFEngine()

    start = time.time()
    result = engine.extract(sample_text_pdf, doc_id="test_fast_01")
    elapsed = time.time() - start

    assert isinstance(result, ExtractionResult)
    assert elapsed < 2.0  # Fast Track requirement: sub-2-second latency
    assert result.total_pages == 3
    assert len(result.text_blocks) > 0
    assert len(result.chunks_advanced) > 0

    # Validate TextBlock properties
    first_block = result.text_blocks[0]
    assert first_block.page == 1
    assert "Flysis" in first_block.text or "Section 1" in first_block.text

    # Validate AdvancedChunk properties
    first_chunk = result.chunks_advanced[0]
    assert first_chunk.chunk_id in (1, "1", "chunk_1")
    assert first_chunk.page_start == 1

    assert first_chunk.token_estimate > 0
    assert first_chunk.token_estimate <= 250  # Enforce 250-token window


def test_fast_engine_table_bypass(sample_text_pdf):
    """Test that extract_tables=False runs cleanly and sets tables to empty."""
    engine = FastPyMuPDFEngine()
    result = engine.extract(sample_text_pdf, doc_id="test_fast_no_tab", extract_tables=False)
    assert len(result.tables) == 0
