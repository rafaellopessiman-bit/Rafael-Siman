from __future__ import annotations

import json
from argparse import Namespace
from typing import Any

from src.core.config import get_settings
from src.exceptions import AtlasLoadError
from src.knowledge.corpus_audit import audit_documents
from src.knowledge.corpus_remediation import (
    DocumentRemediationDecision,
    RemediationPolicy,
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
    upsert_documents,
)

DEFAULT_BATCH_SIZE = 200
DEFAULT_OUTPUT_FORMAT = "text"


def _current_timestamp() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(timespec="seconds")


def _resolve_remediation_policy(settings, args: Namespace | None) -> RemediationPolicy:
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


def _empty_reindex_summary(requested: bool, db_path: str) -> dict[str, Any]:
    return {
        "requested": requested,
        "database_path": db_path,
        "candidate_count": 0,
        "processed": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "candidate_paths": [],
    }


def _summarize_upsert(results: list[Any]) -> dict[str, int]:
    summary = {"processed": 0, "inserted": 0, "updated": 0, "unchanged": 0}
    for item in results:
        action = getattr(item, "action", None)
        if action is None and isinstance(item, dict):
            action = item.get("action")

        normalized = str(action).lower() if action is not None else ""
        summary["processed"] += 1
        if normalized in ("inserted", "updated", "unchanged"):
            summary[normalized] += 1
    return summary


