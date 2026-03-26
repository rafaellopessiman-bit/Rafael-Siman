"""
Automated Relevance Evaluation Suite for the retrieval pipeline.

Computes standard IR metrics (MRR, Precision@K, NDCG@K) against
a benchmark of queries with known expected results, and detects
regressions against a saved baseline.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from src.knowledge.retriever import retrieve_documents
from src.storage.document_store import fetch_all_documents


# ── Data classes ─────────────────────────────────────────

@dataclass
class EvalQuery:
    """A single benchmark query with expected relevant documents."""
    query: str
    expected_files: list[str]
    description: str = ""
    min_score: float = 0.0


@dataclass
class QueryResult:
    """Result of evaluating a single benchmark query."""
    query: str
    description: str
    retrieved_files: list[str]
    expected_files: list[str]
    scores: list[float]
    reciprocal_rank: float
    precision_at_k: float
    ndcg_at_k: float
    top_hit_correct: bool
    elapsed_ms: float


@dataclass
class EvalReport:
    """Aggregated evaluation report."""
    timestamp: str = ""
    db_path: str = ""
    total_queries: int = 0
    top_k: int = 5
    mrr: float = 0.0
    mean_precision_at_k: float = 0.0
    mean_ndcg_at_k: float = 0.0
    top1_accuracy: float = 0.0
    query_results: list[QueryResult] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)


# ── Metric computations ─────────────────────────────────

def _reciprocal_rank(retrieved: list[str], expected: set[str]) -> float:
    """MRR contribution: 1/rank of first relevant hit, or 0."""
    for rank, file_path in enumerate(retrieved, start=1):
        if _matches_any(file_path, expected):
            return 1.0 / rank
    return 0.0


def _precision_at_k(retrieved: list[str], expected: set[str]) -> float:
    """Fraction of retrieved docs that are relevant."""
    if not retrieved:
        return 0.0
    hits = sum(1 for fp in retrieved if _matches_any(fp, expected))
    return hits / len(retrieved)


def _dcg(relevances: list[float]) -> float:
    """Discounted Cumulative Gain."""
    return sum(rel / math.log2(rank + 1) for rank, rel in enumerate(relevances, start=1))


def _ndcg_at_k(retrieved: list[str], expected: set[str]) -> float:
    """Normalized DCG: how well ranked the relevant docs are."""
    relevances = [1.0 if _matches_any(fp, expected) else 0.0 for fp in retrieved]
    dcg = _dcg(relevances)
    ideal = sorted(relevances, reverse=True)
    idcg = _dcg(ideal)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _matches_any(file_path: str, expected: set[str]) -> bool:
    """Check if file_path matches any expected pattern (substring match)."""
    normalized = file_path.replace("\\", "/").lower()
    return any(exp.lower() in normalized for exp in expected)


# ── Core evaluation engine ───────────────────────────────

def load_eval_queries(path: str | Path) -> list[EvalQuery]:
    """Load benchmark queries from a JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    queries = data if isinstance(data, list) else data.get("queries", [])
    return [
        EvalQuery(
            query=q["query"],
            expected_files=q["expected_files"],
            description=q.get("description", ""),
            min_score=q.get("min_score", 0.0),
        )
        for q in queries
    ]


def evaluate_retrieval(
    eval_queries: list[EvalQuery],
    db_path: str,
    top_k: int = 5,
    docs_path: str = "data/entrada",
) -> EvalReport:
    """
    Run all benchmark queries through the retrieval pipeline and compute metrics.

    Args:
        eval_queries: List of benchmark queries with expected results.
        db_path: Path to the SQLite database.
        top_k: Number of results to retrieve per query.
        docs_path: Base path for document loading (fallback).

    Returns:
        EvalReport with per-query and aggregated metrics.
    """
    from datetime import datetime, timezone

    documents = fetch_all_documents(db_path=db_path, base_dir=docs_path)
    if not documents:
        return EvalReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            db_path=db_path,
            regressions=["Nenhum documento encontrado no banco."],
        )

    report = EvalReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        db_path=db_path,
        total_queries=len(eval_queries),
        top_k=top_k,
    )

    rr_sum = 0.0
    prec_sum = 0.0
    ndcg_sum = 0.0
    top1_hits = 0

    for eq in eval_queries:
        t0 = time.perf_counter()
        ranked = retrieve_documents(eq.query, documents, top_k, db_path=db_path)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        retrieved_files = [str(d.get("file_path", "")) for d in ranked]
        scores = [float(d.get("score", 0)) for d in ranked]
        expected_set = set(eq.expected_files)

        rr = _reciprocal_rank(retrieved_files, expected_set)
        prec = _precision_at_k(retrieved_files, expected_set)
        ndcg = _ndcg_at_k(retrieved_files, expected_set)
        top1_ok = bool(retrieved_files and _matches_any(retrieved_files[0], expected_set))

        rr_sum += rr
        prec_sum += prec
        ndcg_sum += ndcg
        if top1_ok:
            top1_hits += 1

        report.query_results.append(QueryResult(
            query=eq.query,
            description=eq.description,
            retrieved_files=retrieved_files,
            expected_files=eq.expected_files,
            scores=scores,
            reciprocal_rank=round(rr, 4),
            precision_at_k=round(prec, 4),
            ndcg_at_k=round(ndcg, 4),
            top_hit_correct=top1_ok,
            elapsed_ms=round(elapsed_ms, 1),
        ))

    n = max(len(eval_queries), 1)
    report.mrr = round(rr_sum / n, 4)
    report.mean_precision_at_k = round(prec_sum / n, 4)
    report.mean_ndcg_at_k = round(ndcg_sum / n, 4)
    report.top1_accuracy = round(top1_hits / n, 4)

    return report


