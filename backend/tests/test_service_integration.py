import json
from pathlib import Path
import pytest
from app.pdf.service import HybridPDFExtractionService
from app.api.utils import _ensure_extraction_cached
from app.api.deps import extraction_cache


def test_service_end_to_end_and_cache(sample_text_pdf, tmp_path):
    """
    Test full service execution:
    1. Extract document and verify canonical artifact write to pdf-information/.
    2. Verify disk caching logic in _ensure_extraction_cached.
    """
    service = HybridPDFExtractionService()
    doc_id = "test_integration_01"

    result = service.extract(sample_text_pdf, doc_id=doc_id)
    assert result.total_pages == 3

    # Check disk artifact
    info_file = Path("pdf-information") / f"{doc_id}_data.json"
    assert info_file.exists()

    with open(info_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "text_blocks" in data
    assert "tables" in data
    assert "chunks_advanced" in data
    assert "outline" in data
    assert "analyzer_report" in data

    # Clean in-memory cache to verify disk loading
    extraction_cache.pop(doc_id, None)

    class DummyDoc:
        filename = Path(sample_text_pdf).name

    import asyncio
    asyncio.run(_ensure_extraction_cached(doc_id, DummyDoc()))
    assert doc_id in extraction_cache
    assert len(extraction_cache[doc_id]["text_blocks"]) > 0


def test_service_extract_tables_only(sample_table_pdf):
    """Test extract_tables_only backward-compatibility helper."""
    service = HybridPDFExtractionService()
    tables = service.extract_tables_only(sample_table_pdf, doc_id="test_tables_only")
    assert isinstance(tables, list)
