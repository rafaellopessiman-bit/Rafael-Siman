import pytest

from src.exceptions import AtlasLoadError
from src.knowledge.image_utils import extract_image_text


def test_extract_image_text_requires_ocr(tmp_path):
    file_path = tmp_path / "scan.png"
    file_path.write_bytes(b"img")

    with pytest.raises(AtlasLoadError, match="Imagem requer OCR"):
        extract_image_text(file_path)
