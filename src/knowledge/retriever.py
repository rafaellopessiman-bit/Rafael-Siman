import re
import sys
import time
from collections import defaultdict
from typing import Any

from src.exceptions import AtlasRetrieverError
from src.knowledge.catalog import CONCEPT_PATTERNS, STACK_PATTERNS, THEME_RULES
from src.knowledge.telemetry import TraceCollector
from src.storage.document_store import DocumentStore

RRF_K = 60
FTS_CANDIDATE_MULTIPLIER = 4
MAX_MATCHED_CHUNKS = 3
RELATED_QUERY_TERMS: dict[str, tuple[str, ...]] = {
    "clean architecture": ("clean_architecture", "architecture", "ddd", "cqrs", "event_sourcing"),
    "clean_architecture": ("clean architecture", "architecture", "ddd", "cqrs", "event_sourcing"),
    "ddd": ("domain driven design", "clean_architecture", "clean architecture", "cqrs", "event_sourcing"),
    "mongodb": ("atlas", "index", "indexes", "transaction", "transactions"),
    "transactions": ("transaction", "mongodb", "index", "indexes"),
    "transaction": ("transactions", "mongodb", "index", "indexes"),
    "embeddings": ("embedding", "vector_search", "vector search", "similarity search", "rag"),
    "embedding": ("embeddings", "vector_search", "vector search", "similarity search", "rag"),
    "vector_search": ("vector search", "similarity search", "embeddings", "rag"),
    "rag": ("retrieval augmented generation", "agents", "embeddings", "vector_search"),
    "agents": ("agent", "agentic", "multi-agent", "orchestration", "rag"),
    "performance": ("latency", "throughput", "profiling", "observability"),
}


