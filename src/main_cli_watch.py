from __future__ import annotations

import time
from argparse import Namespace
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.exceptions import AtlasLoadError
from src.knowledge.corpus_audit import audit_documents
from src.knowledge.corpus_filter import detect_duplicates
from src.knowledge.corpus_remediation import (
    DocumentRemediationDecision,
    build_document_remediation_plan,
    build_error_remediation_decisions,
    build_remediation_policy,
    summarize_remediation_actions,
)
from src.knowledge.corpus_sanitation import sanitize_documents
from src.knowledge.loader import (
    collect_supported_document_paths,
    load_document_batch_with_report,
)
from src.storage.document_store import (
    DocumentAuditHistoryRecord,
    fetch_watch_snapshot,
    initialize_database,
    record_document_audit_history,
    sync_local_files,
    upsert_documents,
    upsert_watch_snapshot,
)
from src.storage.path_utils import normalize_path

DEFAULT_BATCH_SIZE = 200
DEFAULT_WATCH_INTERVAL_SECONDS = 30
WATCH_REMEDIATION_POLICIES = ("manual", "ocr-required", "full-auto")


def _current_timestamp() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(timespec="seconds")


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _resolve_remediation_policy(settings, args: Namespace | None):
    isolate_flags = getattr(args, "isolate_flags", None)
    if isolate_flags is None:
        isolate_flags = getattr(settings, "remediation_isolate_flags", None)
    return build_remediation_policy(isolate_flags)


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


def _resolve_watch_interval(settings, args: Namespace | None) -> int:
    interval = getattr(args, "interval_seconds", None)
    if interval is None:
        interval = getattr(settings, "watch_interval_seconds", DEFAULT_WATCH_INTERVAL_SECONDS)
    return max(int(interval), 1)


def _resolve_watch_policy(settings, args: Namespace | None) -> str:
    policy = getattr(args, "remediation_policy", None) or getattr(settings, "watch_remediation_policy", "full-auto")
    normalized = str(policy).strip().lower()
    if normalized not in WATCH_REMEDIATION_POLICIES:
        return "full-auto"
    return normalized


def _collect_paths_for_watch(docs_path: str) -> tuple[list[Path], str | None]:
    try:
        return collect_supported_document_paths(docs_path), None
    except AtlasLoadError as exc:
        message = str(exc)
        if "Nenhum arquivo textual suportado foi encontrado em:" in message:
            return [], None
        return [], message


def _build_file_signatures(file_paths: list[Path]) -> dict[str, tuple[int, int]]:
    signatures: dict[str, tuple[int, int]] = {}
    for path in file_paths:
        try:
            stat = path.stat()
        except OSError:
            continue
        signatures[normalize_path(path, base_dir=None)] = (int(stat.st_mtime_ns), int(stat.st_size))
    return signatures


def _detect_changed_paths(previous: dict[str, tuple[int, int]], current_paths: list[Path]) -> list[Path]:
    changed: list[Path] = []
    current_signatures = _build_file_signatures(current_paths)
    for path in current_paths:
        normalized_path = normalize_path(path, base_dir=None)
        signature = current_signatures.get(normalized_path)
        if signature is None or previous.get(normalized_path) != signature:
            changed.append(path)
    return changed


def _extract_error_file_path(error: str) -> str | None:
    prefix = "Falha ao carregar "
    if not error.startswith(prefix):
        return None

    try:
        path_part, _ = error[len(prefix):].split(": ", 1)
    except ValueError:
        return None

    return path_part.strip() or None


def _load_batch_safely(file_paths: list[Path], max_workers: int | None, **kwargs: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if not file_paths:
        return [], []

    try:
        return load_document_batch_with_report(file_paths, max_workers=max_workers, **kwargs)
    except AtlasLoadError as exc:
        return [], [str(exc)]


def _record_history(db_path: str, docs_path: str, decisions: list[DocumentRemediationDecision]) -> None:
    if not decisions:
        return

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
                source_command="watch",
                duplicate_of=decision.duplicate_of,
            )
            for decision in decisions
        ],
    )


def _merge_upsert_summary(target: dict[str, int], results: list[Any]) -> None:
    for item in results:
        action = getattr(item, "action", None)
        if action is None and isinstance(item, dict):
            action = item.get("action")
        normalized = str(action).lower() if action is not None else ""
        target["total"] += 1
        if normalized in ("inserted", "updated", "unchanged"):
            target[normalized] += 1


