import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from src.exceptions import AtlasLoadError
from src.knowledge.catalog import infer_document_metadata
from src.knowledge.image_utils import extract_image_text
from src.knowledge.office_utils import extract_docx_text, extract_xlsx_text
from src.knowledge.pdf_utils import extract_pdf_text

SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".json", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".docx", ".xlsx"}
EXTENSION_PRIORITY = {
    ".txt": 0,
    ".md": 1,
    ".json": 2,
    ".pdf": 3,
    ".docx": 4,
    ".xlsx": 5,
    ".png": 6,
    ".jpg": 6,
    ".jpeg": 6,
    ".tif": 6,
    ".tiff": 6,
    ".bmp": 6,
}


def collect_supported_document_paths(documents_path: str | Path) -> list[Path]:
    base_path = Path(documents_path)

    if not base_path.exists():
        raise AtlasLoadError(f"Caminho de documentos não encontrado: {base_path}")

    if not base_path.is_dir():
        raise AtlasLoadError(f"O caminho informado não é uma pasta: {base_path}")

    file_paths = sorted(
        (
            path
            for path in base_path.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_TEXT_EXTENSIONS
        ),
        key=lambda path: (
            EXTENSION_PRIORITY.get(path.suffix.lower(), 99),
            path.stat().st_size,
            str(path).lower(),
        ),
    )

    if not file_paths:
        raise AtlasLoadError(
            f"Nenhum arquivo textual suportado foi encontrado em: {base_path}"
        )

    return file_paths


def load_documents(documents_path: str | Path, max_workers: int | None = None) -> list[dict[str, Any]]:
    documents, errors = load_documents_with_report(documents_path, max_workers=max_workers)

    if errors:
        raise AtlasLoadError(errors[0])

    return documents


