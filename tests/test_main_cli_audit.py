import json
from pathlib import Path

import src.main_cli_audit as cli


def test_handle_audit_returns_clean_message_when_loader_finds_no_supported_documents(monkeypatch):
    class DummySettings:
        documents_path = "dados_vazios"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())

    def fake_collect_paths(_path):
        raise cli.AtlasLoadError("Nenhum arquivo textual suportado foi encontrado em: dados_vazios")

    monkeypatch.setattr(cli, "collect_supported_document_paths", fake_collect_paths)

    result = cli._handle_audit()

    assert "=== Atlas Local | Audit ===" in result
    assert "Origem: dados_vazios" in result
    assert "Aviso: Nenhum arquivo textual suportado foi encontrado em: dados_vazios" in result
    assert "Operação abortada. Nenhuma auditoria executada." in result


def test_handle_audit_reports_summary_and_samples(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"

    class DummyOutlier:
        def __init__(self, file_path, reasons):
            self.file_path = file_path
            self.reasons = reasons

    class DummyCluster:
        def __init__(self, member_paths, shared_terms, average_similarity):
            self.member_paths = member_paths
            self.shared_terms = shared_terms
            self.average_similarity = average_similarity

    class DummyAuditReport:
        total_documents = 2
        duplicate_count = 1
        duplicate_paths = []
        outliers = [DummyOutlier("E:/E-book/bad.txt", ["no_usable_chunks", "numeric_heavy"])]
        clusters = [DummyCluster(["E:/E-book/a.txt", "E:/E-book/b.txt"], ["retrieval", "ranking"], 0.71)]
        flag_counts = {"no_usable_chunks": 1, "numeric_heavy": 1}

    captured = {"audit_records": 0}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/a.txt"), Path("E:/E-book/b.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [
                {"file_path": "E:/E-book/a.txt", "content": "conteudo valido", "metadata": {}},
                {"file_path": "E:/E-book/bad.txt", "content": "12345 12345 12345 12345", "metadata": {}},
            ],
            ["Falha ao carregar E:/E-book/scan.pdf: PDF sem texto extraivel: E:/E-book/scan.pdf"],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: captured.update({"audit_records": len(kwargs["records"])}) or len(kwargs["records"]))
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)

    class Args:
        documents_path = "E:/E-book"
        workers = 4
        batch_size = 50
        similarity_threshold = 0.25

    result = cli._handle_audit(Args())

    assert "Origem: E:/E-book" in result
    assert "Workers: 4" in result
    assert "Batch size: 50" in result
    assert "Similarity threshold: 0.25" in result
    assert "PDF OCR: disabled (ocrmypdf, lang=eng)" in result
    assert "Image OCR: disabled (tesseract, lang=eng)" in result
    assert "Duplicates: 1" in result
    assert "Outliers: 1" in result
    assert "Clusters: 1" in result
    assert "Flag no_usable_chunks: 1" in result
    assert "Outlier sample: E:/E-book/bad.txt => no_usable_chunks, numeric_heavy" in result
    assert "Cluster sample: E:/E-book/a.txt; E:/E-book/b.txt => similaridade média 0.710 | termos: retrieval, ranking" in result
    assert "Skipped PDFs sem texto: 1" in result
    assert "Reindex selective: disabled" in result
    assert "Remediation ocr_required: 1" in result
    assert "Remediation index_with_review: 1" in result
    assert "Remediation isolate: 1" in result
    assert captured["audit_records"] == 2


