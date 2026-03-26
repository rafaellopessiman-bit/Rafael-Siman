from __future__ import annotations

import json
from argparse import Namespace
from typing import Any

from src.core.config import get_settings
from src.storage.document_store import (
    count_document_audit_history,
    fetch_document_audit_history,
    summarize_document_audit_history,
)

DEFAULT_HISTORY_LIMIT = 20
DEFAULT_OUTPUT_FORMAT = "text"


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _render_text(payload: dict[str, Any]) -> str:
    query = payload["query"]
    active_filters = []
    if query["source_command"]:
        active_filters.append(f"source={query['source_command']}")
    if query["remediation_action"]:
        active_filters.append(f"action={query['remediation_action']}")

    lines = [
        "=== Atlas Local | History ===",
        f"Banco: {query['database_path']}",
        f"Documento: {query['file_path']}",
        f"Limit: {query['limit']}",
        f"Offset: {query['offset']}",
        f"Filtros: {', '.join(active_filters) if active_filters else 'none'}",
        f"Output: {query['output']}",
        f"Registros: {payload['count']}",
        f"Total filtrado: {payload['total_count']}",
    ]

    if payload["status"] == "not_found":
        lines.append("Nenhum histórico de qualidade encontrado para o documento informado.")
        return "\n".join(lines)

    summary = payload["summary"]
    if summary["action_counts"]:
        counts = ", ".join(
            f"{action}={summary['action_counts'][action]}"
            for action in sorted(summary["action_counts"])
        )
        lines.append(f"Resumo por action: {counts}")

    latest_decision = summary.get("latest_decision")
    if latest_decision:
        latest_flags = ", ".join(latest_decision["flags"]) if latest_decision["flags"] else "sem flags"
        lines.append(
            "Ultima decisao: "
            f"{latest_decision['audit_timestamp']} | source={latest_decision['source_command']} | "
            f"action={latest_decision['remediation_action']} | should_index={'yes' if latest_decision['should_index'] else 'no'} | "
            f"flags={latest_flags}"
        )

    for item in payload["history"]:
        flags = ", ".join(item["flags"]) if item["flags"] else "sem flags"
        duplicate_suffix = f" | duplicate_of={item['duplicate_of']}" if item.get("duplicate_of") else ""
        lines.append(
            f"{item['audit_timestamp']} | source={item['source_command']} | action={item['remediation_action']} | should_index={'yes' if item['should_index'] else 'no'} | flags={flags}{duplicate_suffix}"
        )

    return "\n".join(lines)


def _render_output(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return _render_text(payload)


def _handle_history(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    file_path = getattr(args, "file_path")
    limit = getattr(args, "limit", None) or DEFAULT_HISTORY_LIMIT
    offset = getattr(args, "offset", None) or 0
    output_format = getattr(args, "output", None) or DEFAULT_OUTPUT_FORMAT
    source_command = getattr(args, "source_command", None)
    remediation_action = getattr(args, "remediation_action", None)

    total_count = count_document_audit_history(
        db_path=db_path,
        file_path=file_path,
        base_dir=docs_path,
        source_command=source_command,
        remediation_action=remediation_action,
    )
    history = fetch_document_audit_history(
        db_path=db_path,
        file_path=file_path,
        base_dir=docs_path,
        limit=limit,
        offset=offset,
        source_command=source_command,
        remediation_action=remediation_action,
    )
    summary = summarize_document_audit_history(
        db_path=db_path,
        file_path=file_path,
        base_dir=docs_path,
        source_command=source_command,
        remediation_action=remediation_action,
    )

    payload = {
        "status": "ok" if history else "not_found",
        "query": {
            "database_path": db_path,
            "documents_path": str(docs_path),
            "file_path": file_path,
            "limit": limit,
            "offset": offset,
            "source_command": source_command,
            "remediation_action": remediation_action,
            "output": output_format,
        },
        "count": len(history),
        "total_count": total_count,
        "summary": summary,
        "history": history,
    }
    return _render_output(payload, output_format)
