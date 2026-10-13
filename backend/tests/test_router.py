import time
import pytest
from app.pdf.router import DocumentProfiler, ExtractionRouter
from app.pdf.config import RouterConfig


def test_router_text_document(sample_text_pdf):
    """Test profiler identifies standard digital text document and selects fast route."""
    config = RouterConfig()
    profiler = DocumentProfiler(config)

    start = time.time()
    profile = profiler.profile(sample_text_pdf)
    elapsed_ms = (time.time() - start) * 1000

    assert elapsed_ms < 500  # Sub-second inspection
    assert profile.is_scanned is False
    assert profile.total_pages == 3
    assert profile.recommended_route == "fast"
    assert "Fast Track" in profile.routing_reason


def test_router_table_document(sample_table_pdf):
    """Test profiler detects vector table lines and routes to docling."""
    config = RouterConfig(min_table_lines=3)
    profiler = DocumentProfiler(config)

    profile = profiler.profile(sample_table_pdf)
    assert profile.has_tables is True
    assert profile.recommended_route == "docling"
    assert "tables" in profile.routing_reason.lower()


def test_extraction_router_forced_routing(sample_text_pdf):
    """Test ExtractionRouter respects forced route parameter."""
    router = ExtractionRouter()
    
    # Normally fast
    route, profile = router.route(sample_text_pdf)
    assert route == "fast"

    # Forced docling
    forced_route, forced_profile = router.route(sample_text_pdf, force_route="docling")
    assert forced_route == "docling"
