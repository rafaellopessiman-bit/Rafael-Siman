from __future__ import annotations

from pathlib import Path

from src.knowledge import (
    build_answer_context,
    load_knowledge_documents,
    retrieve_relevant_documents,
)
from src.storage.document_store import DocumentStore


def test_load_knowledge_documents_prefers_sqlite_chunks(tmp_path: Path) -> None:
    input_dir = tmp_path / "entrada"
    input_dir.mkdir()

    file_path = input_dir / "nota.txt"
    file_path.write_text("conteudo do disco", encoding="utf-8")

    db_path = tmp_path / "atlas.db"
    store = DocumentStore(db_path=db_path, base_dir=input_dir)
    store.upsert_document(file_path=file_path, content="conteudo indexado no sqlite")

    file_path.write_text("conteudo alterado no disco depois do index", encoding="utf-8")

    documents = load_knowledge_documents(
        input_dir=input_dir,
        db_path=db_path,
        base_dir=input_dir,
    )

    assert len(documents) == 1
    assert documents[0]["retrieval_source"] == "sqlite"
    assert "indexado no sqlite" in documents[0]["content"]
    assert "alterado no disco" not in documents[0]["content"]


def test_load_knowledge_documents_falls_back_to_disk_when_db_is_empty(tmp_path: Path) -> None:
    input_dir = tmp_path / "entrada"
    input_dir.mkdir()

    file_path = input_dir / "manual.md"
    file_path.write_text("# Guia\n\nProcesso local", encoding="utf-8")

    db_path = tmp_path / "vazio.db"

    documents = load_knowledge_documents(
        input_dir=input_dir,
        db_path=db_path,
        base_dir=input_dir,
    )

    assert len(documents) == 1
    assert documents[0]["retrieval_source"] == "disk"
    assert "Processo local" in documents[0]["content"]


def test_retrieve_relevant_documents_uses_sqlite_chunks_as_primary_source(tmp_path: Path) -> None:
    input_dir = tmp_path / "entrada"
    input_dir.mkdir()

    file_path = input_dir / "config.txt"
    indexed_content = "Cliente: Atlas\n\nPrioridade: alta\n\nProjeto local"
    file_path.write_text(indexed_content, encoding="utf-8")

    db_path = tmp_path / "atlas.db"
    store = DocumentStore(db_path=db_path, base_dir=input_dir)
    store.index_directory(input_dir)

    file_path.write_text("conteudo irrelevante no disco", encoding="utf-8")

    documents = retrieve_relevant_documents(
        query="cliente prioridade alta",
        input_dir=input_dir,
        db_path=db_path,
        base_dir=input_dir,
        top_k=3,
    )

    assert len(documents) >= 1
    assert documents[0]["retrieval_source"] == "sqlite"
    assert documents[0]["score"] > 0
    assert any("Prioridade: alta" in chunk for chunk in documents[0]["matched_chunks"])


def test_retrieve_relevant_documents_supports_csv_from_sqlite_index(tmp_path: Path) -> None:
    input_dir = tmp_path / "entrada"
    input_dir.mkdir()

    csv_path = input_dir / "dados.csv"
    csv_path.write_text(
        "produto,prioridade,cliente\ncaneta,alta,Atlas\nlapis,baixa,Outro\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "atlas.db"
    store = DocumentStore(db_path=db_path, base_dir=input_dir)
    stats = store.index_directory(input_dir)

    assert stats["documents_seen"] == 1

    documents = retrieve_relevant_documents(
        query="caneta prioridade alta atlas",
        input_dir=input_dir,
        db_path=db_path,
        base_dir=input_dir,
        top_k=3,
    )

    assert len(documents) == 1
    assert documents[0]["retrieval_source"] == "sqlite"
    assert documents[0]["extension"] == ".csv"
    assert documents[0]["score"] > 0
    assert "caneta" in documents[0]["content"].casefold()


def test_build_answer_context_uses_matched_chunks_first() -> None:
    documents = [
        {
            "file_path": "config.txt",
            "content": "conteudo completo",
            "matched_chunks": ["Cliente: Atlas", "Prioridade: alta"],
        }
    ]

    context = build_answer_context(documents)

    assert "Arquivo: config.txt" in context
    assert "Cliente: Atlas" in context
    assert "Prioridade: alta" in context
