from pathlib import Path

import src.main_cli_index as cli


def test_handle_index_returns_clean_message_when_loader_finds_no_supported_documents(monkeypatch):
    class DummySettings:
        documents_path = "dados_vazios"
        database_path = "data/atlas_local.db"

    calls = {"initialize": 0, "upsert": 0, "sync": 0}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())

    def fake_collect_paths(_path):
        raise cli.AtlasLoadError("Nenhum arquivo textual suportado foi encontrado em: dados_vazios")

    def fake_initialize_database(*args, **kwargs):
        calls["initialize"] += 1

    def fake_sync_local_files(*args, **kwargs):
        calls["sync"] += 1
        return 0

    def fake_upsert_documents(*args, **kwargs):
        calls["upsert"] += 1
        return []

    monkeypatch.setattr(cli, "collect_supported_document_paths", fake_collect_paths)
    monkeypatch.setattr(cli, "initialize_database", fake_initialize_database)
    monkeypatch.setattr(cli, "sync_local_files", fake_sync_local_files)
    monkeypatch.setattr(cli, "upsert_documents", fake_upsert_documents)

    result = cli._handle_index()

    assert "=== Atlas Local | Index ===" in result
    assert "Origem: dados_vazios" in result
    assert "Aviso: Nenhum arquivo textual suportado foi encontrado em: dados_vazios" in result
    assert "Operação abortada. Banco inalterado." in result
    assert calls["initialize"] == 0
    assert calls["sync"] == 0
    assert calls["upsert"] == 0


def test_handle_index_uses_cli_overrides(monkeypatch):
    class DummySettings:
        documents_path = "data/entrada"
        database_path = "data/original.db"

    captured = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/book.pdf")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: captured.update({"paths": file_paths, "max_workers": max_workers, "loader_kwargs": kwargs}) or (
            [
                {"file_path": "E:/E-book/book.pdf", "content": "conteudo", "metadata": {"theme": "arquitetura"}}
            ],
            [],
        ),
    )
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: captured.update({"db_path": db_path, "base_dir": base_dir}))
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: captured.update({"synced_paths": current_file_paths}) or 0)
    monkeypatch.setattr(cli, "upsert_documents", lambda **kwargs: [{"action": "inserted"}])

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = 6
        batch_size = 25
        enable_pdf_ocr = True
        pdf_ocr_command = "ocrmypdf-custom"
        pdf_ocr_language = "por+eng"
        enable_image_ocr = True
        image_ocr_command = "tesseract-custom"
        image_ocr_language = "por"

    result = cli._handle_index(Args())

    assert "Origem: E:/E-book" in result
    assert "Banco: data/ebooks.db" in result
    assert "Workers: 6" in result
    assert "Batch size: 25" in result
    assert "PDF OCR: enabled (ocrmypdf-custom, lang=por+eng)" in result
    assert "Image OCR: enabled (tesseract-custom, lang=por)" in result
    assert captured["paths"][0] == Path("E:/E-book/book.pdf")
    assert captured["db_path"] == "data/ebooks.db"
    assert captured["loader_kwargs"]["pdf_ocr_enabled"] is True
    assert captured["loader_kwargs"]["image_ocr_enabled"] is True


def test_handle_index_reports_ocr_candidates(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/ok.txt"), Path("E:/E-book/livro1.pdf"), Path("E:/E-book/livro2.pdf")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [{"file_path": "E:/E-book/ok.txt", "content": "conteudo", "metadata": {}}],
            [
                "Falha ao carregar E:/E-book/livro1.pdf: PDF sem texto extraivel: E:/E-book/livro1.pdf",
                "Falha ao carregar E:/E-book/livro2.pdf: PDF sem texto extraivel: E:/E-book/livro2.pdf",
            ],
        ),
    )
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(cli, "upsert_documents", lambda **kwargs: [{"action": "inserted"}])

    result = cli._handle_index()

    assert "Skipped: 2" in result
    assert "Skipped PDFs sem texto: 2" in result
    assert "Proximo passo sugerido: habilitar OCR seletivo" in result


def test_handle_index_reports_audit_summary(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyOutlier:
        def __init__(self, file_path, reasons):
            self.file_path = file_path
            self.reasons = reasons

    class DummyCluster:
        def __init__(self, member_paths):
            self.member_paths = member_paths

    class DummyAuditReport:
        total_documents = 2
        duplicate_count = 1
        duplicate_paths = ["E:/E-book/dup.txt"]
        outliers = [DummyOutlier("E:/E-book/bad.txt", ["no_usable_chunks", "numeric_heavy"])]
        clusters = [DummyCluster(["E:/E-book/a.txt", "E:/E-book/b.txt"])]
        flag_counts = {"no_usable_chunks": 1, "numeric_heavy": 1}

    captured = {"upsert": None, "audit_records": 0}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/a.txt"), Path("E:/E-book/bad.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [
                {"file_path": "E:/E-book/a.txt", "content": "valid content with enough detail for retrieval and indexing quality checks", "metadata": {}},
                {"file_path": "E:/E-book/bad.txt", "content": "12345 67890 12345 67890 12345 67890 12345 67890", "metadata": {}},
            ],
            [],
        ),
    )
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(
        cli,
        "upsert_documents",
        lambda **kwargs: captured.update({"upsert": kwargs}) or [{"action": "inserted"}],
    )
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: captured.update({"audit_records": len(kwargs["records"])}) or len(kwargs["records"]))
    monkeypatch.setattr(cli, "audit_documents", lambda documents: DummyAuditReport())

    result = cli._handle_index()

    assert "Audit duplicates: 1" in result
    assert "Audit outliers: 1" in result
    assert "Audit clusters: 1" in result
    assert "Audit flag no_usable_chunks: 1" in result
    assert "Remediation index_with_review: 1" in result
    assert "Remediation isolate: 1" in result
    assert captured["audit_records"] == 2
    assert [item["file_path"] for item in captured["upsert"]["documents"]] == ["E:/E-book/a.txt"]


def test_handle_index_records_ocr_required_from_loading_errors(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    captured = {"records": []}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/scan.pdf")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [],
            ["Falha ao carregar E:/E-book/scan.pdf: PDF sem texto extraivel: E:/E-book/scan.pdf"],
        ),
    )
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "sync_local_files", lambda db_path, current_file_paths, base_dir=None: 0)
    monkeypatch.setattr(
        cli,
        "record_document_audit_history",
        lambda **kwargs: captured.update({"records": kwargs["records"]}) or len(kwargs["records"]),
    )

    result = cli._handle_index()

    assert "Remediation ocr_required: 1" in result
    assert len(captured["records"]) == 1
    assert captured["records"][0].remediation_action == "ocr_required"
