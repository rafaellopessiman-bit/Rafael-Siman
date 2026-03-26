import pytest

from src.exceptions import AtlasLoadError
from src.knowledge.loader import (
    _read_plain_text,
    collect_supported_document_paths,
    load_documents,
    load_documents_with_report,
)


def test_read_plain_text_utf8(tmp_path):
    f = tmp_path / "utf8.txt"
    f.write_bytes("conteúdo".encode("utf-8"))
    assert "conteúdo" in _read_plain_text(f)


def test_read_plain_text_cp1252(tmp_path):
    f = tmp_path / "cp1252.txt"
    f.write_bytes("conteúdo".encode("cp1252"))
    assert "conteúdo" in _read_plain_text(f)


def test_read_plain_text_latin1(tmp_path):
    f = tmp_path / "latin1.txt"
    f.write_bytes("café".encode("latin-1"))
    assert "café" in _read_plain_text(f)


def test_load_documents_supports_pdf_with_metadata(tmp_path, monkeypatch):
    pdf_file = tmp_path / "Clean Architecture - Robert Martin.pdf"
    pdf_file.write_bytes(b"%PDF-stub")

    monkeypatch.setattr(
        "src.knowledge.loader.extract_pdf_text",
        lambda _path, ocr_enabled=False, ocr_command="ocrmypdf", ocr_language="eng": (
            "Domain-driven design and clean architecture for backend systems.",
            {"title": "Clean Architecture", "author": "Robert Martin", "page_count": 320},
        ),
    )

    documents = load_documents(tmp_path)

    assert len(documents) == 1
    assert documents[0]["file_name"].endswith(".pdf")
    assert documents[0]["metadata"]["author"] == "Robert Martin"
    assert documents[0]["metadata"]["theme"] == "arquitetura"
    assert "clean_architecture" in documents[0]["metadata"]["concepts"]


def test_collect_supported_document_paths_filters_supported_extensions(tmp_path):
    (tmp_path / "doc.txt").write_text("a", encoding="utf-8")
    (tmp_path / "doc.pdf").write_bytes(b"%PDF")
    (tmp_path / "skip.docx").write_text("x", encoding="utf-8")
    (tmp_path / "scan.png").write_bytes(b"img")

    paths = collect_supported_document_paths(tmp_path)

    assert [path.name for path in paths] == ["doc.txt", "doc.pdf", "skip.docx", "scan.png"]


def test_load_documents_raises_when_pdf_dependency_is_missing(tmp_path, monkeypatch):
    pdf_file = tmp_path / "Livro.pdf"
    pdf_file.write_bytes(b"%PDF-stub")

    def _raise(_path, ocr_enabled=False, ocr_command="ocrmypdf", ocr_language="eng"):
        raise AtlasLoadError("Suporte a PDF indisponivel.")

    monkeypatch.setattr("src.knowledge.loader.extract_pdf_text", _raise)

    with pytest.raises(AtlasLoadError):
        load_documents(tmp_path)


def test_load_documents_with_report_skips_problematic_pdf_when_other_docs_exist(tmp_path, monkeypatch):
    pdf_file = tmp_path / "Livro.pdf"
    txt_file = tmp_path / "nota.txt"
    pdf_file.write_bytes(b"%PDF-stub")
    txt_file.write_text("conteudo de backend e mongodb", encoding="utf-8")

    def _raise(_path, ocr_enabled=False, ocr_command="ocrmypdf", ocr_language="eng"):
        raise AtlasLoadError("PDF com erro")

    monkeypatch.setattr("src.knowledge.loader.extract_pdf_text", _raise)

    documents, errors = load_documents_with_report(tmp_path)

    assert len(documents) == 1
    assert documents[0]["file_name"] == "nota.txt"
    assert len(errors) == 1
    assert "PDF com erro" in errors[0]


def test_load_documents_with_report_passes_pdf_ocr_options_to_pdf_loader(tmp_path, monkeypatch):
    pdf_file = tmp_path / "Livro.pdf"
    pdf_file.write_bytes(b"%PDF-stub")
    captured = {}

    def _fake_extract(path, ocr_enabled=False, ocr_command="ocrmypdf", ocr_language="eng"):
        captured.update(
            {
                "path": path,
                "ocr_enabled": ocr_enabled,
                "ocr_command": ocr_command,
                "ocr_language": ocr_language,
            }
        )
        return "conteudo OCR", {"page_count": 1, "ocr_applied": True}

    monkeypatch.setattr("src.knowledge.loader.extract_pdf_text", _fake_extract)

    documents, errors = load_documents_with_report(
        tmp_path,
        pdf_ocr_enabled=True,
        pdf_ocr_command="ocrmypdf-custom",
        pdf_ocr_language="por+eng",
    )

    assert len(documents) == 1
    assert errors == []
    assert captured["ocr_enabled"] is True
    assert captured["ocr_command"] == "ocrmypdf-custom"
    assert captured["ocr_language"] == "por+eng"


def test_load_documents_with_report_passes_image_ocr_options_to_image_loader(tmp_path, monkeypatch):
    image_file = tmp_path / "scan.png"
    image_file.write_bytes(b"img")
    captured = {}

    def _fake_extract(path, ocr_enabled=False, ocr_command="tesseract", ocr_language="eng"):
        captured.update(
            {
                "path": path,
                "ocr_enabled": ocr_enabled,
                "ocr_command": ocr_command,
                "ocr_language": ocr_language,
            }
        )
        return "conteudo OCR imagem", {"ocr_applied": True}

    monkeypatch.setattr("src.knowledge.loader.extract_image_text", _fake_extract)

    documents, errors = load_documents_with_report(
        tmp_path,
        image_ocr_enabled=True,
        image_ocr_command="tesseract-custom",
        image_ocr_language="por",
    )

    assert len(documents) == 1
    assert errors == []
    assert captured["ocr_enabled"] is True
    assert captured["ocr_command"] == "tesseract-custom"
    assert captured["ocr_language"] == "por"
