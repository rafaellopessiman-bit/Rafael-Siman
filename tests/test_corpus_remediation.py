from src.knowledge.corpus_audit import (
    CorpusAuditReport,
    DocumentCluster,
    DocumentOutlier,
)
from src.knowledge.corpus_filter import detect_duplicates
from src.knowledge.corpus_remediation import (
    build_document_remediation_plan,
    build_remediation_policy,
)


def _doc(file_path: str, content: str) -> dict:
    return {
        "file_path": file_path,
        "file_name": file_path.split("/")[-1],
        "content": content,
        "metadata": {},
    }


def test_remediation_ignores_duplicates_and_isolates_bad_documents():
    documents = [
        _doc("/good.txt", "good document with enough unique tokens and descriptive content for indexing"),
        _doc("/dup-a.txt", "same content duplicate with enough descriptive content"),
        _doc("/dup-b.txt", "same content duplicate with enough descriptive content"),
        _doc("/bad.txt", "12345 12345 12345 12345 12345 12345 12345 12345"),
    ]
    duplicate_report = detect_duplicates(documents)
    audit_report = CorpusAuditReport(
        total_documents=4,
        duplicate_count=1,
        duplicate_paths=["/dup-b.txt"],
        outliers=[DocumentOutlier(file_path="/bad.txt", reasons=["no_usable_chunks", "numeric_heavy"])],
        clusters=[],
        flag_counts={"no_usable_chunks": 1, "numeric_heavy": 1},
    )

    decisions = build_document_remediation_plan(documents, audit_report, duplicate_report=duplicate_report)
    actions = {decision.file_path: decision.action for decision in decisions}

    assert actions["/good.txt"] == "index"
    assert actions["/dup-a.txt"] == "index"
    assert actions["/dup-b.txt"] == "ignore_duplicate"
    assert actions["/bad.txt"] == "isolate"


def test_remediation_marks_clustered_documents_for_review():
    documents = [
        _doc("/a.txt", "retrieval ranking metadata overlap hybrid scoring chunk quality"),
        _doc("/b.txt", "retrieval ranking metadata overlap hybrid scoring chunk quality variant"),
    ]
    audit_report = CorpusAuditReport(
        total_documents=2,
        duplicate_count=0,
        duplicate_paths=[],
        outliers=[],
        clusters=[DocumentCluster(member_paths=["/a.txt", "/b.txt"], shared_terms=["retrieval"], average_similarity=0.7)],
        flag_counts={},
    )

    decisions = build_document_remediation_plan(documents, audit_report)

    assert {decision.action for decision in decisions} == {"index_with_review"}


def test_remediation_policy_can_downgrade_isolation_to_review():
    documents = [_doc("/bad.txt", "12345 12345 12345 12345 12345")]
    audit_report = CorpusAuditReport(
        total_documents=1,
        duplicate_count=0,
        duplicate_paths=[],
        outliers=[DocumentOutlier(file_path="/bad.txt", reasons=["numeric_heavy"])],
        clusters=[],
        flag_counts={"numeric_heavy": 1},
    )

    decisions = build_document_remediation_plan(
        documents,
        audit_report,
        policy=build_remediation_policy("no_usable_chunks"),
    )

    assert decisions[0].action == "index_with_review"
    assert decisions[0].should_index is True
