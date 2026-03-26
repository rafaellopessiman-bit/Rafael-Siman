"""Tests for the retrieval evaluation suite."""
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.knowledge.evaluation import (
    EvalQuery,
    EvalReport,
    QueryResult,
    _reciprocal_rank,
    _precision_at_k,
    _ndcg_at_k,
    _matches_any,
    load_eval_queries,
    evaluate_retrieval,
    save_baseline,
    detect_regressions,
    format_report,
)


# ── Metric unit tests ───────────────────────────────────

class TestMatchesAny:
    def test_substring_match(self):
        assert _matches_any("E:\\E-book\\MongoDB Notes for Professionals.pdf", {"MongoDB"})

    def test_case_insensitive(self):
        assert _matches_any("E:\\E-book\\mongodb-guide.pdf", {"MongoDB"})

    def test_no_match(self):
        assert not _matches_any("E:\\E-book\\python-guide.pdf", {"MongoDB"})

    def test_backslash_normalized(self):
        assert _matches_any("E:\\E-book\\sub\\mongodb.pdf", {"mongodb"})


class TestReciprocalRank:
    def test_first_hit_relevant(self):
        assert _reciprocal_rank(["mongo.pdf", "python.pdf"], {"mongo"}) == 1.0

    def test_second_hit_relevant(self):
        assert _reciprocal_rank(["python.pdf", "mongo.pdf"], {"mongo"}) == 0.5

    def test_no_relevant_hit(self):
        assert _reciprocal_rank(["python.pdf", "java.pdf"], {"mongo"}) == 0.0

    def test_empty_retrieved(self):
        assert _reciprocal_rank([], {"mongo"}) == 0.0


class TestPrecisionAtK:
    def test_all_relevant(self):
        files = ["mongo.pdf", "atlas.pdf"]
        assert _precision_at_k(files, {"mongo", "atlas"}) == 1.0

    def test_half_relevant(self):
        files = ["mongo.pdf", "python.pdf"]
        assert _precision_at_k(files, {"mongo"}) == 0.5

    def test_none_relevant(self):
        assert _precision_at_k(["python.pdf"], {"mongo"}) == 0.0

    def test_empty(self):
        assert _precision_at_k([], {"mongo"}) == 0.0


class TestNdcgAtK:
    def test_perfect_ranking(self):
        files = ["mongo.pdf", "atlas.pdf", "other.pdf"]
        expected = {"mongo", "atlas"}
        ndcg = _ndcg_at_k(files, expected)
        assert ndcg == 1.0

    def test_inverted_ranking(self):
        files = ["other.pdf", "mongo.pdf", "atlas.pdf"]
        expected = {"mongo", "atlas"}
        ndcg = _ndcg_at_k(files, expected)
        assert 0.0 < ndcg < 1.0

    def test_no_relevant(self):
        assert _ndcg_at_k(["other.pdf"], {"mongo"}) == 0.0


# ── IO tests ─────────────────────────────────────────────

class TestLoadEvalQueries:
    def test_loads_from_json(self, tmp_path):
        data = {
            "queries": [
                {"query": "test q", "expected_files": ["file.pdf"], "description": "desc"},
            ]
        }
        p = tmp_path / "eval.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        queries = load_eval_queries(p)
        assert len(queries) == 1
        assert queries[0].query == "test q"
        assert queries[0].expected_files == ["file.pdf"]

    def test_loads_list_format(self, tmp_path):
        data = [{"query": "q1", "expected_files": ["a.pdf"]}]
        p = tmp_path / "eval.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        queries = load_eval_queries(p)
        assert len(queries) == 1


# ── Evaluation integration test ──────────────────────────

