from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from src.exceptions import AtlasLoadError

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - coberto por teste indireto de erro
    PdfReader = None


def extract_pdf_text(
    file_path: str | Path,
    ocr_enabled: bool = False,
    ocr_command: str = "ocrmypdf",
    ocr_language: str = "eng",
) -> tuple[str, dict[str, Any]]:
    path = Path(file_path)

    if PdfReader is None:
        raise AtlasLoadError(
            "Suporte a PDF indisponivel. Instale a dependencia 'pypdf' com pip install -r requirements.txt"
        )

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise AtlasLoadError(f"Falha ao abrir PDF {path}: {exc}") from exc

    metadata = getattr(reader, "metadata", None) or {}
    extracted_metadata = {
        "title": _clean_pdf_value(metadata.get("/Title") or metadata.get("Title")),
        "author": _clean_pdf_value(metadata.get("/Author") or metadata.get("Author")),
        "page_count": len(reader.pages),
    }

    pages = _extract_pdf_pages_text(reader=reader, path=path)
    if not pages:
        if not ocr_enabled:
            raise AtlasLoadError(f"PDF sem texto extraivel: {path}")

        ocr_text = _extract_pdf_text_with_ocr(
            path=path,
            ocr_command=ocr_command,
            ocr_language=ocr_language,
        )
        extracted_metadata["ocr_applied"] = True
        extracted_metadata["ocr_language"] = ocr_language
        return ocr_text, {
            key: value for key, value in extracted_metadata.items() if value not in (None, "")
        }

    return "\n\n".join(pages).strip(), {
        key: value for key, value in extracted_metadata.items() if value not in (None, "")
    }


def _extract_pdf_pages_text(reader: Any, path: Path) -> list[str]:
    pages: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = (page.extract_text() or "").strip()
        except Exception as exc:
            raise AtlasLoadError(f"Falha ao extrair texto do PDF {path} na pagina {page_number}: {exc}") from exc

        if page_text:
            pages.append(f"[Pagina {page_number}]\n{page_text}")
    return pages


def _extract_pdf_text_with_ocr(
    path: Path,
    ocr_command: str,
    ocr_language: str,
) -> str:
    if shutil.which(ocr_command) is None:
        raise AtlasLoadError(
            f"OCR para PDF indisponivel. Instale o comando '{ocr_command}' e suas dependencias para habilitar OCR seletivo."
        )

    with tempfile.TemporaryDirectory(prefix="atlas_pdf_ocr_") as temp_dir:
        temp_path = Path(temp_dir)
        sidecar_path = temp_path / "ocr_output.txt"
        output_pdf_path = temp_path / "ocr_output.pdf"

        try:
            result = subprocess.run(
                [
                    ocr_command,
                    "--force-ocr",
                    "--skip-big",
                    "50",
                    "--sidecar",
                    str(sidecar_path),
                    "-l",
                    ocr_language,
                    str(path),
                    str(output_pdf_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise AtlasLoadError(f"Falha ao executar OCR no PDF {path}: {exc}") from exc

        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            raise AtlasLoadError(f"Falha ao executar OCR no PDF {path}: {stderr or 'erro desconhecido'}")

        try:
            text = sidecar_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise AtlasLoadError(f"Falha ao ler o resultado de OCR do PDF {path}: {exc}") from exc

        if not text:
            raise AtlasLoadError(f"OCR executado mas nao produziu texto para o PDF {path}")

        return text


def _clean_pdf_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
