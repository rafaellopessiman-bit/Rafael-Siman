from __future__ import annotations

from src.core.config import get_settings
from src.exceptions import AtlasLoadError
from src.knowledge.loader import load_documents
from src.storage.document_store import initialize_database, upsert_documents


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _summarize_upsert(results):
    summary = {"inserted": 0, "updated": 0, "unchanged": 0, "total": 0}

    if not isinstance(results, list):
        return summary

    for item in results:
        action = None

        if isinstance(item, dict):
            action = item.get("action")
        else:
            action = getattr(item, "action", None)

        action = str(action).lower() if action is not None else None

        if action in ("inserted", "updated", "unchanged"):
            summary[action] += 1

        summary["total"] += 1

    return summary


def _handle_index() -> str:
    settings = get_settings()
    docs_path = getattr(settings, "documents_path", "data/entrada")
    db_path = _resolve_database_path(settings)

    try:
        documents = load_documents(docs_path)
    except AtlasLoadError as e:
        return "\n".join(
            [
                "=== Atlas Local | Index ===",
                f"Origem: {docs_path}",
                f"Aviso: {e}",
                "Operação abortada. Banco inalterado.",
            ]
        )

    initialize_database(db_path=db_path, base_dir=docs_path)
    results = upsert_documents(db_path=db_path, documents=documents, base_dir=docs_path)

    summary = _summarize_upsert(results)

    return "\n".join(
        [
            "=== Atlas Local | Index ===",
            f"Banco: {db_path}",
            f"Origem: {docs_path}",
            f"Total processado: {summary['total']}",
            f"Inserted: {summary['inserted']}",
            f"Updated: {summary['updated']}",
            f"Unchanged: {summary['unchanged']}",
        ]
    )
