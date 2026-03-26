from __future__ import annotations

import sqlite3
from pathlib import Path

from src.storage.document_store import (
    DocumentAuditHistoryRecord,
    DocumentStore,
    ScheduleRunRecord,
)
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
        "Primeiro bloco do relatorio com informacoes detalhadas sobre o projeto atlas local e seus recursos.\n\n"
        "Segundo bloco com texto suficiente para virar outro chunk conceitual e trazer mais detalhes tecnicos importantes.\n\n"
        "Terceiro bloco do relatorio descrevendo as conclusoes finais e proximos passos do projeto atlas local."
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

    first = store.upsert_document(file_path=file_path, content="# Titulo\n\nConteudo inicial com descricao detalhada do projeto atlas local e seus recursos principais de indexacao")
    second = store.upsert_document(file_path=file_path, content="# Titulo\n\nConteudo alterado com descricao atualizada do projeto atlas local e suas funcionalidades mais recentes")

    assert first.action == "inserted"
    assert second.action == "updated"
    assert store.count_documents() == 1

    documents = store.fetch_documents()
    assert len(documents) == 1
    assert "Conteudo alterado" in documents[0]["content"]
    assert "Conteudo inicial" not in documents[0]["content"]


def test_upsert_force_reindexes_existing_document_even_without_content_change(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    file_path = base_dir / "arquivo.md"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)

    first = store.upsert_document(
        file_path=file_path,
        content="# Titulo\n\nConteudo estavel com detalhes suficientes para permanecer igual entre execucoes.",
    )
    second = store.upsert_document(
        file_path=file_path,
        content="# Titulo\n\nConteudo estavel com detalhes suficientes para permanecer igual entre execucoes.",
        force=True,
    )

    assert first.action == "inserted"
    assert second.action == "updated"
    assert store.count_documents() == 1


def test_remove_orphans_deletes_documents_and_chunks_with_cascade(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()

    keep_file = base_dir / "keep.txt"
    orphan_file = base_dir / "orphan.txt"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.upsert_document(file_path=keep_file, content="manter este documento com informacoes detalhadas sobre o projeto atlas local e indexacao")
    store.upsert_document(file_path=orphan_file, content="remover este documento que nao deve permanecer no banco de dados do projeto\n\nem chunks separados com conteudo suficiente para validacao dos filtros de qualidade")

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


def test_upsert_persists_metadata_and_enables_catalog_search(tmp_path: Path) -> None:
    base_dir = tmp_path / "biblioteca"
    base_dir.mkdir()
    file_path = base_dir / "atlas-rag.pdf"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.upsert_document(
        file_path=file_path,
        content="Guia prático de implementação.",
        metadata={
            "title": "Atlas RAG",
            "author": "Equipe Atlas",
            "theme": "ia_aplicada",
            "stack": ["python", "mongodb", "rag"],
            "concepts": ["agents", "vector_search"],
            "page_count": 180,
        },
    )

    documents = store.fetch_documents()
    assert documents[0]["metadata"]["theme"] == "ia_aplicada"
    assert documents[0]["file_extension"] == ".pdf"
    assert "Tema: ia_aplicada" in documents[0]["catalog_text"]

    matches = store.search_chunks_by_text_fts("mongodb rag", limit=5)
    assert matches
    assert matches[0]["file_path"] == normalize_path(file_path, base_dir=base_dir)


def test_record_and_fetch_document_audit_history(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    file_path = base_dir / "bad.txt"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    written = store.record_audit_history(
        [
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T10:00:00+00:00",
                flags=["numeric_heavy", "no_usable_chunks"],
                remediation_action="isolate",
                should_index=False,
                source_command="audit",
            ),
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T11:00:00+00:00",
                flags=["numeric_heavy"],
                remediation_action="index_with_review",
                should_index=True,
                source_command="index",
            ),
        ]
    )

    history = store.fetch_audit_history(file_path)

    assert written == 2
    assert len(history) == 2
    assert history[0]["remediation_action"] == "index_with_review"
    assert history[0]["should_index"] is True
    assert history[1]["flags"] == ["numeric_heavy", "no_usable_chunks"]


def test_fetch_document_audit_history_can_filter_by_source_and_action(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    file_path = base_dir / "doc.txt"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.record_audit_history(
        [
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T10:00:00+00:00",
                flags=["numeric_heavy"],
                remediation_action="index_with_review",
                should_index=True,
                source_command="audit",
            ),
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T11:00:00+00:00",
                flags=["no_usable_chunks"],
                remediation_action="isolate",
                should_index=False,
                source_command="index",
            ),
        ]
    )

    filtered = store.fetch_audit_history(
        file_path=file_path,
        source_command="audit",
        remediation_action="index_with_review",
    )

    assert len(filtered) == 1
    assert filtered[0]["source_command"] == "audit"
    assert filtered[0]["remediation_action"] == "index_with_review"


