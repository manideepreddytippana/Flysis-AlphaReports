import pytest
from unittest.mock import patch
from app.pdf.service import HybridPDFExtractionService
from app.pdf.legacy_compat import ExtractionResult


def test_circuit_breaker_fallback(sample_text_pdf):
    """
    Simulate a Docling neural model failure (e.g. out of memory, C++ crash, conversion error).
    Verify that HybridPDFExtractionService activates the Fail-Safe Circuit Breaker
    and completes extraction using FastPyMuPDFEngine without crashing.
    """
    service = HybridPDFExtractionService()

    # Force route to 'docling' but mock docling_engine.extract to raise RuntimeError
    with patch.object(service.docling_engine, "extract", side_effect=RuntimeError("Simulated neural model crash")):
        result = service.extract(
            file_path=sample_text_pdf,
            doc_id="test_cb_doc",
            force_route="docling"
        )

    assert isinstance(result, ExtractionResult)
    assert result.total_pages == 3
    assert len(result.text_blocks) > 0
    assert "circuit_breaker_fallback_fast" in result.methods_used
