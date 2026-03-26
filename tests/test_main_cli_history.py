import json

import src.main_cli_history as cli


def test_handle_history_renders_text_entries(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "count_document_audit_history", lambda **kwargs: 2)
    monkeypatch.setattr(
        cli,
        "fetch_document_audit_history",
        lambda **kwargs: [
            {
                "file_path": "doc.txt",
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "flags": ["numeric_heavy"],
                "remediation_action": "index_with_review",
                "should_index": True,
                "source_command": "audit",
                "duplicate_of": None,
                "created_at": "2026-03-25T11:00:05+00:00",
            },
            {
                "file_path": "doc.txt",
                "audit_timestamp": "2026-03-25T10:00:00+00:00",
                "flags": ["no_usable_chunks"],
                "remediation_action": "isolate",
                "should_index": False,
                "source_command": "index",
                "duplicate_of": None,
                "created_at": "2026-03-25T10:00:05+00:00",
            },
        ],
    )
    monkeypatch.setattr(
        cli,
        "summarize_document_audit_history",
        lambda **kwargs: {
            "action_counts": {"index_with_review": 1, "isolate": 1},
            "latest_decision": {
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "remediation_action": "index_with_review",
                "should_index": True,
                "source_command": "audit",
                "duplicate_of": None,
                "flags": ["numeric_heavy"],
            },
        },
    )

    class Args:
        file_path = "E:/E-book/doc.txt"
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        limit = 5
        offset = 0
        source_command = None
        remediation_action = None
        output = "text"

    result = cli._handle_history(Args())

    assert "=== Atlas Local | History ===" in result
    assert "Documento: E:/E-book/doc.txt" in result
    assert "Offset: 0" in result
    assert "Filtros: none" in result
    assert "Registros: 2" in result
    assert "Total filtrado: 2" in result
    assert "Resumo por action: index_with_review=1, isolate=1" in result
    assert "Ultima decisao: 2026-03-25T11:00:00+00:00 | source=audit | action=index_with_review" in result
    assert "action=index_with_review" in result
    assert "action=isolate" in result


def test_handle_history_can_render_json_when_no_records(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "count_document_audit_history", lambda **kwargs: 0)
    monkeypatch.setattr(cli, "fetch_document_audit_history", lambda **kwargs: [])
    monkeypatch.setattr(
        cli,
        "summarize_document_audit_history",
        lambda **kwargs: {"action_counts": {}, "latest_decision": None},
    )

    class Args:
        file_path = "E:/E-book/missing.txt"
        documents_path = None
        database_path = None
        limit = 3
        offset = 0
        source_command = None
        remediation_action = None
        output = "json"

    payload = json.loads(cli._handle_history(Args()))

    assert payload["status"] == "not_found"
    assert payload["count"] == 0
    assert payload["total_count"] == 0
    assert payload["query"]["file_path"] == "E:/E-book/missing.txt"
    assert payload["query"]["database_path"] == "data/ebooks.db"


def test_handle_history_forwards_source_and_action_filters(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    captured = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "count_document_audit_history", lambda **kwargs: 1)

    def _mock_fetch(**kwargs):
        captured.update(kwargs)
        return [
            {
                "file_path": "doc.txt",
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "flags": ["numeric_heavy"],
                "remediation_action": "index_with_review",
                "should_index": True,
                "source_command": "audit",
                "duplicate_of": None,
                "created_at": "2026-03-25T11:00:05+00:00",
            }
        ]

    monkeypatch.setattr(cli, "fetch_document_audit_history", _mock_fetch)
    monkeypatch.setattr(
        cli,
        "summarize_document_audit_history",
        lambda **kwargs: {
            "action_counts": {"index_with_review": 1},
            "latest_decision": {
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "remediation_action": "index_with_review",
                "should_index": True,
                "source_command": "audit",
                "duplicate_of": None,
                "flags": ["numeric_heavy"],
            },
        },
    )

    class Args:
        file_path = "E:/E-book/doc.txt"
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        limit = 7
        offset = 14
        source_command = "audit"
        remediation_action = "index_with_review"
        output = "text"

    result = cli._handle_history(Args())

    assert captured["offset"] == 14
    assert captured["source_command"] == "audit"
    assert captured["remediation_action"] == "index_with_review"
    assert "Filtros: source=audit, action=index_with_review" in result