def test_fetch_document_audit_history_supports_offset_and_summary(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    file_path = base_dir / "doc.txt"

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.record_audit_history(
        [
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T10:00:00+00:00",
                flags=["numeric_heavy"],
                remediation_action="index_with_review",
                should_index=True,
                source_command="audit",
            ),
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T11:00:00+00:00",
                flags=["no_usable_chunks"],
                remediation_action="isolate",
                should_index=False,
                source_command="index",
            ),
            DocumentAuditHistoryRecord(
                file_path=file_path,
                audit_timestamp="2026-03-25T12:00:00+00:00",
                flags=[],
                remediation_action="index",
                should_index=True,
                source_command="index",
            ),
        ]
    )

    paged = store.fetch_audit_history(file_path=file_path, limit=1, offset=1)
    total_count = store.count_audit_history(file_path=file_path)
    summary = store.summarize_audit_history(file_path=file_path)

    assert len(paged) == 1
    assert paged[0]["remediation_action"] == "isolate"
    assert total_count == 3
    assert summary["action_counts"] == {"index": 1, "index_with_review": 1, "isolate": 1}
    assert summary["latest_decision"]["remediation_action"] == "index"


def test_record_and_summarize_schedule_runs(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)

    first_id = store.record_schedule_run(
        ScheduleRunRecord(
            run_timestamp="2026-03-25T10:00:00+00:00",
            status="ok",
            jobs=["audit", "report"],
            summary={"status": "ok"},
            artifacts={"schedule_summary": "data/processados/schedule/run-1.json"},
        )
    )
    second_id = store.record_schedule_run(
        ScheduleRunRecord(
            run_timestamp="2026-03-25T11:00:00+00:00",
            status="partial",
            jobs=["audit", "evaluate"],
            summary={"status": "partial", "steps": {"evaluate": {"status": "partial"}}},
            artifacts={"schedule_summary": "data/processados/schedule/run-2.json"},
        )
    )
    store.update_schedule_run(
        second_id,
        summary={"status": "partial", "history": {"run_id": second_id}},
        artifacts={"schedule_summary": "data/processados/schedule/run-2.json"},
        status="partial",
    )

    runs = store.fetch_schedule_runs(limit=5)
    trend = store.summarize_schedule_runs(limit=5)

    assert first_id > 0
    assert second_id > first_id
    assert len(runs) == 2
    assert runs[0]["status"] == "partial"
    assert runs[0]["jobs"] == ["audit", "evaluate"]
    assert runs[0]["summary"]["history"]["run_id"] == second_id
    assert trend["runs_total"] == 2
    assert trend["status_counts"] == {"partial": 1, "ok": 1}
    assert trend["latest_run_timestamp"] == "2026-03-25T11:00:00+00:00"

    filtered_count = store.count_schedule_runs(status="partial")
    filtered_runs = store.fetch_schedule_runs(limit=5, offset=0, status="partial")
    filtered_trend = store.summarize_schedule_runs(limit=5, status="partial")

    assert filtered_count == 1
    assert len(filtered_runs) == 1
    assert filtered_runs[0]["status"] == "partial"
    assert filtered_trend["status_counts"] == {"partial": 1}


def test_upsert_and_fetch_watch_snapshot(tmp_path: Path) -> None:
    base_dir = tmp_path / "entrada"
    base_dir.mkdir()
    watch_path = base_dir / "biblioteca"
    watch_path.mkdir()

    store = DocumentStore(db_path=tmp_path / "atlas.db", base_dir=base_dir)
    store.upsert_watch_snapshot(
        watch_path=watch_path,
        snapshot={
            "e:/e-book/doc.txt": (100, 20),
            "e:/e-book/scan.pdf": (200, 30),
        },
    )

    snapshot = store.fetch_watch_snapshot(watch_path)
    assert snapshot == {
        "e:/e-book/doc.txt": (100, 20),
        "e:/e-book/scan.pdf": (200, 30),
    }

    store.upsert_watch_snapshot(
        watch_path=watch_path,
        snapshot={"e:/e-book/doc.txt": (300, 40)},
    )

    updated_snapshot = store.fetch_watch_snapshot(watch_path)
    assert updated_snapshot == {"e:/e-book/doc.txt": (300, 40)}