def retrieve_documents(
    query: str,
    documents: list[dict[str, Any]],
    top_k: int,
    use_fts: bool = True,
    db_path: str | None = None,
    trace_collector: TraceCollector | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve documents using FTS5 (if available) or fallback to BM25 by tokens.

    Args:
        query: Search query string
        documents: List of documents (for BM25 fallback)
        top_k: Number of top results to return
        use_fts: If True and db_path available, use FTS5 (much faster)
        db_path: Explicit database path for FTS5 (overrides settings)
        trace_collector: Optional collector for ranking telemetry

    Returns:
        List of documents with relevance scores, sorted by score
    """
    if not query or not query.strip():
        raise AtlasRetrieverError("A consulta de busca está vazia.")

    if not documents:
        raise AtlasRetrieverError("A lista de documentos está vazia.")

    if top_k < 1:
        raise AtlasRetrieverError("TOP_K deve ser maior ou igual a 1.")

    expanded_query = _expand_query(query)
    candidate_limit = max(top_k * FTS_CANDIDATE_MULTIPLIER, top_k)
    fts_documents: list[dict[str, Any]] = []

    if trace_collector:
        trace_collector.start(query, expanded_query, top_k)

    # Try FTS5 first (faster, uses SQLite indexes)
    if use_fts:
        t0 = time.perf_counter()
        try:
            resolved_db_path = db_path
            if not resolved_db_path:
                from src.core.config import get_settings
                settings = get_settings()
                resolved_db_path = getattr(settings, "database_path", None)

            if resolved_db_path:
                store = DocumentStore(db_path=resolved_db_path)
                fts_query = _build_fts_query(expanded_query)

                if fts_query:
                    fts_results = store.search_chunks_by_text_fts(fts_query, limit=candidate_limit)
                    if fts_results:
                        fts_documents = _aggregate_fts_results(fts_results, documents)

                elapsed = time.perf_counter() - t0
                _log_retrieval("fts5", len(fts_documents), elapsed)
                if trace_collector:
                    trace_collector.record_fts(len(fts_documents), elapsed * 1000)
        except Exception as exc:
            _log_retrieval("fts5_error", 0, time.perf_counter() - t0, error=str(exc))

    # BM25 remains the second signal in the hybrid ranking.
    t0 = time.perf_counter()
    bm25_documents = _retrieve_by_bm25(expanded_query, documents, candidate_limit)
    elapsed = time.perf_counter() - t0
    _log_retrieval("bm25", len(bm25_documents), elapsed)
    if trace_collector:
        trace_collector.record_bm25(len(bm25_documents), elapsed * 1000)

    if fts_documents:
        query_terms = set(_tokenize(expanded_query))
        fused = _fuse_rankings(
            fts_documents, bm25_documents, top_k=top_k,
            query_terms=query_terms, trace_collector=trace_collector,
        )
        _log_retrieval("hybrid", len(fused), elapsed)
        return fused

    result = bm25_documents[:top_k]
    if trace_collector:
        trace_collector.finish_bm25_only(result)
    return result


def _log_retrieval(strategy: str, hits: int, elapsed: float, error: str = "") -> None:
    """Emit retrieval telemetry to stderr (non-blocking, debug-level)."""
    import os
    if not os.environ.get("ATLAS_DEBUG"):
        return
    msg = f"[retrieval] strategy={strategy} hits={hits} elapsed={elapsed:.3f}s"
    if error:
        msg += f" error={error!r}"
    print(msg, file=sys.stderr)


def _retrieve_by_bm25(
    query: str,
    documents: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Original BM25 retrieval algorithm (fallback)."""
    from rank_bm25 import BM25Okapi

    tokenized_query = _tokenize(query)
    if not tokenized_query:
        raise AtlasRetrieverError("A consulta não gerou tokens válidos para busca.")

    try:
        tokenized_corpus = []
        valid_documents = []

        for document in documents:
            content = str(document.get("content", "")).strip()
            if not content:
                continue

            tokens = _tokenize(content)
            if not tokens:
                continue

            tokenized_corpus.append(tokens)
            valid_documents.append(document)

        if not valid_documents:
            raise AtlasRetrieverError("Nenhum documento válido foi carregado para o BM25.")

        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(tokenized_query)

        # Lexical overlap boost for short queries (< 3 meaningful tokens)
        query_tokens_set = set(tokenized_query)
        use_overlap_boost = len(tokenized_query) < 3

        ranked_documents = []
        for document, score in zip(valid_documents, scores):
            final_score = float(score)
            if use_overlap_boost and final_score == 0.0:
                # Boost documents that contain at least one query token in path/name
                path_text = (
                    str(document.get("file_path", "")).lower()
                    + " "
                    + str(document.get("file_name", "")).lower()
                )
                if query_tokens_set & set(_tokenize(path_text)):
                    final_score = 0.1  # small non-zero boost to surface them
            ranked_documents.append(
                {
                    **document,
                    "score": final_score,
                }
            )

        ranked_documents.sort(key=lambda item: item["score"], reverse=True)

        # Fallback: if all scores are zero, return most-recent documents by list position
        if all(d["score"] == 0.0 for d in ranked_documents):
            return [{**d, "score": 0.0} for d in valid_documents[-top_k:]]

        return ranked_documents[:top_k]

    except AtlasRetrieverError:
        raise
    except Exception as exc:
        raise AtlasRetrieverError(f"Falha no retrieval BM25: {exc}") from exc


def _aggregate_fts_results(
    fts_results: list[dict[str, Any]],
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate chunk-level FTS hits into document-level results."""
    document_map = {
        str(document.get("file_path", "")): document
        for document in documents
        if str(document.get("file_path", ""))
    }
    aggregated: dict[str, dict[str, Any]] = {}

    for rank, result in enumerate(fts_results, start=1):
        file_path = str(result.get("file_path", ""))
        if not file_path:
            continue

        base_document = document_map.get(file_path, {})
        item = aggregated.get(file_path)
        if item is None:
            item = {
                **base_document,
                "file_path": file_path,
                "file_name": base_document.get("file_name") or file_path.split("\\")[-1].split("/")[-1],
                "content": base_document.get("content") or result.get("text", ""),
                "content_preview": result.get("content_preview", ""),
                "matched_chunks": [],
                "score": abs(float(result.get("score", 0))),
                "_fts_rank": rank,
            }
            aggregated[file_path] = item

        item["score"] = max(float(item.get("score", 0)), abs(float(result.get("score", 0))))
        item["_fts_rank"] = min(int(item.get("_fts_rank", rank)), rank)

        chunk_text = str(result.get("text", "")).strip()
        matched_chunks = item.setdefault("matched_chunks", [])
        if chunk_text and chunk_text not in matched_chunks and len(matched_chunks) < MAX_MATCHED_CHUNKS:
            matched_chunks.append(chunk_text)

        if not item.get("content_preview"):
            item["content_preview"] = result.get("content_preview", "")

    documents_ranked = list(aggregated.values())
    documents_ranked.sort(
        key=lambda item: (int(item.get("_fts_rank", sys.maxsize)), -float(item.get("score", 0))),
    )
    return documents_ranked


def _fuse_rankings(
    fts_documents: list[dict[str, Any]],
    bm25_documents: list[dict[str, Any]],
    top_k: int,
    query_terms: set[str] | None = None,
    trace_collector: TraceCollector | None = None,
) -> list[dict[str, Any]]:
    """Fuse FTS and BM25 results using Reciprocal Rank Fusion."""
    fused: dict[str, dict[str, Any]] = {}
    raw_scores: defaultdict[str, dict[str, float]] = defaultdict(dict)

    for strategy, docs in (("fts", fts_documents), ("bm25", bm25_documents)):
        for rank, document in enumerate(docs, start=1):
            file_path = str(document.get("file_path", ""))
            if not file_path:
                continue

            entry = fused.get(file_path)
            if entry is None:
                entry = {
                    **document,
                    "matched_chunks": list(document.get("matched_chunks") or []),
                    "_rrf_score": 0.0,
                }
                fused[file_path] = entry

            entry["_rrf_score"] += 1.0 / (RRF_K + rank)
            raw_scores[file_path][strategy] = float(document.get("score", 0.0))

            if strategy == "fts":
                entry["content_preview"] = document.get("content_preview") or entry.get("content_preview", "")
                entry["matched_chunks"] = _merge_unique_texts(
                    entry.get("matched_chunks"),
                    document.get("matched_chunks"),
                    limit=MAX_MATCHED_CHUNKS,
                )

    # Weight for blending FTS and BM25 raw scores.
    # FTS (chunk-level BM25) is more precise; corpus-level BM25 biases toward
    # longer documents, so we down-weight it.
    FTS_WEIGHT = 1.0
    BM25_WEIGHT = 0.4

    rrf_scores: dict[str, float] = {}
    metadata_bonuses: dict[str, float] = {}
    metadata_overlap: dict[str, list[str]] = {}

    results: list[dict[str, Any]] = []
    for file_path, entry in fused.items():
        fts_score = raw_scores[file_path].get("fts", 0.0)
        bm25_score = raw_scores[file_path].get("bm25", 0.0)
        blended = fts_score * FTS_WEIGHT + bm25_score * BM25_WEIGHT
        rrf_val = float(entry.get("_rrf_score", 0.0))
        meta_bonus = _metadata_overlap_bonus(entry, query_terms or set())
        entry["score"] = blended + rrf_val + meta_bonus

        rrf_scores[file_path] = rrf_val
        metadata_bonuses[file_path] = meta_bonus
        if trace_collector:
            metadata_overlap[file_path] = _metadata_overlap_detail(entry, query_terms or set())

        entry.pop("_rrf_score", None)
        entry.pop("_fts_rank", None)
        results.append(entry)

    results.sort(key=lambda item: (-float(item.get("score", 0.0)), str(item.get("file_path", ""))))
    top_results = results[:top_k]

    if trace_collector:
        trace_collector.record_fusion(
            strategy="hybrid",
            fused_count=len(top_results),
            ranked_docs=top_results,
            raw_scores=dict(raw_scores),
            rrf_scores=rrf_scores,
            metadata_bonuses=metadata_bonuses,
            metadata_overlap_terms=metadata_overlap,
        )

    return top_results


METADATA_BONUS_WEIGHT = 1.5


def _metadata_overlap_detail(document: dict[str, Any], query_terms: set[str]) -> list[str]:
    """Return the actual query terms that matched document metadata."""
    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    if not metadata or not query_terms:
        return []

    lowered_terms = {t.casefold() for t in query_terms}
    meta_terms: set[str] = set()

    theme = str(metadata.get("theme", "")).casefold()
    if theme:
        meta_terms.add(theme)
        meta_terms.update(theme.replace("_", " ").split())
        for rule_theme, rule_keywords in THEME_RULES:
            if rule_theme == theme:
                meta_terms.update(kw.casefold() for kw in rule_keywords)
                break

    stack = metadata.get("stack", [])
    if isinstance(stack, list):
        for s in stack:
            if isinstance(s, str):
                meta_terms.add(s.casefold())

    concepts = metadata.get("concepts", [])
    if isinstance(concepts, list):
        for c in concepts:
            if isinstance(c, str):
                meta_terms.add(c.casefold())
                meta_terms.update(c.casefold().replace("_", " ").split())

    return sorted(lowered_terms & meta_terms)


def _metadata_overlap_bonus(document: dict[str, Any], query_terms: set[str]) -> float:
    """Score bonus proportional to overlap ratio between query terms and document metadata.

    Uses a ratio-based approach: bonus = (overlap_count / query_size) * METADATA_BONUS_WEIGHT.
    This keeps bonuses small enough to act as tiebreakers without reshuffling documents
    that differ significantly in raw FTS/BM25 scores.
    """
    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    if not metadata or not query_terms:
        return 0.0

    lowered_terms = {t.casefold() for t in query_terms}
    meta_terms: set[str] = set()

    # Collect theme keywords (including THEME_RULES expansion)
    theme = str(metadata.get("theme", "")).casefold()
    if theme:
        meta_terms.add(theme)
        meta_terms.update(theme.replace("_", " ").split())
        for rule_theme, rule_keywords in THEME_RULES:
            if rule_theme == theme:
                meta_terms.update(kw.casefold() for kw in rule_keywords)
                break

    # Collect stack values
    stack = metadata.get("stack", [])
    if isinstance(stack, list):
        for s in stack:
            if isinstance(s, str):
                meta_terms.add(s.casefold())

    # Collect concept values (with underscore expansion)
    concepts = metadata.get("concepts", [])
    if isinstance(concepts, list):
        for c in concepts:
            if isinstance(c, str):
                meta_terms.add(c.casefold())
                meta_terms.update(c.casefold().replace("_", " ").split())

    overlap_count = len(lowered_terms & meta_terms)
    if overlap_count == 0:
        return 0.0

    ratio = overlap_count / max(len(lowered_terms), 1)
    return ratio * METADATA_BONUS_WEIGHT


def _merge_unique_texts(left: Any, right: Any, limit: int) -> list[str]:
    merged: list[str] = []
    for items in (left or [], right or []):
        for item in items:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
            if len(merged) >= limit:
                return merged
    return merged


def _expand_query(query: str) -> str:
    normalized_query = query.strip()
    normalized_text = normalized_query.casefold()
    expanded_terms: list[str] = [normalized_query]

    for label, pattern in CONCEPT_PATTERNS:
        if re.search(pattern, normalized_text, flags=re.IGNORECASE):
            _append_term(expanded_terms, label)
            _append_term(expanded_terms, label.replace("_", " "))

    for label, pattern in STACK_PATTERNS:
        if re.search(pattern, normalized_text, flags=re.IGNORECASE):
            _append_term(expanded_terms, label)

    for trigger, related_terms in RELATED_QUERY_TERMS.items():
        if trigger in normalized_text:
            _append_term(expanded_terms, trigger)
            for term in related_terms:
                _append_term(expanded_terms, term)

    return " ".join(expanded_terms)


def _append_term(terms: list[str], term: str) -> None:
    cleaned = str(term).strip()
    if cleaned and cleaned not in terms:
        terms.append(cleaned)


def _build_fts_query(query: str) -> str:
    tokens = list(dict.fromkeys(_tokenize(query)))
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"' for token in tokens)


def _tokenize(text: str) -> list[str]:
    normalized_text = text.lower()
    return re.findall(r"\w+", normalized_text, flags=re.UNICODE)
