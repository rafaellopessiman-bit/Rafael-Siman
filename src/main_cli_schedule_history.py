from __future__ import annotations

import json
from argparse import Namespace
from typing import Any

from src.core.config import get_settings
from src.storage.document_store import (
    count_schedule_runs,
    fetch_schedule_runs,
    summarize_schedule_runs,
)

DEFAULT_HISTORY_LIMIT = 20
DEFAULT_OUTPUT_FORMAT = "text"


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _render_text(payload: dict[str, Any]) -> str:
    query = payload["query"]
    summary = payload["summary"]
    lines = [
        "=== Atlas Local | History Schedule ===",
        f"Banco: {query['database_path']}",
        f"Limit: {query['limit']}",
        f"Offset: {query['offset']}",
        f"Filtro status: {query['status'] or 'none'}",
        f"Output: {query['output']}",
        f"Registros: {payload['count']}",
        f"Total filtrado: {payload['total_count']}",
        f"Tendencia recente: {summary['status_counts'] if summary['status_counts'] else '{}'}",
    ]

    if summary.get("latest_run_timestamp"):
        lines.append(f"Ultima execucao: {summary['latest_run_timestamp']}")

    if payload["status"] == "not_found":
        lines.append("Nenhuma execucao de schedule encontrada para os filtros informados.")
        return "\n".join(lines)

    for item in payload["runs"]:
        jobs = ", ".join(item.get("jobs", [])) if item.get("jobs") else "none"
        hist = item.get("summary", {}).get("history", {}) if isinstance(item.get("summary"), dict) else {}
        recent = hist.get("recent_status_counts", {}) if isinstance(hist, dict) else {}
        lines.append(
            f"{item['run_timestamp']} | status={item['status']} | jobs={jobs} | run_id={item['id']} | recente={recent}"
        )

    return "\n".join(lines)


def _render_output(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return _render_text(payload)


def _handle_schedule_history(args: Namespace | None = None) -> str:
    settings = get_settings()
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    limit = getattr(args, "limit", None) or DEFAULT_HISTORY_LIMIT
    offset = getattr(args, "offset", None) or 0
    output_format = getattr(args, "output", None) or DEFAULT_OUTPUT_FORMAT
    status = getattr(args, "status", None)

    total_count = count_schedule_runs(db_path=db_path, status=status)
    runs = fetch_schedule_runs(db_path=db_path, limit=limit, offset=offset, status=status)
    summary = summarize_schedule_runs(db_path=db_path, limit=limit, status=status)

    payload = {
        "status": "ok" if runs else "not_found",
        "query": {
            "database_path": db_path,
            "limit": limit,
            "offset": offset,
            "status": status,
            "output": output_format,
        },
        "count": len(runs),
        "total_count": total_count,
        "summary": summary,
        "runs": runs,
    }
    return _render_output(payload, output_format)
