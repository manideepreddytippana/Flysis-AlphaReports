import os
import sys
import tempfile
import pytest
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import fitz  # PyMuPDF


@pytest.fixture(scope="session")
def sample_text_pdf(tmp_path_factory):
    """Generates a synthetic single-column text PDF."""
    path = tmp_path_factory.mktemp("pdfs") / "sample_text.pdf"
    doc = fitz.open()
    for page_num in range(3):
        page = doc.new_page(width=595, height=842)
        text = (
            f"Section {page_num + 1}: Annual Executive Overview\n\n"
            "Flysis AlphaReports provides high-performance document intelligence. "
            "Our hybrid architecture dynamically switches between high-speed linear text "
            "processing and deep visual neural models based on document complexity.\n\n"
            "The fast track executes in sub-2-second latencies for typical digital prose documents, "
            "while the deep track leverages Docling and TableFormer to resolve intricate financial "
            "statements and multi-spanning cell grids with maximum accuracy.\n"
        )
        page.insert_text((50, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture(scope="session")
def sample_table_pdf(tmp_path_factory):
    """Generates a synthetic PDF containing explicit vector table lines."""
    path = tmp_path_factory.mktemp("pdfs") / "sample_table.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), "Financial Statement Overview", fontsize=14)

    # Draw table grid with lines (>= 4 lines)
    shape = page.new_shape()
    # Outer rectangle
    shape.draw_rect(fitz.Rect(50, 70, 500, 200))
    # Horizontal grid lines
    shape.draw_line(fitz.Point(50, 100), fitz.Point(500, 100))
    shape.draw_line(fitz.Point(50, 130), fitz.Point(500, 130))
    shape.draw_line(fitz.Point(50, 160), fitz.Point(500, 160))
    # Vertical grid lines
    shape.draw_line(fitz.Point(200, 70), fitz.Point(200, 200))
    shape.draw_line(fitz.Point(350, 70), fitz.Point(350, 200))
    shape.finish(color=(0, 0, 0), width=1)
    shape.commit()

    # Insert cell texts
    page.insert_text((55, 90), "Metric", fontsize=10)
    page.insert_text((205, 90), "2024 ($M)", fontsize=10)
    page.insert_text((355, 90), "2025 ($M)", fontsize=10)

    page.insert_text((55, 120), "Total Revenue", fontsize=10)
    page.insert_text((205, 120), "12,450", fontsize=10)
    page.insert_text((355, 120), "15,890", fontsize=10)

    page.insert_text((55, 150), "Gross Margin", fontsize=10)
    page.insert_text((205, 150), "4,200", fontsize=10)
    page.insert_text((355, 150), "5,610", fontsize=10)

    page.insert_text((55, 180), "Net Income", fontsize=10)
    page.insert_text((205, 180), "1,150", fontsize=10)
    page.insert_text((355, 180), "1,890", fontsize=10)

    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture(scope="session")
def real_upload_text_pdf():
    """Returns path to existing real 122-page text PDF in uploads if present."""
    p = Path(__file__).resolve().parent.parent / "uploads" / "01f62f21-bde8-4b75-8b2d-2571302feefa.pdf"
    if p.exists():
        return str(p)
    return None
