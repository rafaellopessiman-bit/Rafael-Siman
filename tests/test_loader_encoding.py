from src.knowledge.loader import _read_plain_text


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
