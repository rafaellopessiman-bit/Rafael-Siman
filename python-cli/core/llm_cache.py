"""
LLM Response Cache - in-memory LRU cache and optional persistent SQLite cache.

In-memory (default):
  - Ultra-fast (dict lookup)
  - Lost on process exit
  - Controlled by LLM_CACHE_ENABLED / LLM_CACHE_MAX_SIZE

Persistent (opt-in via LLM_CACHE_PERSISTENT=true):
  - Survives process restarts -- hot starts are always fast
  - Thread-safe and multi-process safe (WAL mode)
  - Optional TTL via LLM_CACHE_TTL_SECONDS
  - Stored at LLM_CACHE_PATH (default: data/llm_cache.db)
"""

import hashlib
import sqlite3
import threading
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass(frozen=True)
class CacheEntry:
    """Immutable cache entry with metadata."""
    response: str
    timestamp: str
    prompt_hash: str


# ---------------------------------------------------------------------------
# In-memory LRU cache (original, default)
# ---------------------------------------------------------------------------

class LLMResponseCache:
    """In-memory LRU cache for LLM responses."""

    def __init__(self, enabled: bool = True, max_size: int = 1000):
        self.enabled = enabled
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, prompt: str) -> Optional[str]:
        """Get cached response for prompt. Returns None if not cached."""
        if not self.enabled:
            return None
        key = _hash_prompt(prompt)
        if key in self._cache:
            self._hits += 1
            return self._cache[key].response
        self._misses += 1
        return None

    def put(self, prompt: str, response: str) -> None:
        """Store response in cache."""
        if not self.enabled:
            return
        key = _hash_prompt(prompt)
        if len(self._cache) >= self.max_size:
            remove_count = max(1, self.max_size // 10)
            for old_key in list(self._cache.keys())[:remove_count]:
                del self._cache[old_key]
        self._cache[key] = CacheEntry(
            response=response,
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            prompt_hash=key,
        )

    def clear(self) -> None:
        """Clear all cached responses."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        """Return cache statistics."""
        total_calls = self._hits + self._misses
        hit_rate = (self._hits / total_calls * 100) if total_calls > 0 else 0.0
        return {
            "type": "memory",
            "enabled": self.enabled,
            "entries": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Hash a prompt string (delegates to module-level helper)."""
        return _hash_prompt(prompt)


# ---------------------------------------------------------------------------
# Persistent SQLite cache (opt-in)
# ---------------------------------------------------------------------------

class PersistentLLMCache:
    """
    SQLite-backed LLM response cache. Survives process restarts.

    Activated when LLM_CACHE_PERSISTENT=true in .env.
    Storage path: LLM_CACHE_PATH (default: data/llm_cache.db)
    Optional TTL: LLM_CACHE_TTL_SECONDS (default: no expiry)
    """

    _DDL = """
        CREATE TABLE IF NOT EXISTS responses (
            prompt_hash   TEXT PRIMARY KEY,
            prompt_prefix TEXT,
            response      TEXT NOT NULL,
            model         TEXT,
            created_at    TEXT NOT NULL,
            access_count  INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_responses_created_at
            ON responses(created_at);
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
    """

    def __init__(
        self,
        db_path: "str | Path" = "data/llm_cache.db",
        enabled: bool = True,
        ttl_seconds: Optional[int] = None,
        model: str = "",
    ) -> None:
        self.db_path = Path(db_path)
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.model = model
        self._hits = 0
        self._misses = 0
        if self.enabled:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(self._DDL)

    def get(self, prompt: str) -> Optional[str]:
        if not self.enabled:
            return None
        key = _hash_prompt(prompt)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT response, created_at FROM responses WHERE prompt_hash = ?",
                (key,),
            ).fetchone()
        if row is None:
            self._misses += 1
            return None
        if self.ttl_seconds is not None:
            age_s = (datetime.now(UTC) - datetime.fromisoformat(row["created_at"])).total_seconds()
            if age_s > self.ttl_seconds:
                self._evict(key)
                self._misses += 1
                return None
        self._hits += 1
        with self._connect() as conn:
            conn.execute(
                "UPDATE responses SET access_count = access_count + 1 WHERE prompt_hash = ?",
                (key,),
            )
        return row["response"]

    def put(self, prompt: str, response: str) -> None:
        if not self.enabled:
            return
        key = _hash_prompt(prompt)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO responses (prompt_hash, prompt_prefix, response, model, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(prompt_hash) DO UPDATE SET
                    response = excluded.response,
                    model = excluded.model,
                    created_at = excluded.created_at,
                    access_count = access_count + 1
                """,
                (key, prompt[:120], response, self.model, datetime.now(UTC).isoformat(timespec="seconds")),
            )

    def clear(self) -> None:
        self._hits = 0
        self._misses = 0
        if not self.enabled:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM responses")

    def cleanup(self, max_age_days: int = 30) -> int:
        """Remove entries older than max_age_days. Returns count removed."""
        if not self.enabled:
            return 0
        import datetime as dt
        cutoff = (datetime.now(UTC) - dt.timedelta(days=max_age_days)).isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM responses WHERE created_at < ?", (cutoff,))
            return cur.rowcount

    def stats(self) -> dict:
        total_calls = self._hits + self._misses
        hit_rate = (self._hits / total_calls * 100) if total_calls > 0 else 0.0
        count = 0
        if self.enabled:
            with self._connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        return {
            "type": "persistent",
            "enabled": self.enabled,
            "entries": count,
            "db_path": str(self.db_path),
            "ttl_seconds": self.ttl_seconds,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _evict(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM responses WHERE prompt_hash = ?", (key,))


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Singleton management (thread-safe)
# ---------------------------------------------------------------------------

_default_cache: Optional[LLMResponseCache | PersistentLLMCache] = None
_cache_lock = threading.Lock()


def get_cache(
    enabled: Optional[bool] = None,
    max_size: Optional[int] = None,
) -> LLMResponseCache | PersistentLLMCache:
    """Get or create the default cache instance (thread-safe, double-checked locking)."""
    global _default_cache

    if _default_cache is None:
        with _cache_lock:
            if _default_cache is None:
                from src.core.config import get_settings
                settings = get_settings()

                cache_enabled = getattr(settings, "llm_cache_enabled", True)
                cache_max_size = getattr(settings, "llm_cache_max_size", 1000)
                cache_persistent = getattr(settings, "llm_cache_persistent", False)
                cache_path = getattr(settings, "llm_cache_path", "data/llm_cache.db")
                cache_ttl = getattr(settings, "llm_cache_ttl_seconds", None)
                groq_model = getattr(settings, "groq_model", "")

                if enabled is not None:
                    cache_enabled = enabled
                if max_size is not None:
                    cache_max_size = max_size

                if cache_persistent:
                    _default_cache = PersistentLLMCache(
                        db_path=cache_path,
                        enabled=cache_enabled,
                        ttl_seconds=cache_ttl,
                        model=groq_model,
                    )
                else:
                    _default_cache = LLMResponseCache(
                        enabled=cache_enabled,
                        max_size=cache_max_size,
                    )

    return _default_cache


def reset_cache() -> None:
    """Reset the global cache instance (for testing)."""
    global _default_cache
    with _cache_lock:
        _default_cache = None
