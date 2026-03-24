import re
import sys
import time
from typing import Any

from src.exceptions import AtlasRetrieverError
from src.storage.document_store import DocumentStore


def retrieve_documents(
    query: str,
    documents: list[dict[str, Any]],
    top_k: int,
    use_fts: bool = True,
) -> list[dict[str, Any]]:
    """
    Retrieve documents using FTS5 (if available) or fallback to BM25 by tokens.

    Args:
        query: Search query string
        documents: List of documents (for BM25 fallback)
        top_k: Number of top results to return
        use_fts: If True and db_path available, use FTS5 (much faster)

    Returns:
        List of documents with relevance scores, sorted by score
    """
    if not query or not query.strip():
        raise AtlasRetrieverError("A consulta de busca está vazia.")

    if not documents:
        raise AtlasRetrieverError("A lista de documentos está vazia.")

    if top_k < 1:
        raise AtlasRetrieverError("TOP_K deve ser maior ou igual a 1.")

    # Try FTS5 first (faster, uses SQLite indexes)
    if use_fts:
        t0 = time.perf_counter()
        try:
            from src.core.config import get_settings
            settings = get_settings()
            db_path = getattr(settings, "database_path", None)

            if db_path:
                store = DocumentStore(db_path=db_path)
                fts_results = store.search_chunks_by_text_fts(query, limit=top_k)

                if fts_results:
                    elapsed = time.perf_counter() - t0
                    _log_retrieval("fts5", len(fts_results), elapsed)
                    return _fts_results_to_documents(fts_results)
        except Exception as exc:
            _log_retrieval("fts5_error", 0, time.perf_counter() - t0, error=str(exc))

    # Fallback: BM25
    t0 = time.perf_counter()
    result = _retrieve_by_bm25(query, documents, top_k)
    elapsed = time.perf_counter() - t0
    _log_retrieval("bm25", len(result), elapsed)
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


def _fts_results_to_documents(fts_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert FTS search results to document format."""
    documents = []
    for result in fts_results:
        documents.append(
            {
                "id": result.get("id"),
                "file_path": result.get("file_path"),
                "file_name": result.get("file_path", "").split("\\")[-1].split("/")[-1],
                "content": result.get("text", ""),
                "content_preview": result.get("content_preview", ""),
                "score": abs(result.get("score", 0)),  # FTS rank is negative, convert to positive
            }
        )
    return documents


def _tokenize(text: str) -> list[str]:
    normalized_text = text.lower()
    return re.findall(r"\w+", normalized_text, flags=re.UNICODE)