def load_documents_with_report(
    documents_path: str | Path,
    max_workers: int | None = None,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_command: str = "ocrmypdf",
    pdf_ocr_language: str = "eng",
    image_ocr_enabled: bool = False,
    image_ocr_command: str = "tesseract",
    image_ocr_language: str = "eng",
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Load documents from directory, with optional parallel processing.

    Args:
        documents_path: Path to directory containing documents
        max_workers: Number of threads for parallel loading.
                     If None, uses min(4, cpu_count())

    Returns:
        Tuple with loaded documents and a list of loading errors.
    """
    file_paths = collect_supported_document_paths(documents_path)

    return load_document_batch_with_report(
        file_paths,
        max_workers=max_workers,
        pdf_ocr_enabled=pdf_ocr_enabled,
        pdf_ocr_command=pdf_ocr_command,
        pdf_ocr_language=pdf_ocr_language,
        image_ocr_enabled=image_ocr_enabled,
        image_ocr_command=image_ocr_command,
        image_ocr_language=image_ocr_language,
    )


def load_document_batch_with_report(
    file_paths: list[Path],
    max_workers: int | None = None,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_command: str = "ocrmypdf",
    pdf_ocr_language: str = "eng",
    image_ocr_enabled: bool = False,
    image_ocr_command: str = "tesseract",
    image_ocr_language: str = "eng",
) -> tuple[list[dict[str, Any]], list[str]]:
    if not file_paths:
        return [], []

    # Determine thread count (default: 4 or fewer if CPU count is low)
    if max_workers is None:
        import os
        max_workers = min(4, os.cpu_count() or 1)

    # Parallel loading using ThreadPoolExecutor
    documents: list[dict[str, Any]] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all file reading tasks
        future_to_path = {
            executor.submit(
                _load_single_document,
                file_path,
                pdf_ocr_enabled,
                pdf_ocr_command,
                pdf_ocr_language,
                image_ocr_enabled,
                image_ocr_command,
                image_ocr_language,
            ): file_path
            for file_path in file_paths
        }

        # Collect results as they complete
        for future in as_completed(future_to_path):
            try:
                doc = future.result()
                if doc:
                    documents.append(doc)
            except AtlasLoadError as exc:
                file_path = future_to_path[future]
                errors.append(f"Falha ao carregar {file_path}: {exc}")
            except Exception as exc:
                file_path = future_to_path[future]
                errors.append(f"Falha ao carregar {file_path}: {exc}")

    if not documents:
        if errors:
            raise AtlasLoadError(errors[0])
        return [], []

    # Sort by file path for consistent ordering
    documents.sort(key=lambda d: d["file_path"].lower())

    return documents, errors


def _load_single_document(
    file_path: Path,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_command: str = "ocrmypdf",
    pdf_ocr_language: str = "eng",
    image_ocr_enabled: bool = False,
    image_ocr_command: str = "tesseract",
    image_ocr_language: str = "eng",
) -> dict[str, Any]:
    """Load a single document. Used by parallel loader."""
    content, base_metadata = _read_textual_file(
        file_path,
        pdf_ocr_enabled=pdf_ocr_enabled,
        pdf_ocr_command=pdf_ocr_command,
        pdf_ocr_language=pdf_ocr_language,
        image_ocr_enabled=image_ocr_enabled,
        image_ocr_command=image_ocr_command,
        image_ocr_language=image_ocr_language,
    )
    metadata = infer_document_metadata(file_path=file_path, content=content, base_metadata=base_metadata)
    return {
        "file_name": file_path.name,
        "file_path": str(file_path),
        "content": content,
        "metadata": metadata,
    }


def load_csv_rows(file_path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(file_path)

    if not csv_path.exists():
        raise AtlasLoadError(f"Arquivo CSV não encontrado: {csv_path}")

    if not csv_path.is_file():
        raise AtlasLoadError(f"O caminho informado não é um arquivo CSV: {csv_path}")

    if csv_path.suffix.lower() != ".csv":
        raise AtlasLoadError(f"Extensão inválida para CSV: {csv_path.name}")

    raw_content = csv_path.read_text(encoding="utf-8-sig").strip()
    if not raw_content:
        raise AtlasLoadError(f"Arquivo CSV vazio: {csv_path}")

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            rows = [dict(row) for row in reader]
            fieldnames = reader.fieldnames
    except Exception as exc:
        raise AtlasLoadError(f"Falha ao ler CSV {csv_path}: {exc}") from exc

    if not fieldnames:
        raise AtlasLoadError(f"CSV sem cabeçalho válido: {csv_path}")

    if not rows:
        raise AtlasLoadError(f"CSV sem linhas de dados: {csv_path}")

    return rows


def _read_textual_file(
    file_path: Path,
    pdf_ocr_enabled: bool = False,
    pdf_ocr_command: str = "ocrmypdf",
    pdf_ocr_language: str = "eng",
    image_ocr_enabled: bool = False,
    image_ocr_command: str = "tesseract",
    image_ocr_language: str = "eng",
) -> tuple[str, dict[str, Any]]:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return _read_plain_text(file_path), {}

    if suffix == ".json":
        return _read_json_as_text(file_path), {}

    if suffix == ".pdf":
        return extract_pdf_text(
            file_path,
            ocr_enabled=pdf_ocr_enabled,
            ocr_command=pdf_ocr_command,
            ocr_language=pdf_ocr_language,
        )

    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return extract_image_text(
            file_path,
            ocr_enabled=image_ocr_enabled,
            ocr_command=image_ocr_command,
            ocr_language=image_ocr_language,
        )

    if suffix == ".docx":
        return extract_docx_text(file_path)

    if suffix == ".xlsx":
        return extract_xlsx_text(file_path)

    raise AtlasLoadError(f"Extensão não suportada: {file_path.name}")


def _read_plain_text(file_path):
    last_exc = None

    for _enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return file_path.read_text(encoding=_enc).strip()
        except UnicodeDecodeError as _e:
            last_exc = _e
            continue
        except OSError as exc:
            raise AtlasLoadError(f"Falha ao ler arquivo {file_path}: {exc}") from exc

    raise AtlasLoadError(
        f"Falha ao ler arquivo {file_path}: {last_exc}"
    ) from last_exc

def _read_json_as_text(file_path: Path) -> str:
    try:
        raw_content = file_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        raise AtlasLoadError(f"Falha ao ler JSON {file_path}: {exc}") from exc

    if not raw_content:
        raise AtlasLoadError(f"Arquivo JSON vazio: {file_path}")

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise AtlasLoadError(f"JSON inválido em {file_path}: {exc}") from exc

    return json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
