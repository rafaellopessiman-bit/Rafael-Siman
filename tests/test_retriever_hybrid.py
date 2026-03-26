from __future__ import annotations

from pathlib import Path

from src.knowledge.retriever import _build_fts_query, _expand_query, _metadata_overlap_bonus, retrieve_documents
from src.storage.document_store import DocumentStore, fetch_all_documents


def test_expand_query_adds_related_terms_for_embeddings_and_mongodb() -> None:
    expanded = _expand_query("mongodb embeddings")

    assert "vector_search" in expanded
    assert "similarity search" in expanded
    assert "transactions" in expanded or "transaction" in expanded

    fts_query = _build_fts_query(expanded)
    assert '"mongodb"' in fts_query
    assert '"vector_search"' in fts_query


def test_retrieve_documents_hybrid_promotes_catalog_concepts_from_sqlite(tmp_path: Path) -> None:
    input_dir = tmp_path / "entrada"
    input_dir.mkdir()

    db_path = tmp_path / "atlas.db"
    store = DocumentStore(db_path=db_path, base_dir=input_dir)

    mongodb_doc = input_dir / "mongodb-notes.pdf"
    store.upsert_document(
        file_path=mongodb_doc,
        content="Use db.transactions.createIndex({ cr_dr: 1 }) para indexar a collection.",
        metadata={
            "theme": "bancos",
            "stack": ["mongodb"],
            "concepts": ["performance"],
        },
    )

    vector_doc = input_dir / "vector-guide.pdf"
    store.upsert_document(
        file_path=vector_doc,
        content="Guia operacional de busca semantica para catálogos locais.",
        metadata={
            "theme": "ia_aplicada",
            "stack": ["rag"],
            "concepts": ["vector_search", "agents"],
        },
    )

    documents = fetch_all_documents(db_path=db_path, base_dir=input_dir)

    mongodb_results = retrieve_documents(
        query="mongodb indexing transactions",
        documents=documents,
        top_k=3,
        db_path=str(db_path),
    )

    assert mongodb_results[0]["file_name"] == "mongodb-notes.pdf"
    assert mongodb_results[0]["score"] > 0
    assert mongodb_results[0].get("matched_chunks")

    vector_results = retrieve_documents(
        query="embeddings agents",
        documents=documents,
        top_k=3,
        db_path=str(db_path),
    )

    assert vector_results[0]["file_name"] == "vector-guide.pdf"
    assert vector_results[0]["score"] > 0


class TestMetadataOverlapBonus:
    """Tests for query-metadata overlap scoring (ratio-based)."""

    def test_theme_overlap_gives_bonus(self):
        doc = {"metadata": {"theme": "bancos", "stack": [], "concepts": []}}
        # "mongodb" is a keyword for theme "bancos" via THEME_RULES; 1/2 terms match
        bonus = _metadata_overlap_bonus(doc, {"mongodb", "indexing"})
        assert bonus > 0.0
        assert bonus <= 1.5  # max weight

    def test_stack_overlap_gives_bonus(self):
        doc = {"metadata": {"theme": "backend", "stack": ["python", "django"], "concepts": []}}
        # 2/2 terms match stack
        bonus = _metadata_overlap_bonus(doc, {"python", "django"})
        assert bonus > 0.0

    def test_concept_overlap_gives_bonus(self):
        doc = {"metadata": {"theme": "ia_aplicada", "stack": [], "concepts": ["embeddings", "vector_search"]}}
        # "embeddings" matches concept, "vector" matches expanded concept
        bonus = _metadata_overlap_bonus(doc, {"embeddings", "vector"})
        assert bonus > 0.0

    def test_no_overlap_gives_zero(self):
        doc = {"metadata": {"theme": "bancos", "stack": ["mongodb"], "concepts": ["performance"]}}
        # none of these query terms appear in metadata
        bonus = _metadata_overlap_bonus(doc, {"python", "django", "web"})
        assert bonus == 0.0

    def test_empty_metadata_gives_zero(self):
        doc = {"metadata": {}}
        bonus = _metadata_overlap_bonus(doc, {"mongodb"})
        assert bonus == 0.0

    def test_empty_query_terms_gives_zero(self):
        doc = {"metadata": {"theme": "bancos", "stack": ["mongodb"]}}
        bonus = _metadata_overlap_bonus(doc, set())
        assert bonus == 0.0

    def test_no_metadata_key_gives_zero(self):
        doc = {}
        bonus = _metadata_overlap_bonus(doc, {"mongodb"})
        assert bonus == 0.0

    def test_higher_overlap_ratio_gives_higher_bonus(self):
        doc = {"metadata": {
            "theme": "bancos",
            "stack": ["mongodb", "python"],
            "concepts": ["performance"],
        }}
        # 1 of 3 terms match
        bonus_low = _metadata_overlap_bonus(doc, {"mongodb", "unrelated1", "unrelated2"})
        # 2 of 2 terms match
        bonus_high = _metadata_overlap_bonus(doc, {"mongodb", "performance"})
        assert bonus_high > bonus_low

    def test_full_overlap_gives_max_bonus(self):
        doc = {"metadata": {"theme": "bancos", "stack": ["mongodb"], "concepts": []}}
        # "mongodb" matches stack AND theme keywords; 1/1 = 100% ratio
        bonus = _metadata_overlap_bonus(doc, {"mongodb"})
        assert bonus == 1.5  # METADATA_BONUS_WEIGHT
