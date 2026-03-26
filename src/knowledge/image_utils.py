from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.exceptions import AtlasLoadError


def extract_image_text(
    file_path: str | Path,
    ocr_enabled: bool = False,
    ocr_command: str = "tesseract",
    ocr_language: str = "eng",
) -> tuple[str, dict[str, object]]:
    path = Path(file_path)

    if not ocr_enabled:
        raise AtlasLoadError(f"Imagem requer OCR: {path}")

    if shutil.which(ocr_command) is None:
        raise AtlasLoadError(
            f"OCR para imagem indisponivel. Instale o comando '{ocr_command}' e suas dependencias para habilitar OCR seletivo."
        )

    try:
        result = subprocess.run(
            [ocr_command, str(path), "stdout", "-l", ocr_language],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise AtlasLoadError(f"Falha ao executar OCR na imagem {path}: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise AtlasLoadError(f"Falha ao executar OCR na imagem {path}: {stderr or 'erro desconhecido'}")

    text = (result.stdout or "").strip()
    if not text:
        raise AtlasLoadError(f"OCR executado mas nao produziu texto para a imagem {path}")

    return text, {
        "ocr_applied": True,
        "ocr_language": ocr_language,
        "source_kind": "image",
    }
