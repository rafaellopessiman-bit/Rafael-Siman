from __future__ import annotations

import sqlite3
from pathlib import Path

from src.storage.document_store import DocumentStore
from src.storage.path_utils import normalize_path


def test_initialize_database_creates_sqlite_file_and_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "atlas_local.sqlite3"
    store = DocumentStore(db_path=db_path, base_dir=tmp_path)

    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert "documents" in tables
    assert "chunks" in tables
    assert store.count_documents() == 0
    assert store.count_chunks() == 0


def test_upsert_and_fetch_documents_with_chunks(tmp_path: Path) -> None:
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    file_path = base_dir / "relatorio.txt"

    content = (
        "Primeiro bloco.\n\n"
        "Segundo bloco com texto suficiente para virar outro chunk conceitual.\n\n"
        "Terceiro bloco."
    )

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    result = store.upsert_document(file_path=file_path, content=content)

    assert result.action == "inserted"
    assert result.chunks_written >= 2
    assert store.count_documents() == 1
    assert store.count_chunks() == result.chunks_written

    documents = store.fetch_documents()
    assert len(documents) == 1
    assert documents[0]["file_path"] == normalize_path(file_path, base_dir=base_dir)

    chunks = store.fetch_chunks_with_metadata()
    assert len(chunks) == result.chunks_written
    assert all(chunk["file_path"] == documents[0]["file_path"] for chunk in chunks)


def test_upsert_updates_existing_document_without_duplication(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    file_path = base_dir / "arquivo.md"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)

    first = store.upsert_document(file_path=file_path, content="# Titulo\n\nConteudo inicial")
    second = store.upsert_document(file_path=file_path, content="# Titulo\n\nConteudo alterado")

    assert first.action == "inserted"
    assert second.action == "updated"
    assert store.count_documents() == 1

    documents = store.fetch_documents()
    assert len(documents) == 1
    assert "Conteudo alterado" in documents[0]["content"]
    assert "Conteudo inicial" not in documents[0]["content"]


def test_remove_orphans_deletes_documents_and_chunks_with_cascade(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()

    keep_file = base_dir / "keep.txt"
    orphan_file = base_dir / "orphan.txt"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.upsert_document(file_path=keep_file, content="manter")
    store.upsert_document(file_path=orphan_file, content="remover\n\nem chunks")

    assert store.count_documents() == 2
    assert store.count_chunks() >= 2

    removed = store.remove_orphans([keep_file])

    assert removed == 1
    assert store.count_documents() == 1

    remaining_docs = store.fetch_documents()
    assert remaining_docs[0]["file_path"] == normalize_path(keep_file, base_dir=base_dir)

    remaining_chunks = store.fetch_chunks_with_metadata()
    assert all(chunk["file_path"] == remaining_docs[0]["file_path"] for chunk in remaining_chunks)


def test_normalize_path_is_stable_for_relative_and_absolute_forms(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    nested = base_dir / "SubPasta"
    nested.mkdir(parents=True)

    file_path = nested / "Arquivo.TXT"

    normalized_from_absolute = normalize_path(file_path, base_dir=base_dir)
    normalized_from_relative = normalize_path(file_path.relative_to(base_dir), base_dir=base_dir)

    assert normalized_from_absolute == normalized_from_relative
    assert "\\" not in normalized_from_absolute


def test_index_directory_reads_files_syncs_orphans_and_populates_chunks(tmp_path: Path) -> None:
    documents_dir = tmp_path / "entrada"
    documents_dir.mkdir()

    (documents_dir / "a.txt").write_text("alpha\n\nbeta", encoding="utf-8")
    (documents_dir / "b.md").write_text("# Titulo\n\nconteudo", encoding="utf-8")

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=documents_dir)
    first_stats = store.index_directory(documents_dir)

    assert first_stats["documents_seen"] == 2
    assert store.count_documents() == 2
    assert store.count_chunks() >= 2

    (documents_dir / "b.md").unlink()
    second_stats = store.index_directory(documents_dir)

    assert second_stats["documents_seen"] == 1
    assert second_stats["documents_removed"] == 1
    assert store.count_documents() == 1