def _reindex_candidates(
    db_path: str,
    docs_path: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if not candidates:
        return _empty_reindex_summary(True, db_path)

    initialize_database(db_path=db_path, base_dir=docs_path)
    results = upsert_documents(db_path=db_path, documents=candidates, base_dir=docs_path, force=True)
    summary = _summarize_upsert(results)

    return {
        "requested": True,
        "database_path": db_path,
        "candidate_count": len(candidates),
        "processed": summary["processed"],
        "inserted": summary["inserted"],
        "updated": summary["updated"],
        "unchanged": summary["unchanged"],
        "candidate_paths": [str(document.get("file_path", "")) for document in candidates],
    }


def _summarize_remediation(decisions: list[DocumentRemediationDecision]) -> dict[str, Any]:
    counts = summarize_remediation_actions(decisions)
    return {
        "counts": counts,
        "isolated_paths": [decision.file_path for decision in decisions if decision.action == "isolate"],
        "ignored_duplicate_paths": [decision.file_path for decision in decisions if decision.action == "ignore_duplicate"],
        "review_paths": [decision.file_path for decision in decisions if decision.action == "index_with_review"],
        "ocr_required_paths": [decision.file_path for decision in decisions if decision.action == "ocr_required"],
    }


def _render_text(payload: dict[str, Any]) -> str:
    if payload["status"] != "ok":
        return "\n".join(
            [
                "=== Atlas Local | Audit ===",
                f"Origem: {payload['audit']['source_path']}",
                f"Aviso: {payload['message']}",
                "Operação abortada. Nenhuma auditoria executada.",
            ]
        )

    audit = payload["audit"]
    error_summary = payload["errors"]
    reindex = payload["reindex"]
    remediation = payload["remediation"]

    lines = [
        "=== Atlas Local | Audit ===",
        f"Origem: {audit['source_path']}",
        f"Workers: {audit['workers']}",
        f"Batch size: {audit['batch_size']}",
        f"Similarity threshold: {audit['similarity_threshold']}",
        f"PDF OCR: {'enabled' if audit['pdf_ocr_enabled'] else 'disabled'} ({audit['pdf_ocr_command']}, lang={audit['pdf_ocr_language']})",
        f"Image OCR: {'enabled' if audit['image_ocr_enabled'] else 'disabled'} ({audit['image_ocr_command']}, lang={audit['image_ocr_language']})",
        f"Isolate flags: {', '.join(audit['isolate_flags']) if audit['isolate_flags'] else 'none'}",
        f"Output: {audit['output']}",
        f"Arquivos detectados: {audit['files_detected']}",
        f"Documentos auditados: {audit['documents_audited']}",
        f"Duplicates: {audit['duplicates']}",
        f"Outliers: {audit['outliers']}",
        f"Clusters: {audit['clusters']}",
        f"Skipped: {error_summary['total']}",
    ]

    for reason in sorted(audit["flag_counts"]):
        lines.append(f"Flag {reason}: {audit['flag_counts'][reason]}")

    for sample in payload["outliers"][:5]:
        lines.append(f"Outlier sample: {sample['file_path']} => {', '.join(sample['reasons'])}")

    for cluster in payload["clusters"][:3]:
        shared_terms = ", ".join(cluster["shared_terms"]) if cluster["shared_terms"] else "sem termos compartilhados"
        lines.append(
            f"Cluster sample: {'; '.join(cluster['member_paths'])} => similaridade média {cluster['average_similarity']:.3f} | termos: {shared_terms}"
        )

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

    if reindex["requested"]:
        lines.append(f"Reindex selective: enabled ({reindex['candidate_count']} candidatos)")
        lines.append(f"Reindex processed: {reindex['processed']}")
        lines.append(f"Reindex inserted: {reindex['inserted']}")
        lines.append(f"Reindex updated: {reindex['updated']}")
        lines.append(f"Reindex unchanged: {reindex['unchanged']}")
    else:
        lines.append("Reindex selective: disabled")

    for action in sorted(remediation["counts"]):
        lines.append(f"Remediation {action}: {remediation['counts'][action]}")

    if audit["documents_audited"] > 0 and audit["duplicates"] == 0 and audit["outliers"] == 0 and audit["clusters"] == 0:
        lines.append("Resultado: nenhum sinal forte de qualidade ruim foi encontrado no corpus auditado.")

    return "\n".join(lines)


def _render_output(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return _render_text(payload)


def _handle_audit(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    max_workers = getattr(args, "workers", None)
    batch_size = getattr(args, "batch_size", None) or DEFAULT_BATCH_SIZE
    similarity_threshold = getattr(args, "similarity_threshold", None)
    output_format = getattr(args, "output", None) or DEFAULT_OUTPUT_FORMAT
    reindex_selective = bool(getattr(args, "reindex_selective", False))
    remediation_policy = _resolve_remediation_policy(settings, args)
    pdf_ocr = _resolve_pdf_ocr_settings(settings, args)
    image_ocr = _resolve_image_ocr_settings(settings, args)

    try:
        file_paths = collect_supported_document_paths(docs_path)
    except AtlasLoadError as exc:
        payload = {
            "status": "aborted",
            "message": str(exc),
            "audit": {
                "source_path": docs_path,
                "database_path": db_path,
                "workers": max_workers if max_workers is not None else "auto",
                "batch_size": batch_size,
                "similarity_threshold": similarity_threshold if similarity_threshold is not None else "default",
                "pdf_ocr_enabled": pdf_ocr["enabled"],
                "pdf_ocr_command": pdf_ocr["command"],
                "pdf_ocr_language": pdf_ocr["language"],
                "image_ocr_enabled": image_ocr["enabled"],
                "image_ocr_command": image_ocr["command"],
                "image_ocr_language": image_ocr["language"],
                "isolate_flags": sorted(remediation_policy.isolate_flags),
                "output": output_format,
                "files_detected": 0,
                "documents_audited": 0,
                "duplicates": 0,
                "outliers": 0,
                "clusters": 0,
                "flag_counts": {},
            },
            "duplicate_paths": [],
            "outliers": [],
            "clusters": [],
            "errors": _summarize_errors([]),
            "reindex": _empty_reindex_summary(reindex_selective, db_path),
        }
        return _render_output(payload, output_format)

    total_documents = 0
    total_duplicates = 0
    total_outliers = 0
    total_clusters = 0
    flag_counts: dict[str, int] = {}
    duplicate_paths: list[str] = []
    all_outliers: list[dict[str, Any]] = []
    all_clusters: list[dict[str, Any]] = []
    all_decisions: list[DocumentRemediationDecision] = []
    reindex_candidates: list[dict[str, Any]] = []
    errors: list[str] = []

    initialize_database(db_path=db_path, base_dir=docs_path)

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
        if error_decisions:
            all_decisions.extend(error_decisions)
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
                        source_command="audit",
                        duplicate_of=decision.duplicate_of,
                    )
                    for decision in error_decisions
                ],
            )

        if not batch_documents:
            continue

        report = (
            audit_documents(batch_documents, similarity_threshold=similarity_threshold)
            if similarity_threshold is not None
            else audit_documents(batch_documents)
        )
        remediation_plan = build_document_remediation_plan(batch_documents, report, policy=remediation_policy)
        all_decisions.extend(remediation_plan)

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
                    source_command="audit",
                    duplicate_of=decision.duplicate_of,
                )
                for decision in remediation_plan
            ],
        )

        total_documents += report.total_documents
        total_duplicates += report.duplicate_count
        total_outliers += len(report.outliers)
        total_clusters += len(report.clusters)
        duplicate_paths.extend(getattr(report, "duplicate_paths", []))

        for reason, count in report.flag_counts.items():
            flag_counts[reason] = flag_counts.get(reason, 0) + int(count)

        for item in report.outliers:
            all_outliers.append({"file_path": item.file_path, "reasons": list(item.reasons)})

        for cluster in report.clusters:
            all_clusters.append(
                {
                    "member_paths": list(cluster.member_paths),
                    "shared_terms": list(cluster.shared_terms),
                    "average_similarity": cluster.average_similarity,
                }
            )

        if reindex_selective:
            reindex_candidates.extend(
                document
                for document in batch_documents
                if any(
                    decision.file_path == str(document.get("file_path", ""))
                    and decision.action == "index_with_review"
                    for decision in remediation_plan
                )
            )

    error_summary = _summarize_errors(errors)
    deduped_duplicate_paths = sorted({path for path in duplicate_paths if path})
    deduped_reindex_candidates: list[dict[str, Any]] = []
    seen_reindex_paths: set[str] = set()
    for document in reindex_candidates:
        file_path = str(document.get("file_path", ""))
        if not file_path or file_path in seen_reindex_paths:
            continue
        seen_reindex_paths.add(file_path)
        deduped_reindex_candidates.append(document)

    reindex_summary = (
        _reindex_candidates(db_path=db_path, docs_path=docs_path, candidates=deduped_reindex_candidates)
        if reindex_selective
        else _empty_reindex_summary(False, db_path)
    )

    payload = {
        "status": "ok",
        "audit": {
            "source_path": docs_path,
            "database_path": db_path,
            "workers": max_workers if max_workers is not None else "auto",
            "batch_size": batch_size,
            "similarity_threshold": similarity_threshold if similarity_threshold is not None else "default",
            "pdf_ocr_enabled": pdf_ocr["enabled"],
            "pdf_ocr_command": pdf_ocr["command"],
            "pdf_ocr_language": pdf_ocr["language"],
            "image_ocr_enabled": image_ocr["enabled"],
            "image_ocr_command": image_ocr["command"],
            "image_ocr_language": image_ocr["language"],
            "isolate_flags": sorted(remediation_policy.isolate_flags),
            "output": output_format,
            "files_detected": len(file_paths),
            "documents_audited": total_documents,
            "duplicates": total_duplicates,
            "outliers": total_outliers,
            "clusters": total_clusters,
            "flag_counts": dict(sorted(flag_counts.items())),
        },
        "duplicate_paths": deduped_duplicate_paths,
        "outliers": all_outliers,
        "clusters": all_clusters,
        "remediation": _summarize_remediation(all_decisions),
        "errors": error_summary,
        "reindex": reindex_summary,
    }

    return _render_output(payload, output_format)
