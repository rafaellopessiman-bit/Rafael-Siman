import json
import zipfile
from pathlib import Path

import src.main_cli_report as cli


def test_handle_report_renders_json(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(
        cli,
        "fetch_all_documents",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.pdf",
                "file_name": "doc1.pdf",
                "file_extension": ".pdf",
                "updated_at": "2026-03-25T10:00:00+00:00",
                "content": "conteudo detalhado do documento",
                "metadata": {"title": "Doc 1", "author": "Autor 1", "theme": "arquitetura"},
            }
        ],
    )
    monkeypatch.setattr(cli, "fetch_all_chunks", lambda db_path, base_dir=None: ["chunk-1", "chunk-2"])
    monkeypatch.setattr(
        cli,
        "fetch_latest_document_audit_decisions",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.pdf",
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "flags": ["ocr_required"],
                "remediation_action": "ocr_required",
                "should_index": False,
                "source_command": "audit",
                "duplicate_of": None,
                "created_at": "2026-03-25T11:00:00+00:00",
            }
        ],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output = "json"

    payload = json.loads(cli._handle_report(Args()))

    assert payload["status"] == "ok"
    assert payload["report"]["output"] == "json"
    assert payload["summary"]["indexed_documents"] == 1
    assert payload["summary"]["pending_ocr_documents"] == 1
    assert payload["documents"][0]["latest_action"] == "ocr_required"


def test_handle_report_renders_csv(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(
        cli,
        "fetch_all_documents",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.docx",
                "file_name": "doc1.docx",
                "file_extension": ".docx",
                "updated_at": "2026-03-25T10:00:00+00:00",
                "content": "conteudo detalhado do documento",
                "metadata": {"title": "Doc 1", "theme": "processos"},
            }
        ],
    )
    monkeypatch.setattr(cli, "fetch_all_chunks", lambda db_path, base_dir=None: ["chunk-1"])
    monkeypatch.setattr(cli, "fetch_latest_document_audit_decisions", lambda db_path, base_dir=None: [])

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output = "csv"

    result = cli._handle_report(Args())

    assert "file_path,file_name,file_extension,indexed" in result
    assert "E:/E-book/doc1.docx" in result
    assert ".docx" in result


def test_handle_report_renders_markdown(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(
        cli,
        "fetch_all_documents",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.txt",
                "file_name": "doc1.txt",
                "file_extension": ".txt",
                "updated_at": "2026-03-25T10:00:00+00:00",
                "content": "conteudo detalhado do documento",
                "metadata": {"theme": "arquitetura"},
            }
        ],
    )
    monkeypatch.setattr(cli, "fetch_all_chunks", lambda db_path, base_dir=None: ["chunk-1"])
    monkeypatch.setattr(
        cli,
        "fetch_latest_document_audit_decisions",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.txt",
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "flags": ["cluster_similar_document"],
                "remediation_action": "index_with_review",
                "should_index": True,
                "source_command": "audit",
                "duplicate_of": None,
                "created_at": "2026-03-25T11:00:00+00:00",
            }
        ],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output = "markdown"

    result = cli._handle_report(Args())

    assert "# Atlas Local Report" in result
    assert "## Latest Actions" in result
    assert "index_with_review" in result
    assert "E:/E-book/doc1.txt" in result


def test_handle_report_writes_xlsx_with_operational_sheets(monkeypatch, tmp_path):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(
        cli,
        "fetch_all_documents",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.pdf",
                "file_name": "doc1.pdf",
                "file_extension": ".pdf",
                "updated_at": "2026-03-25T10:00:00+00:00",
                "content": "conteudo detalhado do documento",
                "metadata": {"theme": "arquitetura", "title": "Doc 1"},
            }
        ],
    )
    monkeypatch.setattr(cli, "fetch_all_chunks", lambda db_path, base_dir=None: ["chunk-1"])
    monkeypatch.setattr(
        cli,
        "fetch_latest_document_audit_decisions",
        lambda db_path, base_dir=None: [
            {
                "file_path": "E:/E-book/doc1.pdf",
                "audit_timestamp": "2026-03-25T11:00:00+00:00",
                "flags": ["ocr_required"],
                "remediation_action": "ocr_required",
                "should_index": False,
                "source_command": "audit",
                "duplicate_of": None,
                "created_at": "2026-03-25T11:00:00+00:00",
            }
        ],
    )

    output_path = tmp_path / "report.xlsx"

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output = "xlsx"
        output_path = None

    Args.output_path = str(output_path)

    result = cli._handle_report(Args())

    assert f"Relatorio gerado em: {output_path}" == result
    assert output_path.exists()
    with zipfile.ZipFile(output_path) as archive:
        workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
        pending_xml = archive.read("xl/worksheets/sheet6.xml").decode("utf-8")
        assert 'name="PendingOCR"' in workbook_xml
        assert 'name="Documents"' in workbook_xml
        assert '<autoFilter ref="A1:O2"/>' in pending_xml
        assert '<cols>' in pending_xml
        assert 'state="frozen"' in pending_xml
        assert ' s="1"' in pending_xml
