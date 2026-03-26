"""Corpus quality filters applied at indexing and retrieval time.

Provides:
- Chunk-level quality scoring (drops noise, TOC, boilerplate)
- Near-duplicate document detection via content hashing
- Chunk deduplication within a document
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

# ── Chunk quality thresholds ────────────────────────────
MIN_CHUNK_CHARS = 60
MIN_ALPHA_RATIO = 0.30          # at least 30% alphabetic chars
MAX_NUMERIC_RATIO = 0.60        # reject if >60% digits (page numbers, tables of numbers)
MIN_UNIQUE_WORDS = 5            # reject if fewer unique words

# Patterns that indicate boilerplate / non-informative chunks
_BOILERPLATE_RE = re.compile(
    r"^(table\s+of\s+contents"
    r"|tabela\s+de\s+conte[uú]do"
    r"|summ?[aá]rio"
    r"|index|[ií]ndice"
    r"|copyright|all\s+rights?\s+reserved"
    r"|isbn[:\s]"
    r"|page\s+\d+\s+of\s+\d+"
    r"|p[aá]gina\s+\d+)",
    re.IGNORECASE,
)


@dataclass
class ChunkQualityResult:
    """Result of evaluating a single chunk."""
    accepted: bool
    reason: str = ""


def evaluate_chunk_quality(text: str) -> ChunkQualityResult:
    """Score a chunk and decide whether to keep it.

    Returns ChunkQualityResult with accepted=True if the chunk
    should be indexed, or accepted=False with a reason otherwise.
    """
    stripped = text.strip()

    if len(stripped) < MIN_CHUNK_CHARS:
        return ChunkQualityResult(False, "too_short")

    alpha_count = sum(1 for c in stripped if c.isalpha())
    total = len(stripped)
    if total > 0 and (alpha_count / total) < MIN_ALPHA_RATIO:
        return ChunkQualityResult(False, "low_alpha_ratio")

    digit_count = sum(1 for c in stripped if c.isdigit())
    if total > 0 and (digit_count / total) > MAX_NUMERIC_RATIO:
        return ChunkQualityResult(False, "high_numeric_ratio")

    words = stripped.split()
    unique_words = set(w.lower() for w in words)
    if len(unique_words) < MIN_UNIQUE_WORDS:
        return ChunkQualityResult(False, "low_vocabulary")

    # Check first 200 chars for boilerplate patterns
    if _BOILERPLATE_RE.search(stripped[:200]):
        return ChunkQualityResult(False, "boilerplate")

    return ChunkQualityResult(True)


def filter_chunks(chunks: list[str]) -> tuple[list[str], int]:
    """Filter a list of chunks, returning (accepted_chunks, dropped_count)."""
    accepted: list[str] = []
    dropped = 0
    for chunk in chunks:
        result = evaluate_chunk_quality(chunk)
        if result.accepted:
            accepted.append(chunk)
        else:
            dropped += 1
    return accepted, dropped


# ── Document deduplication ──────────────────────────────

def content_fingerprint(content: str) -> str:
    """Compute a normalized fingerprint for near-duplicate detection.

    Normalizes whitespace and lowercases before hashing, so that
    documents with minor formatting differences are considered equivalent.
    """
    normalized = re.sub(r"\s+", " ", content.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class DuplicateReport:
    """Report of duplicate detection across a set of documents."""
    unique_documents: list[dict[str, Any]] = field(default_factory=list)
    duplicates: list[dict[str, Any]] = field(default_factory=list)


def detect_duplicates(documents: list[dict[str, Any]]) -> DuplicateReport:
    """Detect near-duplicate documents based on content fingerprint.

    Returns a DuplicateReport with unique docs and the discarded duplicates.
    Documents are compared by normalized content hash. When duplicates exist,
    the first occurrence (by file_path order) is kept.
    """
    seen: dict[str, str] = {}  # fingerprint -> file_path of first occurrence
    report = DuplicateReport()

    sorted_docs = sorted(documents, key=lambda d: str(d.get("file_path", "")))

    for doc in sorted_docs:
        content = doc.get("content", "")
        fp = content_fingerprint(content)
        file_path = str(doc.get("file_path", ""))

        if fp in seen:
            report.duplicates.append({
                **doc,
                "_duplicate_of": seen[fp],
                "_fingerprint": fp,
            })
        else:
            seen[fp] = file_path
            report.unique_documents.append(doc)

    return report


# ── Chunk deduplication within a document ───────────────

def deduplicate_chunks(chunks: list[str]) -> tuple[list[str], int]:
    """Remove exact-duplicate chunks within a document, preserving order.

    Returns (unique_chunks, removed_count).
    """
    seen: set[str] = set()
    unique: list[str] = []
    removed = 0

    for chunk in chunks:
        normalized = chunk.strip()
        if normalized in seen:
            removed += 1
            continue
        seen.add(normalized)
        unique.append(chunk)

    return unique, removed
