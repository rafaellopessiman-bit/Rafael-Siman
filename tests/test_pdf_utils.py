from types import SimpleNamespace

import pytest

from src.exceptions import AtlasLoadError
from src.knowledge import pdf_utils


class _FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class _FakeReader:
    def __init__(self, texts: list[str]) -> None:
        self.pages = [_FakePage(text) for text in texts]
        self.metadata = {"/Title": "Livro", "/Author": "Autor"}


def test_extract_pdf_text_uses_embedded_text_when_available(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_utils, "PdfReader", lambda _path: _FakeReader(["pagina 1", "pagina 2"]))

    text, metadata = pdf_utils.extract_pdf_text(tmp_path / "book.pdf")

    assert "[Pagina 1]" in text
    assert metadata["title"] == "Livro"
    assert metadata["author"] == "Autor"
    assert metadata["page_count"] == 2


def test_extract_pdf_text_can_fallback_to_ocr(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_utils, "PdfReader", lambda _path: _FakeReader(["", ""]))
    monkeypatch.setattr(pdf_utils, "_extract_pdf_text_with_ocr", lambda path, ocr_command, ocr_language: "texto via ocr")

    text, metadata = pdf_utils.extract_pdf_text(
        tmp_path / "book.pdf",
        ocr_enabled=True,
        ocr_command="ocrmypdf",
        ocr_language="por+eng",
    )

    assert text == "texto via ocr"
    assert metadata["ocr_applied"] is True
    assert metadata["ocr_language"] == "por+eng"


def test_extract_pdf_text_raises_when_pdf_has_no_text_and_ocr_is_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_utils, "PdfReader", lambda _path: _FakeReader(["", ""]))

    with pytest.raises(AtlasLoadError, match="PDF sem texto extraivel"):
        pdf_utils.extract_pdf_text(tmp_path / "book.pdf")


def test_extract_pdf_text_with_ocr_requires_external_command(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_utils.shutil, "which", lambda _name: None)

    with pytest.raises(AtlasLoadError, match="OCR para PDF indisponivel"):
        pdf_utils._extract_pdf_text_with_ocr(tmp_path / "book.pdf", "ocrmypdf", "eng")


def test_extract_pdf_text_with_ocr_reads_sidecar_output(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_utils.shutil, "which", lambda _name: "C:/bin/ocrmypdf.exe")

    def _fake_run(command, capture_output, text, check):
        sidecar_index = command.index("--sidecar") + 1
        sidecar_path = command[sidecar_index]
        with open(sidecar_path, "w", encoding="utf-8") as file:
            file.write("texto ocr")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(pdf_utils.subprocess, "run", _fake_run)

    text = pdf_utils._extract_pdf_text_with_ocr(tmp_path / "book.pdf", "ocrmypdf", "eng")

    assert text == "texto ocr"
