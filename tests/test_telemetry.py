"""Tests for src.knowledge.telemetry module."""
import json

import pytest

from src.knowledge.telemetry import (
    DocumentTrace,
    RetrievalTrace,
    TraceCollector,
    format_trace_compact,
)


class TestDocumentTrace:
    def test_defaults(self):
        dt = DocumentTrace(file_path="/a/b.txt", rank=1, final_score=10.0)
        assert dt.fts_score == 0.0
        assert dt.bm25_score == 0.0
        assert dt.metadata_overlap_terms == []

    def test_custom_values(self):
        dt = DocumentTrace(
            file_path="/a/b.txt",
            rank=2,
            final_score=15.5,
            fts_score=8.0,
            bm25_score=5.0,
            rrf_score=0.05,
            metadata_bonus=1.2,
            blended_score=10.0,
            matched_chunks_count=3,
            metadata_overlap_terms=["python", "flask"],
        )
        assert dt.rank == 2
        assert dt.metadata_overlap_terms == ["python", "flask"]


class TestRetrievalTrace:
    def test_to_dict(self):
        trace = RetrievalTrace(
            query_original="test",
            query_expanded="test expanded",
            strategy="hybrid",
            top_k=5,
        )
        d = trace.to_dict()
        assert d["query_original"] == "test"
        assert d["strategy"] == "hybrid"
        assert isinstance(d["documents"], list)

    def test_to_json(self):
        trace = RetrievalTrace(
            query_original="o que é python?",
            query_expanded="python linguagem programação",
            strategy="hybrid",
            top_k=5,
        )
        j = trace.to_json()
        parsed = json.loads(j)
        assert parsed["query_original"] == "o que é python?"

    def test_to_json_preserves_unicode(self):
        trace = RetrievalTrace(
            query_original="café résumé",
            query_expanded="café résumé expanded",
            strategy="hybrid",
            top_k=5,
        )
        j = trace.to_json()
        assert "café" in j
        assert "résumé" in j


class TestTraceCollector:
    def test_start_creates_trace(self):
        tc = TraceCollector()
        assert tc.trace is None
        tc.start("q", "q expanded", 5)
        assert tc.trace is not None
        assert tc.trace.query_original == "q"
        assert tc.trace.strategy == "pending"

    def test_record_fts(self):
        tc = TraceCollector()
        tc.start("q", "q", 5)
        tc.record_fts(42, 15.3)
        assert tc.trace.fts_candidates == 42
        assert tc.trace.elapsed_fts_ms == 15.3

    def test_record_bm25(self):
        tc = TraceCollector()
        tc.start("q", "q", 5)
        tc.record_bm25(100, 25.0)
        assert tc.trace.bm25_candidates == 100

    def test_record_fusion(self):
        tc = TraceCollector()
        tc.start("q", "q", 5)
        docs = [
            {"file_path": "/a.txt", "score": 10.0, "matched_chunks": ["c1"]},
            {"file_path": "/b.txt", "score": 5.0},
        ]
        raw = {"/a.txt": {"fts": 8.0, "bm25": 3.0}, "/b.txt": {"fts": 2.0, "bm25": 4.0}}
        rrf = {"/a.txt": 0.05, "/b.txt": 0.03}
        meta = {"/a.txt": 1.0, "/b.txt": 0.0}
        overlap = {"/a.txt": ["python"], "/b.txt": []}

        tc.record_fusion(
            strategy="hybrid",
            fused_count=2,
            ranked_docs=docs,
            raw_scores=raw,
            rrf_scores=rrf,
            metadata_bonuses=meta,
            metadata_overlap_terms=overlap,
        )

        assert tc.trace.strategy == "hybrid"
        assert tc.trace.fused_count == 2
        assert len(tc.trace.documents) == 2

        d0 = tc.trace.documents[0]
        assert d0.file_path == "/a.txt"
        assert d0.rank == 1
        assert d0.final_score == 10.0
        assert d0.fts_score == 8.0
        assert d0.matched_chunks_count == 1
        assert d0.metadata_overlap_terms == ["python"]

    def test_record_fusion_noop_without_start(self):
        tc = TraceCollector()
        tc.record_fusion(
            strategy="hybrid", fused_count=0, ranked_docs=[],
            raw_scores={}, rrf_scores={}, metadata_bonuses={}, metadata_overlap_terms={},
        )
        assert tc.trace is None

    def test_finish_bm25_only(self):
        tc = TraceCollector()
        tc.start("q", "q", 5)
        docs = [{"file_path": "/x.txt", "score": 7.5}]
        tc.finish_bm25_only(docs)
        assert tc.trace.strategy == "bm25_only"
        assert len(tc.trace.documents) == 1
        assert tc.trace.documents[0].bm25_score == 7.5

    def test_elapsed_total_calculated(self):
        tc = TraceCollector()
        tc.start("q", "q", 5)
        tc.record_fusion(
            strategy="hybrid", fused_count=0, ranked_docs=[],
            raw_scores={}, rrf_scores={}, metadata_bonuses={}, metadata_overlap_terms={},
        )
        assert tc.trace.elapsed_total_ms >= 0


class TestFormatTraceCompact:
    def test_basic_output(self):
        trace = RetrievalTrace(
            query_original="typescript",
            query_expanded="typescript javascript",
            strategy="hybrid",
            top_k=5,
            fts_candidates=10,
            bm25_candidates=20,
            fused_count=2,
            elapsed_fts_ms=12.0,
            elapsed_bm25_ms=8.0,
            elapsed_total_ms=25.0,
            documents=[
                DocumentTrace(
                    file_path="/books/effective_typescript.txt",
                    rank=1,
                    final_score=29.85,
                    fts_score=18.26,
                    bm25_score=26.41,
                    rrf_score=0.033,
                    metadata_bonus=1.2,
                    blended_score=28.824,
                    matched_chunks_count=3,
                    metadata_overlap_terms=["typescript"],
                ),
            ],
        )
        output = format_trace_compact(trace)
        assert "--- Retrieval Trace ---" in output
        assert "typescript" in output
        assert "hybrid" in output
        assert "--- End Trace ---" in output

    def test_long_filename_truncated(self):
        trace = RetrievalTrace(
            query_original="q",
            query_expanded="q",
            strategy="hybrid",
            top_k=5,
            documents=[
                DocumentTrace(
                    file_path="/very_long_" + "x" * 60 + ".txt",
                    rank=1,
                    final_score=1.0,
                ),
            ],
        )
        output = format_trace_compact(trace)
        assert "..." in output

    def test_empty_documents(self):
        trace = RetrievalTrace(
            query_original="q",
            query_expanded="q",
            strategy="hybrid",
            top_k=5,
        )
        output = format_trace_compact(trace)
        assert "--- End Trace ---" in output