def test_handle_audit_can_render_json_output(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyAuditReport:
        total_documents = 1
        duplicate_count = 1
        duplicate_paths = ["E:/E-book/dup.txt"]
        outliers = []
        clusters = []
        flag_counts = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/dup-a.txt"), Path("E:/E-book/dup-b.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [
                {"file_path": "E:/E-book/dup-a.txt", "content": "conteudo repetido valido", "metadata": {}},
                {"file_path": "E:/E-book/dup-b.txt", "content": "conteudo repetido valido", "metadata": {}},
            ],
            [],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 25
        similarity_threshold = None
        output = "json"
        reindex_selective = False

    result = cli._handle_audit(Args())
    payload = json.loads(result)

    assert payload["status"] == "ok"
    assert payload["audit"]["output"] == "json"
    assert payload["duplicate_paths"] == ["E:/E-book/dup.txt"]
    assert payload["reindex"]["requested"] is False
    assert payload["remediation"]["counts"]["ignore_duplicate"] == 1
    assert payload["remediation"]["ocr_required_paths"] == []


def test_handle_audit_can_trigger_selective_reindex(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyOutlier:
        def __init__(self, file_path, reasons):
            self.file_path = file_path
            self.reasons = reasons

    class DummyAuditReport:
        total_documents = 2
        duplicate_count = 0
        duplicate_paths = []
        outliers = []
        clusters = []
        flag_counts = {}

    captured = {"initialized": [], "upsert": None}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/good.txt"), Path("E:/E-book/bad.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [
                {"file_path": "E:/E-book/good.txt", "content": "bom conteudo", "metadata": {}},
                {"file_path": "E:/E-book/bad.txt", "content": "conteudo ruim", "metadata": {}},
            ],
            [],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: captured["initialized"].append((db_path, base_dir)))
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))
    monkeypatch.setattr(
        cli,
        "upsert_documents",
        lambda db_path, documents, base_dir=None, force=False: captured.update({
            "upsert": {
                "db_path": db_path,
                "documents": documents,
                "base_dir": base_dir,
                "force": force,
            }
        }) or [{"action": "updated"}],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = 2
        batch_size = 50
        similarity_threshold = 0.25
        output = "text"
        reindex_selective = True

    result = cli._handle_audit(Args())

    assert "Reindex selective: enabled (0 candidatos)" in result
    assert "Reindex updated: 0" in result
    assert captured["initialized"] == [("data/ebooks.db", "E:/E-book")]
    assert captured["upsert"] is None


def test_handle_audit_reindexes_only_review_documents(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyCluster:
        def __init__(self, member_paths, shared_terms, average_similarity):
            self.member_paths = member_paths
            self.shared_terms = shared_terms
            self.average_similarity = average_similarity

    class DummyAuditReport:
        total_documents = 2
        duplicate_count = 0
        duplicate_paths = []
        outliers = []
        clusters = [DummyCluster(["E:/E-book/a.txt", "E:/E-book/b.txt"], ["retrieval"], 0.66)]
        flag_counts = {}

    captured = {"upsert": None}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/a.txt"), Path("E:/E-book/b.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [
                {"file_path": "E:/E-book/a.txt", "content": "conteudo a", "metadata": {}},
                {"file_path": "E:/E-book/b.txt", "content": "conteudo b", "metadata": {}},
            ],
            [],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))
    monkeypatch.setattr(
        cli,
        "upsert_documents",
        lambda db_path, documents, base_dir=None, force=False: captured.update({
            "upsert": {"documents": documents, "force": force}
        }) or [{"action": "updated"}, {"action": "updated"}],
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 50
        similarity_threshold = 0.25
        output = "text"
        reindex_selective = True

    result = cli._handle_audit(Args())

    assert "Reindex selective: enabled (2 candidatos)" in result
    assert captured["upsert"]["force"] is True
    assert len(captured["upsert"]["documents"]) == 2


def test_handle_audit_applies_isolate_flags_override(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        remediation_isolate_flags = ("numeric_heavy",)

    class DummyOutlier:
        def __init__(self, file_path, reasons):
            self.file_path = file_path
            self.reasons = reasons

    class DummyAuditReport:
        total_documents = 1
        duplicate_count = 0
        duplicate_paths = []
        outliers = [DummyOutlier("E:/E-book/bad.txt", ["numeric_heavy"])]
        clusters = []
        flag_counts = {"numeric_heavy": 1}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/bad.txt")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: (
            [{"file_path": "E:/E-book/bad.txt", "content": "12345 12345", "metadata": {}}],
            [],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 20
        similarity_threshold = None
        output = "json"
        reindex_selective = False
        isolate_flags = "no_usable_chunks"

    payload = json.loads(cli._handle_audit(Args()))

    assert payload["audit"]["isolate_flags"] == ["no_usable_chunks"]
    assert payload["remediation"]["counts"]["index_with_review"] == 1


def test_handle_audit_passes_pdf_ocr_options_to_loader(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

    class DummyAuditReport:
        total_documents = 1
        duplicate_count = 0
        duplicate_paths = []
        outliers = []
        clusters = []
        flag_counts = {}

    captured = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "collect_supported_document_paths", lambda path: [Path("E:/E-book/livro.pdf")])
    monkeypatch.setattr(
        cli,
        "load_document_batch_with_report",
        lambda file_paths, max_workers=None, **kwargs: captured.update({"loader_kwargs": kwargs}) or (
            [{"file_path": "E:/E-book/livro.pdf", "content": "conteudo OCR", "metadata": {}}],
            [],
        ),
    )
    monkeypatch.setattr(cli, "audit_documents", lambda documents, similarity_threshold=None: DummyAuditReport())
    monkeypatch.setattr(cli, "initialize_database", lambda db_path, base_dir=None: None)
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = 2
        batch_size = 10
        enable_pdf_ocr = True
        pdf_ocr_command = "ocrmypdf-custom"
        pdf_ocr_language = "por+eng"
        enable_image_ocr = True
        image_ocr_command = "tesseract-custom"
        image_ocr_language = "por"
        similarity_threshold = None
        output = "text"
        reindex_selective = False

    result = cli._handle_audit(Args())

    assert "PDF OCR: enabled (ocrmypdf-custom, lang=por+eng)" in result
    assert "Image OCR: enabled (tesseract-custom, lang=por)" in result
    assert captured["loader_kwargs"]["pdf_ocr_enabled"] is True
    assert captured["loader_kwargs"]["pdf_ocr_command"] == "ocrmypdf-custom"
    assert captured["loader_kwargs"]["pdf_ocr_language"] == "por+eng"
    assert captured["loader_kwargs"]["image_ocr_enabled"] is True
    assert captured["loader_kwargs"]["image_ocr_command"] == "tesseract-custom"
    assert captured["loader_kwargs"]["image_ocr_language"] == "por"


def test_handle_audit_reports_ocr_required_paths_in_json(monkeypatch):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"

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
    monkeypatch.setattr(cli, "record_document_audit_history", lambda **kwargs: len(kwargs["records"]))

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        workers = None
        batch_size = 10
        similarity_threshold = None
        output = "json"
        reindex_selective = False

    payload = json.loads(cli._handle_audit(Args()))

    assert payload["remediation"]["counts"]["ocr_required"] == 1
    assert payload["remediation"]["ocr_required_paths"] == ["E:/E-book/scan.pdf"]
