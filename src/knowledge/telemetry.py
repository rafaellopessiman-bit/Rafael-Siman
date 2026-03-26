"""Structured retrieval telemetry for ranking diagnostics.

Captures per-document score breakdowns so that ranking changes
can be diagnosed without guesswork.  Activated by --debug flag
or ATLAS_DEBUG=1 environment variable.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DocumentTrace:
    """Score breakdown for a single ranked document."""

    file_path: str
    rank: int
    final_score: float
    fts_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    metadata_bonus: float = 0.0
    blended_score: float = 0.0
    matched_chunks_count: int = 0
    metadata_overlap_terms: list[str] = field(default_factory=list)


@dataclass
class RetrievalTrace:
    """Full trace of a single retrieval operation."""

    query_original: str
    query_expanded: str
    strategy: str  # "hybrid", "bm25_only", "fts_only"
    top_k: int
    fts_candidates: int = 0
    bm25_candidates: int = 0
    fused_count: int = 0
    elapsed_fts_ms: float = 0.0
    elapsed_bm25_ms: float = 0.0
    elapsed_total_ms: float = 0.0
    documents: list[DocumentTrace] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def format_trace_compact(trace: RetrievalTrace) -> str:
    """Format trace as a compact human-readable string for CLI output."""
    lines = [
        "--- Retrieval Trace ---",
        f"Query:    {trace.query_original}",
        f"Expanded: {trace.query_expanded}",
        f"Strategy: {trace.strategy}  |  FTS={trace.fts_candidates}  BM25={trace.bm25_candidates}  Fused={trace.fused_count}",
        f"Timing:   FTS={trace.elapsed_fts_ms:.0f}ms  BM25={trace.elapsed_bm25_ms:.0f}ms  Total={trace.elapsed_total_ms:.0f}ms",
        "",
        f"{'#':>2}  {'Final':>7}  {'FTS':>7}  {'BM25':>7}  {'RRF':>6}  {'Meta':>5}  File",
        f"{'':->2}  {'':->7}  {'':->7}  {'':->7}  {'':->6}  {'':->5}  {'':->40}",
    ]
    for doc in trace.documents:
        name = doc.file_path.replace("\\", "/").split("/")[-1]
        if len(name) > 50:
            name = name[:47] + "..."
        overlap = ""
        if doc.metadata_overlap_terms:
            overlap = f"  [{', '.join(doc.metadata_overlap_terms[:5])}]"
        lines.append(
            f"{doc.rank:2d}  {doc.final_score:7.1f}  {doc.fts_score:7.1f}  "
            f"{doc.bm25_score:7.1f}  {doc.rrf_score:6.3f}  {doc.metadata_bonus:5.2f}  "
            f"{name}{overlap}"
        )
    lines.append("--- End Trace ---")
    return "\n".join(lines)


class TraceCollector:
    """Context-local trace accumulator.  One instance per retrieve_documents call."""

    def __init__(self) -> None:
        self.trace: RetrievalTrace | None = None
        self._t0: float = 0.0

    def start(self, query_original: str, query_expanded: str, top_k: int) -> None:
        self._t0 = time.perf_counter()
        self.trace = RetrievalTrace(
            query_original=query_original,
            query_expanded=query_expanded,
            strategy="pending",
            top_k=top_k,
        )

    def record_fts(self, count: int, elapsed_ms: float) -> None:
        if self.trace:
            self.trace.fts_candidates = count
            self.trace.elapsed_fts_ms = elapsed_ms

    def record_bm25(self, count: int, elapsed_ms: float) -> None:
        if self.trace:
            self.trace.bm25_candidates = count
            self.trace.elapsed_bm25_ms = elapsed_ms

    def record_fusion(
        self,
        strategy: str,
        fused_count: int,
        ranked_docs: list[dict[str, Any]],
        raw_scores: dict[str, dict[str, float]],
        rrf_scores: dict[str, float],
        metadata_bonuses: dict[str, float],
        metadata_overlap_terms: dict[str, list[str]],
    ) -> None:
        if not self.trace:
            return
        self.trace.strategy = strategy
        self.trace.fused_count = fused_count
        self.trace.elapsed_total_ms = (time.perf_counter() - self._t0) * 1000

        FTS_WEIGHT = 1.0
        BM25_WEIGHT = 0.4

        for rank, doc in enumerate(ranked_docs, start=1):
            fp = str(doc.get("file_path", ""))
            fts_raw = raw_scores.get(fp, {}).get("fts", 0.0)
            bm25_raw = raw_scores.get(fp, {}).get("bm25", 0.0)
            blended = fts_raw * FTS_WEIGHT + bm25_raw * BM25_WEIGHT
            self.trace.documents.append(
                DocumentTrace(
                    file_path=fp,
                    rank=rank,
                    final_score=float(doc.get("score", 0.0)),
                    fts_score=fts_raw,
                    bm25_score=bm25_raw,
                    rrf_score=rrf_scores.get(fp, 0.0),
                    metadata_bonus=metadata_bonuses.get(fp, 0.0),
                    blended_score=blended,
                    matched_chunks_count=len(doc.get("matched_chunks") or []),
                    metadata_overlap_terms=metadata_overlap_terms.get(fp, []),
                )
            )

    def finish_bm25_only(self, ranked_docs: list[dict[str, Any]]) -> None:
        if not self.trace:
            return
        self.trace.strategy = "bm25_only"
        self.trace.elapsed_total_ms = (time.perf_counter() - self._t0) * 1000
        for rank, doc in enumerate(ranked_docs, start=1):
            fp = str(doc.get("file_path", ""))
            self.trace.documents.append(
                DocumentTrace(
                    file_path=fp,
                    rank=rank,
                    final_score=float(doc.get("score", 0.0)),
                    bm25_score=float(doc.get("score", 0.0)),
                )
            )
