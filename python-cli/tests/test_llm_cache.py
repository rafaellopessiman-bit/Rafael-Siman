"""
Tests for LLM Response Cache
"""
import hashlib

import pytest

from src.core.llm_cache import LLMResponseCache, PersistentLLMCache, get_cache, reset_cache


def test_llm_response_cache_stores_and_retrieves():
    """Test basic cache store and retrieve."""
    cache = LLMResponseCache(enabled=True, max_size=10)
    
    prompt = "Como você pode ajudar?"
    response = "Posso ajudar com muitas coisas!"
    
    # First retrieve is None (miss)
    assert cache.get(prompt) is None
    
    # Store response
    cache.put(prompt, response)
    
    # Second retrieve gets the cached response (hit)
    assert cache.get(prompt) == response


def test_llm_response_cache_disabling():
    """Test cache behavior when disabled."""
    cache = LLMResponseCache(enabled=False, max_size=10)
    
    prompt = "Test prompt"
    response = "Test response"
    
    # Even after storing, returns None when disabled
    cache.put(prompt, response)
    assert cache.get(prompt) is None


def test_llm_response_cache_tracks_stats():
    """Test cache statistics."""
    cache = LLMResponseCache(enabled=True, max_size=10)
    
    prompt = "Test"
    response = "Response"
    cache.put(prompt, response)
    
    # First hit
    cache.get(prompt)
    # Second miss
    cache.get("different prompt")
    
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["entries"] == 1
    assert stats["hit_rate_percent"] == 50.0


def test_llm_response_cache_max_size():
    """Test cache respects max size limit."""
    cache = LLMResponseCache(enabled=True, max_size=3)
    
    # Add 5 entries to cache with max size 3
    for i in range(5):
        cache.put(f"prompt_{i}", f"response_{i}")
    
    # Cache should not exceed max_size (removes 10%)
    assert len(cache._cache) <= 3


def test_llm_response_cache_hash_consistency():
    """Test that same prompt produces same hash."""
    cache = LLMResponseCache(enabled=True, max_size=10)
    
    prompt = "Test prompt with some content"
    hash1 = cache._hash_prompt(prompt)
    hash2 = cache._hash_prompt(prompt)
    
    assert hash1 == hash2


def test_llm_response_cache_clears():
    """Test cache.clear() resets everything."""
    cache = LLMResponseCache(enabled=True, max_size=10)
    
    cache.put("prompt", "response")
    cache.get("prompt")
    
    cache.clear()
    
    assert len(cache._cache) == 0
    assert cache._hits == 0
    assert cache._misses == 0


def test_global_cache_singleton():
    """Test global cache singleton behavior."""
    reset_cache()
    
    cache1 = get_cache()
    cache1.put("test", "response")
    
    cache2 = get_cache()
    
    # Both should reference same cache
    assert cache2.get("test") == "response"


def test_cache_disabled_via_config():
    """Test cache respects enabled flag."""
    cache = LLMResponseCache(enabled=False)
    cache.put("prompt", "response")
    
    # Should return None even after storing (disabled)
    assert cache.get("prompt") is None


def test_persistent_cache_stores_and_retrieves(tmp_path):
    """Persistent cache should store and retrieve entries from SQLite."""
    db_path = tmp_path / "llm_cache.db"
    cache = PersistentLLMCache(db_path=db_path, enabled=True)

    prompt = "prompt persistente"
    response = "resposta persistente"

    assert cache.get(prompt) is None
    cache.put(prompt, response)
    assert cache.get(prompt) == response


def test_persistent_cache_persists_between_instances(tmp_path):
    """Data should survive new cache instance creation."""
    db_path = tmp_path / "llm_cache.db"

    cache1 = PersistentLLMCache(db_path=db_path, enabled=True)
    cache1.put("prompt", "resposta")

    cache2 = PersistentLLMCache(db_path=db_path, enabled=True)
    assert cache2.get("prompt") == "resposta"


def test_persistent_cache_ttl_expires_entry(tmp_path):
    """Entry should expire when TTL has passed."""
    db_path = tmp_path / "llm_cache.db"
    cache = PersistentLLMCache(db_path=db_path, enabled=True, ttl_seconds=0)

    cache.put("prompt ttl", "resposta ttl")
    assert cache.get("prompt ttl") is None


def test_persistent_cache_cleanup_removes_old_entries(tmp_path):
    """cleanup should remove entries older than threshold."""
    db_path = tmp_path / "llm_cache.db"
    cache = PersistentLLMCache(db_path=db_path, enabled=True)
    prompt = "prompt antigo"
    cache.put(prompt, "resposta antiga")

    # Force old timestamp to guarantee cleanup match.
    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    with cache._connect() as conn:
        conn.execute(
            "UPDATE responses SET created_at = ? WHERE prompt_hash = ?",
            ("2000-01-01T00:00:00+00:00", key),
        )

    removed = cache.cleanup(max_age_days=0)

    assert removed >= 1
    assert cache.get(prompt) is None