class TestEvaluateRetrieval:
    @patch("src.knowledge.evaluation.fetch_all_documents")
    @patch("src.knowledge.evaluation.retrieve_documents")
    def test_computes_metrics(self, mock_retrieve, mock_fetch):
        mock_fetch.return_value = [
            {"file_path": "mongo.pdf", "content": "mongodb indexing", "file_name": "mongo.pdf"},
            {"file_path": "python.pdf", "content": "python guide", "file_name": "python.pdf"},
        ]
        mock_retrieve.return_value = [
            {"file_path": "mongo.pdf", "score": 20.0},
            {"file_path": "python.pdf", "score": 5.0},
        ]

        queries = [
            EvalQuery(query="mongodb", expected_files=["mongo.pdf"], description="test"),
        ]
        report = evaluate_retrieval(queries, db_path=":memory:", top_k=5)

        assert report.total_queries == 1
        assert report.mrr == 1.0
        assert report.top1_accuracy == 1.0
        assert len(report.query_results) == 1
        assert report.query_results[0].top_hit_correct is True

    @patch("src.knowledge.evaluation.fetch_all_documents")
    def test_empty_database(self, mock_fetch):
        mock_fetch.return_value = []
        report = evaluate_retrieval([], db_path=":memory:")
        assert "Nenhum documento" in report.regressions[0]


# ── Baseline and regression tests ────────────────────────

class TestBaselineAndRegressions:
    def test_save_and_load_baseline(self, tmp_path):
        report = EvalReport(
            timestamp="2026-01-01T00:00:00",
            db_path="test.db",
            total_queries=1,
            top_k=5,
            mrr=0.8,
            mean_precision_at_k=0.6,
            mean_ndcg_at_k=0.7,
            top1_accuracy=0.9,
            query_results=[
                QueryResult(
                    query="test", description="", retrieved_files=[], expected_files=[],
                    scores=[], reciprocal_rank=0.8, precision_at_k=0.6,
                    ndcg_at_k=0.7, top_hit_correct=True, elapsed_ms=10.0,
                ),
            ],
        )
        baseline_path = tmp_path / "baseline.json"
        save_baseline(report, baseline_path)
        assert baseline_path.exists()

        data = json.loads(baseline_path.read_text())
        assert data["mrr"] == 0.8

    def test_detect_no_regression(self, tmp_path):
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps({
            "mrr": 0.8, "mean_precision_at_k": 0.6,
            "mean_ndcg_at_k": 0.7, "top1_accuracy": 0.9,
            "per_query": {},
        }))

        report = EvalReport(mrr=0.85, mean_precision_at_k=0.65, mean_ndcg_at_k=0.75, top1_accuracy=0.95)
        regressions = detect_regressions(report, baseline_path)
        assert regressions == []

    def test_detect_regression(self, tmp_path):
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps({
            "mrr": 0.8, "mean_precision_at_k": 0.6,
            "mean_ndcg_at_k": 0.7, "top1_accuracy": 0.9,
            "per_query": {},
        }))

        report = EvalReport(mrr=0.5, mean_precision_at_k=0.3, mean_ndcg_at_k=0.4, top1_accuracy=0.4)
        regressions = detect_regressions(report, baseline_path)
        assert len(regressions) >= 3
        assert any("mrr" in r for r in regressions)

    def test_no_baseline_file(self, tmp_path):
        report = EvalReport(mrr=0.8)
        regressions = detect_regressions(report, tmp_path / "nonexistent.json")
        assert regressions == []


# ── Format report test ───────────────────────────────────

class TestFormatReport:
    def test_format_includes_metrics(self):
        report = EvalReport(
            timestamp="2026-01-01T00:00:00",
            db_path="test.db",
            total_queries=1,
            mrr=0.75,
            mean_precision_at_k=0.5,
            mean_ndcg_at_k=0.6,
            top1_accuracy=1.0,
            query_results=[
                QueryResult(
                    query="mongodb", description="",
                    retrieved_files=["mongo.pdf"], expected_files=["mongo.pdf"],
                    scores=[20.0], reciprocal_rank=1.0, precision_at_k=1.0,
                    ndcg_at_k=1.0, top_hit_correct=True, elapsed_ms=5.2,
                ),
            ],
        )
        text = format_report(report)
        assert "MRR" in text
        assert "0.7500" in text
        assert "[OK]" in text
        assert "mongodb" in text

    def test_format_shows_regressions(self):
        report = EvalReport(
            regressions=["REGRESSAO mrr: 0.8 -> 0.5"],
            query_results=[],
        )
        text = format_report(report)
        assert "REGRESSIONS" in text
        assert "REGRESSAO" in text
