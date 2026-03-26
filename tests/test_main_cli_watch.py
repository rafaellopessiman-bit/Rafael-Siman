from pathlib import Path

import src.main_cli_watch as cli


def test_handle_watch_auto_remediates_ocr_and_indexes(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyAuditReport:
        duplicate_count = 0
        outliers = []
        clusters = []
        flag_counts = {}

    class DummyDuplicateReport:
        duplicates = []
        unique_documents = [
            {"file_path": "E:/E-book/scan.pdf", "content": "texto OCR", "metadata": {}},
        ]

    captured = {"history_actions": [], "upsert_documents": None, "load_calls": []}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/scan.pdf")])
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)

    def fake_load(file_paths, max_workers=None, **kwargs):
        captured["load_calls"].append(kwargs)
        if kwargs.get("pdf_ocr_enabled"):
            return (
                [{"file_path": "E:/E-book/scan.pdf", "content": "texto OCR", "metadata": {}}],
                [],
            )
        return (
            [],
            ["Falha ao carregar E:/E-book/scan.pdf: PDF sem texto extraivel: E:/E-book/scan.pdf"],
        )

    monkeypatch.setattr(cli, "load_document_batch_with_report", fake_load)
    monkeypatch.setattr(cli, "audit_documents", lambda documents: DummyAuditReport())
    monkeypatch.setattr(cli, "detect_duplicates", lambda documents: DummyDuplicateReport())
    monkeypatch.setattr(
        cli,
        "record_document_audit_history",
        lambda **kwargs: captured["history_actions"].extend(record.remediation_action for record in kwargs["records"]),
    )
    monkeypatch.setattr(
        cli,
        "upsert_documents",
        lambda db_path, documents, base_dir=None, force=False: captured.update({
            "upsert_documents": documents,
        }) or [{"action": "inserted"}],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = 2
        batch_size = 25
        interval_seconds = 1
        max_cycles = 1
        remediation_policy = "ocr-required"
        enable_pdf_ocr = False
        pdf_ocr_command = None
        pdf_ocr_language = None
        enable_image_ocr = False
        image_ocr_command = None
        image_ocr_language = None
        isolate_flags = None

    result = cli._handle_watch(Args())

    assert "=== Atlas Local | Watch ===" in result
    assert "Remediation policy: ocr-required" in result
    assert "Cycles executed: 1" in result
    assert "Changes detected: 1" in result
    assert "Auto-remediated OCR: 1" in result
    assert "Indexed: 1" in result
    assert captured["history_actions"] == ["ocr_required", "index"]
    assert captured["upsert_documents"] == [{"file_path": "E:/E-book/scan.pdf", "content": "texto OCR", "metadata": {}}]
    assert captured["load_calls"][0]["pdf_ocr_enabled"] is False
    assert captured["load_calls"][1]["pdf_ocr_enabled"] is True


def test_handle_watch_manual_policy_keeps_ocr_pending(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    captured = {"history_actions": [], "upsert_called": False}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/scan.pdf")])
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [],
            ["Falha ao carregar E:/E-book/scan.pdf: PDF sem texto extraivel: E:/E-book/scan.pdf"],
        ),
    )
    monkeypatch.setattr(
        cli,
        "record_document_audit_history",
        lambda **kwargs: captured["history_actions"].extend(record.remediation_action for record in kwargs["records"]),
    )
    monkeypatch.setattr(
        cli,
        "upsert_documents",
        lambda *args, **kwargs: captured.update({"upsert_called": True}) or [],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 10
        interval_seconds = 1
        max_cycles = 1
        remediation_policy = "manual"
        enable_pdf_ocr = False
        pdf_ocr_command = None
        pdf_ocr_language = None
        enable_image_ocr = False
        image_ocr_command = None
        image_ocr_language = None
        isolate_flags = None

    result = cli._handle_watch(Args())

    assert "Remediation policy: manual" in result
    assert "Auto-remediated OCR: 0" in result
    assert "Pending OCR: 1" in result
    assert "Indexed: 0" in result
    assert captured["history_actions"] == ["ocr_required"]
    assert captured["upsert_called"] is False


def test_handle_watch_uses_persisted_snapshot_to_skip_first_cycle(monkeypatch, tmp_path):
    watch_file = tmp_path / "scan.pdf"
    watch_file.write_text("conteudo", encoding="utf-8")

    class DummySettings:
        documents_path = str(tmp_path)
        database_path = "data/ebooks.db"

    stored_snapshots = []

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [watch_file])
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(cli, "fetch_watch_snapshot", lambda db_path, watch_path: cli._build_file_signatures([watch_file]))
    monkeypatch.setattr(cli, "upsert_watch_snapshot", lambda db_path, watch_path, snapshot: stored_snapshots.append(snapshot))
    monkeypatch.setattr(cli, "load_document_batch_with_report", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("nao deveria carregar lote sem mudancas")))

    class Args:
        documents_path = str(tmp_path)
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 10
        interval_seconds = 1
        max_cycles = 1
        remediation_policy = "full-auto"
        enable_pdf_ocr = False
        pdf_ocr_command = None
        pdf_ocr_language = None
        enable_image_ocr = False
        image_ocr_command = None
        image_ocr_language = None
        isolate_flags = None

    result = cli._handle_watch(Args())

    assert "Changes detected: 0" in result
    assert "Indexed: 0" in result
    assert len(stored_snapshots) == 1


def test_handle_watch_full_auto_sanitizes_and_applies_isolation(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyOutlier:
        def __init__(self, file_path, reasons):
            self.file_path = file_path
            self.reasons = reasons

    class DummyAuditReport:
        duplicate_count = 0
        outliers = [DummyOutlier("E:/E-book/raw.txt", ["no_usable_chunks"])]
        clusters = []
        flag_counts = {"no_usable_chunks": 1}

    captured = {"upsert_called": False, "audit_content": None, "snapshots": []}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/raw.txt")])
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(cli, "fetch_watch_snapshot", lambda db_path, watch_path: {})
    monkeypatch.setattr(cli, "upsert_watch_snapshot", lambda db_path, watch_path, snapshot: captured["snapshots"].append(snapshot))
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [{"file_path": "E:/E-book/raw.txt", "content": "linha 1\x00\n\n\nlinha   2\r\n", "metadata": {}}],
            [],
        ),
    )

    def fake_audit(documents):
        captured["audit_content"] = documents[0]["content"]
        return DummyAuditReport()

    class DummyDuplicateReport:
        duplicates = []

        def __init__(self, documents):
            self.unique_documents = documents

    monkeypatch.setattr(cli, "audit_documents", fake_audit)
    monkeypatch.setattr(cli, "detect_duplicates", lambda documents: DummyDuplicateReport(documents))
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))
    monkeypatch.setattr(cli, "upsert_documents", lambda *args, **kwargs: captured.update({"upsert_called": True}) or [])

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 10
        interval_seconds = 1
        max_cycles = 1
        remediation_policy = "full-auto"
        enable_pdf_ocr = False
        pdf_ocr_command = None
        pdf_ocr_language = None
        enable_image_ocr = False
        image_ocr_command = None
        image_ocr_language = None
        isolate_flags = "no_usable_chunks"

    result = cli._handle_watch(Args())

    assert captured["audit_content"] == "linha 1\n\nlinha 2"
    assert "Sanitized documents: 1" in result
    assert "Auto-isolated: 1" in result
    assert "Remediation isolate: 1" in result
    assert captured["upsert_called"] is False