def _retry_ocr_candidates(
    error_decisions: list[DocumentRemediationDecision],
    max_workers: int | None,
    pdf_ocr: dict[str, Any],
    image_ocr: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], set[str]]:
    ocr_paths = [Path(decision.file_path) for decision in error_decisions if decision.action == "ocr_required"]
    retry_documents, retry_errors = _load_batch_safely(
        ocr_paths,
        max_workers=max_workers,
        pdf_ocr_enabled=True,
        pdf_ocr_command=pdf_ocr["command"],
        pdf_ocr_language=pdf_ocr["language"],
        image_ocr_enabled=True,
        image_ocr_command=image_ocr["command"],
        image_ocr_language=image_ocr["language"],
    )
    recovered_paths = {str(document.get("file_path", "")) for document in retry_documents if document.get("file_path")}
    return retry_documents, retry_errors, recovered_paths


def _should_retry_with_ocr(remediation_policy: str) -> bool:
    return remediation_policy in {"ocr-required", "full-auto"}


def _apply_watch_policy(remediation_policy: str, documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if remediation_policy != "full-auto":
        return documents, {"documents": 0, "changed_characters": 0}
    return sanitize_documents(documents)


def _handle_watch(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = str(getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada"))
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    max_workers = getattr(args, "workers", None)
    batch_size = getattr(args, "batch_size", None) or DEFAULT_BATCH_SIZE
    interval_seconds = _resolve_watch_interval(settings, args)
    max_cycles = getattr(args, "max_cycles", None)
    remediation_policy = _resolve_watch_policy(settings, args)
    policy = _resolve_remediation_policy(settings, args)
    pdf_ocr = _resolve_pdf_ocr_settings(settings, args)
    image_ocr = _resolve_image_ocr_settings(settings, args)

    initialize_database(db_path=db_path, base_dir=docs_path)

    previous_signatures = fetch_watch_snapshot(db_path=db_path, watch_path=docs_path)
    cycles_executed = 0
    cycles_with_changes = 0
    idle_cycles = 0
    changes_detected = 0
    removed_total = 0
    auto_remediated_ocr = 0
    pending_ocr = 0
    errors: list[str] = []
    remediation_counts: dict[str, int] = {}
    sanitation_summary = {"documents": 0, "changed_characters": 0}
    upsert_summary = {"inserted": 0, "updated": 0, "unchanged": 0, "total": 0}
    last_warning: str | None = None

    while True:
        cycles_executed += 1
        current_paths, fatal_error = _collect_paths_for_watch(docs_path)
        if fatal_error:
            last_warning = fatal_error
            break

        removed_total += int(sync_local_files(db_path=db_path, current_file_paths=current_paths, base_dir=docs_path))
        changed_paths = _detect_changed_paths(previous_signatures, current_paths)
        previous_signatures = _build_file_signatures(current_paths)
        upsert_watch_snapshot(db_path=db_path, watch_path=docs_path, snapshot=previous_signatures)

        if not changed_paths:
            idle_cycles += 1
        else:
            cycles_with_changes += 1
            changes_detected += len(changed_paths)

            for start in range(0, len(changed_paths), batch_size):
                batch_paths = changed_paths[start:start + batch_size]
                batch_documents, batch_errors = _load_batch_safely(
                    batch_paths,
                    max_workers=max_workers,
                    pdf_ocr_enabled=pdf_ocr["enabled"],
                    pdf_ocr_command=pdf_ocr["command"],
                    pdf_ocr_language=pdf_ocr["language"],
                    image_ocr_enabled=image_ocr["enabled"],
                    image_ocr_command=image_ocr["command"],
                    image_ocr_language=image_ocr["language"],
                )

                error_decisions = build_error_remediation_decisions(batch_errors)
                recovered_paths: set[str] = set()

                if error_decisions:
                    _record_history(db_path, docs_path, error_decisions)
                    for action, count in summarize_remediation_actions(error_decisions).items():
                        remediation_counts[action] = remediation_counts.get(action, 0) + int(count)

                    if _should_retry_with_ocr(remediation_policy):
                        retry_documents, retry_errors, recovered_paths = _retry_ocr_candidates(
                            error_decisions,
                            max_workers=max_workers,
                            pdf_ocr=pdf_ocr,
                            image_ocr=image_ocr,
                        )
                        if recovered_paths:
                            auto_remediated_ocr += len(recovered_paths)
                            batch_documents.extend(retry_documents)
                        unresolved_original_errors = [
                            error
                            for error in batch_errors
                            if _extract_error_file_path(error) not in recovered_paths
                        ]
                        batch_errors = unresolved_original_errors + list(retry_errors)

                errors.extend(batch_errors)
                pending_ocr += len(
                    [
                        error
                        for error in batch_errors
                        if any(flag == "ocr_required" for flag in (_extract_error_file_path(error),)) is False
                    ]
                )
                pending_ocr = remediation_counts.get("ocr_required", 0) - auto_remediated_ocr
                if pending_ocr < 0:
                    pending_ocr = 0

                if not batch_documents:
                    continue

                batch_documents, sanitation_stats = _apply_watch_policy(remediation_policy, batch_documents)
                sanitation_summary["documents"] += int(sanitation_stats.get("documents", 0))
                sanitation_summary["changed_characters"] += int(sanitation_stats.get("changed_characters", 0))

                audit_report = audit_documents(batch_documents)
                duplicate_report = detect_duplicates(batch_documents)
                remediation_plan = build_document_remediation_plan(
                    batch_documents,
                    audit_report,
                    duplicate_report=duplicate_report,
                    policy=policy,
                )
                _record_history(db_path, docs_path, remediation_plan)
                for action, count in summarize_remediation_actions(remediation_plan).items():
                    remediation_counts[action] = remediation_counts.get(action, 0) + int(count)

                allowed_paths = {decision.file_path for decision in remediation_plan if decision.should_index}
                ready_documents = [
                    document
                    for document in duplicate_report.unique_documents
                    if str(document.get("file_path", "")) in allowed_paths
                ]

                if not ready_documents:
                    continue

                results = upsert_documents(db_path=db_path, documents=ready_documents, base_dir=docs_path)
                _merge_upsert_summary(upsert_summary, results if isinstance(results, list) else [])

        if max_cycles is not None and cycles_executed >= int(max_cycles):
            break

        time.sleep(interval_seconds)

    lines = [
        "=== Atlas Local | Watch ===",
        f"Origem: {docs_path}",
        f"Banco: {db_path}",
        f"Interval seconds: {interval_seconds}",
        f"Max cycles: {max_cycles if max_cycles is not None else 'infinite'}",
        f"Remediation policy: {remediation_policy}",
        f"PDF OCR bootstrap: {'enabled' if pdf_ocr['enabled'] else 'disabled'} ({pdf_ocr['command']}, lang={pdf_ocr['language']})",
        f"Image OCR bootstrap: {'enabled' if image_ocr['enabled'] else 'disabled'} ({image_ocr['command']}, lang={image_ocr['language']})",
        f"Cycles executed: {cycles_executed}",
        f"Cycles with changes: {cycles_with_changes}",
        f"Idle cycles: {idle_cycles}",
        f"Changes detected: {changes_detected}",
        f"Removed: {removed_total}",
        f"Indexed: {upsert_summary['total']}",
        f"Inserted: {upsert_summary['inserted']}",
        f"Updated: {upsert_summary['updated']}",
        f"Unchanged: {upsert_summary['unchanged']}",
        f"Auto-remediated OCR: {auto_remediated_ocr}",
        f"Sanitized documents: {sanitation_summary['documents']}",
        f"Sanitized characters: {sanitation_summary['changed_characters']}",
        f"Pending OCR: {pending_ocr}",
        f"Errors: {len(errors)}",
    ]

    if remediation_policy == "full-auto":
        lines.append(f"Auto-isolated: {remediation_counts.get('isolate', 0)}")
        lines.append(f"Auto-review: {remediation_counts.get('index_with_review', 0)}")

    if policy.isolate_flags:
        lines.append(f"Isolate flags: {', '.join(sorted(policy.isolate_flags))}")

    for action in sorted(remediation_counts):
        lines.append(f"Remediation {action}: {remediation_counts[action]}")

    if last_warning:
        lines.append(f"Aviso: {last_warning}")

    for sample in errors[:3]:
        lines.append(f"Error sample: {sample}")

    return "\n".join(lines)
