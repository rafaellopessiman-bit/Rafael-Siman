from __future__ import annotations

from argparse import Namespace
from typing import Any

from src.core.config import get_settings
from src.exceptions import AtlasLoadError
from src.knowledge.corpus_audit import audit_documents
from src.knowledge.corpus_filter import detect_duplicates
from src.knowledge.corpus_remediation import (
    build_document_remediation_plan,
    build_error_remediation_decisions,
    build_remediation_policy,
    summarize_remediation_actions,
)
from src.knowledge.loader import (
    collect_supported_document_paths,
    load_document_batch_with_report,
)
from src.storage.document_store import (
    DocumentAuditHistoryRecord,
    initialize_database,
    record_document_audit_history,
    sync_local_files,
    upsert_documents,
)

DEFAULT_BATCH_SIZE = 200


def _current_timestamp() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(timespec="seconds")


def _resolve_remediation_policy(settings, args: Namespace | None):
    isolate_flags = getattr(args, "isolate_flags", None)
    if isolate_flags is None:
        isolate_flags = getattr(settings, "remediation_isolate_flags", None)
    return build_remediation_policy(isolate_flags)


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _resolve_pdf_ocr_settings(settings, args: Namespace | None) -> dict[str, Any]:
    enabled = bool(getattr(args, "enable_pdf_ocr", False) or getattr(settings, "pdf_ocr_enabled", False))
    command = getattr(args, "pdf_ocr_command", None) or getattr(settings, "pdf_ocr_command", "ocrmypdf")
    language = getattr(args, "pdf_ocr_language", None) or getattr(settings, "pdf_ocr_language", "eng")
    return {
        "enabled": enabled,
        "command": command,
        "language": language,
    }


def _resolve_image_ocr_settings(settings, args: Namespace | None) -> dict[str, Any]:
    enabled = bool(getattr(args, "enable_image_ocr", False) or getattr(settings, "image_ocr_enabled", False))
    command = getattr(args, "image_ocr_command", None) or getattr(settings, "image_ocr_command", "tesseract")
    language = getattr(args, "image_ocr_language", None) or getattr(settings, "image_ocr_language", "eng")
    return {
        "enabled": enabled,
        "command": command,
        "language": language,
    }


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


def _merge_upsert_summaries(target: dict[str, int], batch_summary: dict[str, int]) -> dict[str, int]:
    for key in ("inserted", "updated", "unchanged", "total"):
        target[key] += int(batch_summary.get(key, 0))
    return target


def _summarize_errors(errors: list[str] | None) -> dict[str, int | list[str]]:
    items = list(errors or [])
    lowered = [item.casefold() for item in items]

    pdf_without_text = sum("pdf sem texto extraivel" in item for item in lowered)
    pdf_dependency = sum("suporte a pdf indisponivel" in item for item in lowered)
    image_requires_ocr = sum("imagem requer ocr" in item for item in lowered)
    image_ocr_dependency = sum("ocr para imagem indisponivel" in item for item in lowered)

    return {
        "total": len(items),
        "pdf_without_text": pdf_without_text,
        "pdf_dependency": pdf_dependency,
        "image_requires_ocr": image_requires_ocr,
        "image_ocr_dependency": image_ocr_dependency,
        "samples": items[:3],
    }


