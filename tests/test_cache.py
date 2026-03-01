"""Tests for cache module."""

import pytest
from pathlib import Path
from outlook_ai.cache import EmailCache


def test_cache_init(tmp_path):
    """Test cache initialization."""
    db_path = tmp_path / "test.db"
    cache = EmailCache(db_path=str(db_path))
    
    assert db_path.exists()


def test_cache_clear(tmp_path):
    """Test cache clear."""
    db_path = tmp_path / "test.db"
    cache = EmailCache(db_path=str(db_path))
    
    cache.clear_cache()
