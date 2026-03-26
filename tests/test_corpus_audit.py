import pytest
from src.knowledge.corpus_audit import audit_documents


def _doc(file_path: str, content: str) -> dict:
    return {
        "file_path": file_path,
        "file_name": file_path.split("/")[-1],
        "content": content,
        "metadata": {},
    }


def test_audit_detects_documents_without_usable_chunks():
    documents = [
        _doc("/ok.txt", "This is a valid document with enough descriptive content to survive chunk quality filters and remain useful for retrieval."),
        _doc("/bad.txt", "12345 67890 12345 67890 12345 67890 12345 67890 12345 67890"),
    ]

    report = audit_documents(documents)

    assert report.total_documents == 2
    assert any(item.file_path == "/bad.txt" for item in report.outliers)
    bad_item = next(item for item in report.outliers if item.file_path == "/bad.txt")
    assert "no_usable_chunks" in bad_item.reasons


def test_audit_detects_repetitive_document_outlier():
    repetitive_line = "chapter one repeated heading for testing repeated heading for testing"
    repetitive = "\n".join([repetitive_line] * 12)
    documents = [_doc("/repeat.txt", repetitive)]

    report = audit_documents(documents)

    outlier = report.outliers[0]
    assert outlier.file_path == "/repeat.txt"
    assert "repetitive_content" in outlier.reasons


def test_audit_clusters_similar_documents():
    documents = [
        _doc(
            "/python-a.txt",
            "Python retrieval ranking uses bm25 fusion, metadata overlap and chunk quality for document search in local corpora.",
        ),
        _doc(
            "/python-b.txt",
            "Python retrieval pipeline combines bm25 fusion, metadata overlap and chunk quality for local document search.",
        ),
        _doc(
            "/finance.txt",
            "Financial accounting statements and cash flow analysis have different terminology and different domain structure.",
        ),
    ]

    report = audit_documents(documents, similarity_threshold=0.25)

    assert len(report.clusters) == 1
    member_paths = sorted(report.clusters[0].member_paths)
    assert member_paths == ["/python-a.txt", "/python-b.txt"]


def test_audit_counts_duplicate_documents():
    documents = [
        _doc("/a.txt", "Same document content with enough descriptive terms for duplicate detection to be meaningful."),
        _doc("/b.txt", "Same   document content with enough descriptive terms for duplicate detection to be meaningful."),
    ]

    report = audit_documents(documents)

    assert report.duplicate_count == 1


def test_audit_flags_length_outlier_when_distribution_is_clear():
    documents = [
        _doc(f"/doc-{index}.txt", "Short but valid content for corpus analysis and retrieval testing with enough vocabulary variety present.")
        for index in range(5)
    ]
    documents.append(
        _doc(
            "/very-long.txt",
            " ".join(["extensive"] * 1500) + " retrieval corpus analysis feature selection metadata ranking chunk quality",
        )
    )

    report = audit_documents(documents)

    long_item = next(item for item in report.outliers if item.file_path == "/very-long.txt")
    assert "char_count_outlier" in long_item.reasons or "token_count_outlier" in long_item.reasons