def _handle_index(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    max_workers = getattr(args, "workers", None)
    batch_size = getattr(args, "batch_size", None) or DEFAULT_BATCH_SIZE
    remediation_policy = _resolve_remediation_policy(settings, args)
    pdf_ocr = _resolve_pdf_ocr_settings(settings, args)
    image_ocr = _resolve_image_ocr_settings(settings, args)

    try:
        file_paths = collect_supported_document_paths(docs_path)
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
    removed = sync_local_files(db_path=db_path, current_file_paths=file_paths, base_dir=docs_path)

    summary = {"inserted": 0, "updated": 0, "unchanged": 0, "total": 0}
    errors: list[str] = []
    total_duplicates = 0
    audit_duplicate_total = 0
    audit_outlier_total = 0
    audit_cluster_total = 0
    audit_flag_counts: dict[str, int] = {}
    remediation_counts: dict[str, int] = {}

    for start in range(0, len(file_paths), batch_size):
        batch_paths = file_paths[start:start + batch_size]
        batch_documents, batch_errors = load_document_batch_with_report(
            batch_paths,
            max_workers=max_workers,
            pdf_ocr_enabled=pdf_ocr["enabled"],
            pdf_ocr_command=pdf_ocr["command"],
            pdf_ocr_language=pdf_ocr["language"],
            image_ocr_enabled=image_ocr["enabled"],
            image_ocr_command=image_ocr["command"],
            image_ocr_language=image_ocr["language"],
        )
        errors.extend(batch_errors)
        error_decisions = build_error_remediation_decisions(batch_errors)
        for action, count in summarize_remediation_actions(error_decisions).items():
            remediation_counts[action] = remediation_counts.get(action, 0) + int(count)

        if error_decisions:
            record_document_audit_history(
                db_path=db_path,
                base_dir=docs_path,
                records=[
                    DocumentAuditHistoryRecord(
                        file_path=decision.file_path,
                        audit_timestamp=_current_timestamp(),
                        flags=decision.flags,
                        remediation_action=decision.action,
                        should_index=decision.should_index,
                        source_command="index",
                        duplicate_of=decision.duplicate_of,
                    )
                    for decision in error_decisions
                ],
            )

        if not batch_documents:
            continue

        audit_report = audit_documents(batch_documents)
        duplicate_report = detect_duplicates(batch_documents)
        remediation_plan = build_document_remediation_plan(
            batch_documents,
            audit_report,
            duplicate_report=duplicate_report,
            policy=remediation_policy,
        )
        for action, count in summarize_remediation_actions(remediation_plan).items():
            remediation_counts[action] = remediation_counts.get(action, 0) + int(count)

        record_document_audit_history(
            db_path=db_path,
            base_dir=docs_path,
            records=[
                DocumentAuditHistoryRecord(
                    file_path=decision.file_path,
                    audit_timestamp=_current_timestamp(),
                    flags=decision.flags,
                    remediation_action=decision.action,
                    should_index=decision.should_index,
                    source_command="index",
                    duplicate_of=decision.duplicate_of,
                )
                for decision in remediation_plan
            ],
        )

        audit_duplicate_total += audit_report.duplicate_count
        audit_outlier_total += len(audit_report.outliers)
        audit_cluster_total += len(audit_report.clusters)
        for reason, count in audit_report.flag_counts.items():
            audit_flag_counts[reason] = audit_flag_counts.get(reason, 0) + int(count)

        total_duplicates += len(duplicate_report.duplicates)
        allowed_paths = {
            decision.file_path
            for decision in remediation_plan
            if decision.should_index
        }
        batch_documents = [
            document
            for document in duplicate_report.unique_documents
            if str(document.get("file_path", "")) in allowed_paths
        ]

        if not batch_documents:
            continue

        results = upsert_documents(db_path=db_path, documents=batch_documents, base_dir=docs_path)
        _merge_upsert_summaries(summary, _summarize_upsert(results))

    error_summary = _summarize_errors(errors)

    lines = [
        "=== Atlas Local | Index ===",
        f"Banco: {db_path}",
        f"Origem: {docs_path}",
        f"Workers: {max_workers if max_workers is not None else 'auto'}",
        f"Batch size: {batch_size}",
        f"PDF OCR: {'enabled' if pdf_ocr['enabled'] else 'disabled'} ({pdf_ocr['command']}, lang={pdf_ocr['language']})",
        f"Image OCR: {'enabled' if image_ocr['enabled'] else 'disabled'} ({image_ocr['command']}, lang={image_ocr['language']})",
        f"Isolate flags: {', '.join(sorted(remediation_policy.isolate_flags)) if remediation_policy.isolate_flags else 'none'}",
        f"Arquivos detectados: {len(file_paths)}",
        f"Total processado: {summary['total']}",
        f"Inserted: {summary['inserted']}",
        f"Updated: {summary['updated']}",
        f"Unchanged: {summary['unchanged']}",
        f"Skipped: {error_summary['total']}",
        f"Duplicates: {total_duplicates}",
        f"Audit duplicates: {audit_duplicate_total}",
        f"Audit outliers: {audit_outlier_total}",
        f"Audit clusters: {audit_cluster_total}",
        f"Removed: {removed}",
    ]

    for reason in sorted(audit_flag_counts):
        lines.append(f"Audit flag {reason}: {audit_flag_counts[reason]}")

    for action in sorted(remediation_counts):
        lines.append(f"Remediation {action}: {remediation_counts[action]}")

    if error_summary["pdf_without_text"]:
        lines.append(f"Skipped PDFs sem texto: {error_summary['pdf_without_text']}")

    if error_summary["pdf_dependency"]:
        lines.append(f"Skipped por dependencia PDF: {error_summary['pdf_dependency']}")

    if error_summary["image_requires_ocr"]:
        lines.append(f"Skipped imagens aguardando OCR: {error_summary['image_requires_ocr']}")

    if error_summary["image_ocr_dependency"]:
        lines.append(f"Skipped por dependencia de OCR de imagem: {error_summary['image_ocr_dependency']}")

    for sample in error_summary["samples"]:
        lines.append(f"Skip sample: {sample}")

    if error_summary["pdf_without_text"] or error_summary["image_requires_ocr"]:
        lines.append("Proximo passo sugerido: habilitar OCR seletivo para documentos digitalizados ou imagens sem texto extraivel.")

    return "\n".join(lines)
