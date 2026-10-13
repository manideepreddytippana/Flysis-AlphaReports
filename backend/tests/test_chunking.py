import pytest
from app.pdf.chunker import FlysisHybridChunker


def test_chunker_initialization():
    """Test chunker lazy initialization and default token limit."""
    chunker = FlysisHybridChunker(max_tokens=250)
    assert chunker.max_tokens == 250
    assert "MiniLM" in chunker.model_name

    # Check pre_warm executes without error
    chunker.pre_warm()
    assert chunker._chunker is not None