# ── Baseline comparison ──────────────────────────────────

def save_baseline(report: EvalReport, path: str | Path) -> None:
    """Save the current report as a baseline for future regression detection."""
    data = {
        "timestamp": report.timestamp,
        "db_path": report.db_path,
        "top_k": report.top_k,
        "mrr": report.mrr,
        "mean_precision_at_k": report.mean_precision_at_k,
        "mean_ndcg_at_k": report.mean_ndcg_at_k,
        "top1_accuracy": report.top1_accuracy,
        "per_query": {
            qr.query: {
                "reciprocal_rank": qr.reciprocal_rank,
                "precision_at_k": qr.precision_at_k,
                "ndcg_at_k": qr.ndcg_at_k,
                "top_hit_correct": qr.top_hit_correct,
            }
            for qr in report.query_results
        },
    }
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_regressions(
    report: EvalReport,
    baseline_path: str | Path,
    threshold: float = 0.05,
) -> list[str]:
    """
    Compare current report against saved baseline and return regression messages.

    A regression is detected when any aggregate metric drops by more than `threshold`.
    """
    path = Path(baseline_path)
    if not path.exists():
        return []

    baseline = json.loads(path.read_text(encoding="utf-8"))
    regressions: list[str] = []

    for metric in ("mrr", "mean_precision_at_k", "mean_ndcg_at_k", "top1_accuracy"):
        current = getattr(report, metric, 0.0)
        previous = baseline.get(metric, 0.0)
        if previous > 0 and (previous - current) > threshold:
            regressions.append(
                f"REGRESSAO {metric}: {previous:.4f} → {current:.4f} (delta={current - previous:+.4f})"
            )

    per_query_baseline = baseline.get("per_query", {})
    for qr in report.query_results:
        prev = per_query_baseline.get(qr.query, {})
        prev_rr = prev.get("reciprocal_rank", 0.0)
        if prev_rr > 0 and (prev_rr - qr.reciprocal_rank) > threshold:
            regressions.append(
                f"REGRESSAO query '{qr.query}': RR {prev_rr:.4f} → {qr.reciprocal_rank:.4f}"
            )

    return regressions


# ── Report formatting ────────────────────────────────────

def format_report(report: EvalReport) -> str:
    """Format the evaluation report as human-readable text."""
    lines = [
        "=" * 60,
        "  Evaluation Report — Retrieval Quality",
        "=" * 60,
        f"  Timestamp : {report.timestamp}",
        f"  DB Path   : {report.db_path}",
        f"  Queries   : {report.total_queries}",
        f"  TOP_K     : {report.top_k}",
        "",
        "  Aggregate Metrics:",
        f"    MRR              : {report.mrr:.4f}",
        f"    Mean P@{report.top_k}         : {report.mean_precision_at_k:.4f}",
        f"    Mean NDCG@{report.top_k}      : {report.mean_ndcg_at_k:.4f}",
        f"    Top-1 Accuracy   : {report.top1_accuracy:.4f}",
        "",
    ]

    if report.regressions:
        lines.append("  ⚠ REGRESSIONS DETECTED:")
        for reg in report.regressions:
            lines.append(f"    - {reg}")
        lines.append("")

    lines.append("  Per-Query Results:")
    lines.append("-" * 60)

    for qr in report.query_results:
        status = "OK" if qr.top_hit_correct else "MISS"
        lines.append(f"  [{status}] {qr.query}")
        if qr.description:
            lines.append(f"       Desc: {qr.description}")
        lines.append(f"       RR={qr.reciprocal_rank:.4f}  P@K={qr.precision_at_k:.4f}  NDCG={qr.ndcg_at_k:.4f}  {qr.elapsed_ms:.0f}ms")
        lines.append(f"       Expected: {qr.expected_files}")
        top_hits = [
            f"{fp.split('/')[-1].split(chr(92))[-1]} ({s:.1f})"
            for fp, s in zip(qr.retrieved_files[:3], qr.scores[:3])
        ]
        lines.append(f"       Got top3: {top_hits}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
