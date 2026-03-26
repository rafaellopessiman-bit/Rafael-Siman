from __future__ import annotations

import json
import shutil
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

from src.core.config import get_settings
from src.integrations.webhook import build_webhook_payload, send_json_webhook
from src.knowledge.corpus_audit import audit_documents
from src.knowledge.corpus_filter import detect_duplicates
from src.knowledge.corpus_remediation import (
    build_document_remediation_plan,
    build_error_remediation_decisions,
    build_remediation_policy,
    summarize_remediation_actions,
)
from src.knowledge.evaluation import (
    detect_regressions,
    evaluate_retrieval,
    format_report,
    load_eval_queries,
)
from src.knowledge.loader import load_document_batch_with_report
from src.main_cli_audit import _handle_audit
from src.main_cli_index import DEFAULT_BATCH_SIZE
from src.main_cli_report import generate_report_artifact
from src.storage.document_store import (
    DocumentAuditHistoryRecord,
    ScheduleRunRecord,
    fetch_schedule_runs,
    initialize_database,
    record_document_audit_history,
    record_schedule_run,
    summarize_schedule_runs,
    update_schedule_run,
    upsert_documents,
)

DEFAULT_OUTPUT_DIR = Path("data/processados/schedule")


def _current_timestamp() -> str:
    return __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(timespec="seconds")


def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _resolve_output_dir(output_dir: str | None) -> Path:
    return Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR


def _normalize_jobs(raw_jobs: list[str] | tuple[str, ...] | None) -> list[str]:
    items = list(raw_jobs or ["all"])
    if "all" in items:
        return ["audit", "report", "ocr-pending", "evaluate"]
    return items


def _should_notify(summary_status: str, mode: str) -> bool:
    normalized = mode.strip().lower()
    if normalized == "never":
        return False
    if normalized == "always":
        return True
    if normalized == "on-error":
        return summary_status == "error"
    return summary_status in {"partial", "error"}


def _resolve_summary_status(step_results: dict[str, Any]) -> str:
    statuses = [str(item.get("status", "ok")).lower() for item in step_results.values() if isinstance(item, dict)]
    if any(status == "error" for status in statuses):
        return "error"
    if any(status not in {"ok", "skipped"} for status in statuses):
        return "partial"
    return "ok"


def _evaluation_status(regressions: list[str], load_errors: list[str]) -> str:
    if load_errors:
        return "error"
    if regressions:
        return "partial"
    return "ok"


def _is_critical_regression(regressions: list[str]) -> bool:
    aggregate_metrics = (
        "REGRESSAO mrr:",
        "REGRESSAO mean_precision_at_k:",
        "REGRESSAO mean_ndcg_at_k:",
        "REGRESSAO top1_accuracy:",
    )
    return any(str(item).startswith(aggregate_metrics) for item in regressions)


def run_pdf_ocr_batch(
    pdf_paths: list[str],
    ocr_command: str = "ocrmypdf",
    ocr_language: str = "eng",
    in_place: bool = False,
) -> dict[str, Any]:
    if shutil.which(ocr_command) is None:
        return {
            "status": "error",
            "message": f"Comando OCR nao encontrado: {ocr_command}",
            "candidate_count": len(pdf_paths),
            "processed": 0,
            "outputs": [],
            "errors": [f"Comando OCR nao encontrado: {ocr_command}"],
        }

    outputs: list[dict[str, str]] = []
    errors: list[str] = []
    processed = 0

    for pdf_path in pdf_paths:
        path = Path(pdf_path)
        if not path.exists():
            errors.append(f"Arquivo nao encontrado: {path}")
            continue

        output_path = path if in_place else path.with_name(f"{path.stem}.ocr{path.suffix}")
        result = subprocess.run(
            [
                ocr_command,
                "--force-ocr",
                "-l",
                ocr_language,
                str(path),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or result.stdout or "").strip()
            errors.append(f"Falha ao executar OCR em {path}: {stderr or 'erro desconhecido'}")
            continue

        processed += 1
        outputs.append({"input_path": str(path), "output_path": str(output_path)})

    return {
        "status": "ok" if not errors else "partial",
        "candidate_count": len(pdf_paths),
        "processed": processed,
        "outputs": outputs,
        "errors": errors,
    }


def run_reindex_after_ocr(
    file_paths: list[str],
    docs_path: str,
    db_path: str,
    max_workers: int | None = None,
    batch_size: int | None = None,
    isolate_flags: str | None = None,
) -> dict[str, Any]:
    candidates = [str(path) for path in file_paths if str(path)]
    if not candidates:
        return {
            "status": "skipped",
            "candidate_count": 0,
            "processed": 0,
            "indexed": 0,
            "errors": [],
            "remediation_counts": {},
        }

    initialize_database(db_path=db_path, base_dir=docs_path)
    remediation_policy = build_remediation_policy(isolate_flags)
    effective_batch_size = batch_size or DEFAULT_BATCH_SIZE
    processed = 0
    indexed = 0
    errors: list[str] = []
    remediation_counts: dict[str, int] = {}

    def _record_history(decisions, audit_timestamp: str) -> None:
        if not decisions:
            return
        record_document_audit_history(
            db_path=db_path,
            base_dir=docs_path,
            records=[
                DocumentAuditHistoryRecord(
                    file_path=decision.file_path,
                    audit_timestamp=audit_timestamp,
                    flags=decision.flags,
                    remediation_action=decision.action,
                    should_index=decision.should_index,
                    source_command="index",
                    duplicate_of=decision.duplicate_of,
                )
                for decision in decisions
            ],
        )

    for start in range(0, len(candidates), effective_batch_size):
        batch_paths = candidates[start:start + effective_batch_size]
        batch_documents, batch_errors = load_document_batch_with_report(batch_paths, max_workers=max_workers)
        errors.extend(batch_errors)

        error_decisions = build_error_remediation_decisions(batch_errors)
        for action, count in summarize_remediation_actions(error_decisions).items():
            remediation_counts[action] = remediation_counts.get(action, 0) + int(count)
        _record_history(error_decisions, _current_timestamp())

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
        _record_history(remediation_plan, _current_timestamp())

        allowed_paths = {decision.file_path for decision in remediation_plan if decision.should_index}
        ready_documents = [
            document
            for document in duplicate_report.unique_documents
            if str(document.get("file_path", "")) in allowed_paths
        ]
        processed += len(batch_documents)

        if not ready_documents:
            continue

        results = upsert_documents(db_path=db_path, documents=ready_documents, base_dir=docs_path)
        indexed += len(results) if isinstance(results, list) else len(ready_documents)

    return {
        "status": "ok" if not errors else "partial",
        "candidate_count": len(candidates),
        "processed": processed,
        "indexed": indexed,
        "errors": errors,
        "remediation_counts": remediation_counts,
    }


def _handle_schedule(args: Namespace | None = None) -> str:
    settings = get_settings()
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    output_dir = _resolve_output_dir(getattr(args, "output_dir", None))
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _current_timestamp().replace(":", "-")
    jobs = _normalize_jobs(getattr(args, "jobs", None))

    audit_payload: dict[str, Any] | None = None
    audit_output_path = Path(getattr(args, "audit_output_path", "") or output_dir / f"audit-{timestamp}.json")
    report_output = getattr(args, "report_output", None) or "xlsx"
    report_output_path = getattr(args, "report_output_path", None) or output_dir / f"report-{timestamp}"
    eval_queries_path = getattr(args, "eval_queries_path", None) or getattr(settings, "schedule_eval_queries_path", "data/eval_queries.json")
    eval_baseline_path = getattr(args, "eval_baseline_path", None) or getattr(settings, "schedule_eval_baseline_path", "data/eval_baseline.json")
    eval_top_k = getattr(args, "eval_top_k", None) or getattr(settings, "schedule_eval_top_k", 5)
    pdf_ocr_command = getattr(args, "pdf_ocr_command", None) or getattr(settings, "pdf_ocr_command", "ocrmypdf")
    pdf_ocr_language = getattr(args, "pdf_ocr_language", None) or getattr(settings, "pdf_ocr_language", "eng")
    ocr_in_place = bool(getattr(args, "ocr_in_place", False))
    reindex_after_ocr = bool(getattr(args, "reindex_after_ocr", False))
    notify_webhook_url = getattr(args, "notify_webhook_url", None) or getattr(settings, "schedule_notify_webhook_url", None)
    notify_on = getattr(args, "notify_on", None) or getattr(settings, "schedule_notify_on", "on-issues")
    notify_timeout_seconds = getattr(args, "notify_timeout_seconds", None) or getattr(settings, "schedule_notify_timeout_seconds", 10)
    notify_format = getattr(args, "notify_format", None) or getattr(settings, "schedule_notify_format", "raw")
    step_results: dict[str, Any] = {}
    artifact_paths: dict[str, str] = {}

    lines = [
        "=== Atlas Local | Schedule ===",
        f"Origem: {docs_path}",
        f"Banco: {db_path}",
        f"Jobs: {', '.join(jobs)}",
        f"Output dir: {output_dir}",
    ]

    if "audit" in jobs or "ocr-pending" in jobs:
        audit_args = Namespace(
            documents_path=docs_path,
            database_path=db_path,
            workers=getattr(args, "workers", None),
            batch_size=getattr(args, "batch_size", None),
            similarity_threshold=getattr(args, "similarity_threshold", None),
            output="json",
            reindex_selective=False,
            isolate_flags=getattr(args, "isolate_flags", None),
        )
        audit_result = _handle_audit(audit_args)
        audit_output_path.parent.mkdir(parents=True, exist_ok=True)
        audit_output_path.write_text(audit_result, encoding="utf-8")
        audit_payload = json.loads(audit_result)
        remediation = audit_payload.get("remediation", {}) if isinstance(audit_payload.get("remediation"), dict) else {}
        step_results["audit"] = {
            "status": str(audit_payload.get("status", "ok")),
            "ocr_required_count": len(remediation.get("ocr_required_paths", []) or []),
            "isolated_count": len(remediation.get("isolated_paths", []) or []),
            "review_count": len(remediation.get("review_paths", []) or []),
            "remediation_counts": remediation.get("counts", {}),
        }
        artifact_paths["audit_json"] = str(audit_output_path)
        lines.append(f"Audit JSON: {audit_output_path}")

    if "report" in jobs:
        report_artifact = generate_report_artifact(
            db_path=db_path,
            docs_path=str(docs_path),
            output_format=report_output,
            output_path=report_output_path,
            prefix="report",
        )
        step_results["report"] = {"status": "ok" if report_artifact.get("written") else "partial"}
        if report_artifact.get("written"):
            artifact_paths["report_artifact"] = str(report_artifact["output_path"])
            lines.append(f"Report artifact: {report_artifact['output_path']}")

    if "evaluate" in jobs:
        eval_errors: list[str] = []
        eval_queries = []
        queries_path = Path(str(eval_queries_path))
        baseline_path = Path(str(eval_baseline_path))
        if not queries_path.exists():
            eval_errors.append(f"Arquivo de queries nao encontrado: {queries_path}")
            eval_report = None
            regressions: list[str] = []
        else:
            eval_queries = load_eval_queries(queries_path)
            eval_report = evaluate_retrieval(
                eval_queries,
                db_path=db_path,
                top_k=int(eval_top_k),
                docs_path=str(docs_path),
            )
            regressions = detect_regressions(eval_report, baseline_path)
            if regressions:
                eval_report.regressions = regressions

        eval_payload = {
            "status": _evaluation_status(regressions if not eval_errors else [], eval_errors),
            "queries_path": str(queries_path),
            "baseline_path": str(baseline_path),
            "queries_total": len(eval_queries),
            "top_k": int(eval_top_k),
            "regressions": regressions if not eval_errors else [],
            "errors": eval_errors,
        }
        if eval_report is not None:
            eval_payload["metrics"] = {
                "mrr": eval_report.mrr,
                "mean_precision_at_k": eval_report.mean_precision_at_k,
                "mean_ndcg_at_k": eval_report.mean_ndcg_at_k,
                "top1_accuracy": eval_report.top1_accuracy,
            }
        eval_payload["critical_regression"] = _is_critical_regression(eval_payload["regressions"])
        step_results["evaluate"] = eval_payload
        eval_summary_path = output_dir / f"evaluate-summary-{timestamp}.json"
        eval_summary_path.write_text(json.dumps(eval_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        artifact_paths["evaluate_summary"] = str(eval_summary_path)
        lines.append(f"Evaluate summary: {eval_summary_path}")
        if eval_report is not None:
            eval_report_path = output_dir / f"evaluate-report-{timestamp}.txt"
            eval_report_path.write_text(format_report(eval_report), encoding="utf-8")
            artifact_paths["evaluate_report"] = str(eval_report_path)
            lines.append(f"Evaluate metrics: MRR={eval_report.mrr:.4f} Top1={eval_report.top1_accuracy:.4f}")
            lines.append(f"Evaluate regressions: {len(regressions)}")
        if eval_errors:
            lines.append(f"Evaluate erros: {len(eval_errors)}")

    if "ocr-pending" in jobs:
        if audit_payload is None:
            raise ValueError("OCR pendente requer payload de auditoria.")

        pdf_paths = [
            path
            for path in audit_payload.get("remediation", {}).get("ocr_required_paths", [])
            if str(path).lower().endswith(".pdf")
        ]
        ocr_summary = run_pdf_ocr_batch(
            pdf_paths=pdf_paths,
            ocr_command=pdf_ocr_command,
            ocr_language=pdf_ocr_language,
            in_place=ocr_in_place,
        )
        step_results["ocr_pending"] = {
            "status": str(ocr_summary.get("status", "ok")),
            "candidate_count": int(ocr_summary.get("candidate_count", 0)),
            "processed": int(ocr_summary.get("processed", 0)),
        }
        ocr_summary_path = output_dir / f"ocr-summary-{timestamp}.json"
        ocr_summary_path.write_text(json.dumps(ocr_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        artifact_paths["ocr_summary"] = str(ocr_summary_path)
        lines.append(f"OCR pending candidatos: {ocr_summary['candidate_count']}")
        lines.append(f"OCR pending processados: {ocr_summary['processed']}")
        lines.append(f"OCR summary: {ocr_summary_path}")
        if ocr_summary.get("errors"):
            lines.append(f"OCR erros: {len(ocr_summary['errors'])}")
        if reindex_after_ocr and ocr_summary.get("processed"):
            reindex_summary = run_reindex_after_ocr(
                file_paths=[item.get("output_path", "") for item in ocr_summary.get("outputs", [])],
                docs_path=str(docs_path),
                db_path=db_path,
                max_workers=getattr(args, "workers", None),
                batch_size=getattr(args, "batch_size", None),
                isolate_flags=getattr(args, "isolate_flags", None),
            )
            step_results["reindex_after_ocr"] = {
                "status": str(reindex_summary.get("status", "ok")),
                "candidate_count": int(reindex_summary.get("candidate_count", 0)),
                "indexed": int(reindex_summary.get("indexed", 0)),
            }
            reindex_summary_path = output_dir / f"reindex-summary-{timestamp}.json"
            reindex_summary_path.write_text(json.dumps(reindex_summary, ensure_ascii=False, indent=2), encoding="utf-8")
            artifact_paths["reindex_summary"] = str(reindex_summary_path)
            lines.append(f"Reindex after OCR candidatos: {reindex_summary['candidate_count']}")
            lines.append(f"Reindex after OCR indexados: {reindex_summary['indexed']}")
            lines.append(f"Reindex summary: {reindex_summary_path}")
            if reindex_summary.get("errors"):
                lines.append(f"Reindex erros: {len(reindex_summary['errors'])}")

    schedule_summary = {
        "status": _resolve_summary_status(step_results),
        "schedule": {
            "generated_at": _current_timestamp(),
            "documents_path": str(docs_path),
            "database_path": db_path,
            "jobs": jobs,
            "output_dir": str(output_dir),
            "ocr_in_place": ocr_in_place,
            "reindex_after_ocr": reindex_after_ocr,
        },
        "steps": step_results,
        "artifacts": artifact_paths,
    }
    exit_code = 0
    evaluate_step = step_results.get("evaluate", {}) if isinstance(step_results.get("evaluate"), dict) else {}
    critical_exit_code = int(getattr(args, "critical_regression_exit_code", 2) or 2)
    if schedule_summary["status"] == "error":
        exit_code = 1
    if evaluate_step.get("critical_regression"):
        exit_code = critical_exit_code
        lines.append(f"Evaluate critical regression: yes (exit_code={critical_exit_code})")
    schedule_summary["exit_code"] = exit_code
    summary_path = output_dir / f"schedule-summary-{timestamp}.json"
    summary_path.write_text(json.dumps(schedule_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    artifact_paths["schedule_summary"] = str(summary_path)
    lines.append(f"Schedule summary: {summary_path}")

    if notify_webhook_url and _should_notify(schedule_summary["status"], str(notify_on)):
        webhook_payload = build_webhook_payload(schedule_summary, format_name=str(notify_format))
        notification_result = send_json_webhook(
            url=str(notify_webhook_url),
            payload=webhook_payload,
            timeout_seconds=int(notify_timeout_seconds),
        )
        schedule_summary["notification"] = {
            "mode": str(notify_on),
            "format": str(notify_format),
            "url": str(notify_webhook_url),
            **notification_result,
        }
        if notification_result.get("status") == "ok":
            lines.append(f"Webhook notify: ok ({notification_result.get('status_code')})")
        else:
            lines.append(f"Webhook notify: error ({notification_result.get('message', 'falha desconhecida')})")
    elif notify_webhook_url:
        lines.append(f"Webhook notify: skipped ({notify_on})")

    run_id = record_schedule_run(
        db_path=db_path,
        base_dir=docs_path,
        record=ScheduleRunRecord(
            run_timestamp=str(schedule_summary["schedule"]["generated_at"]),
            status=str(schedule_summary["status"]),
            jobs=list(jobs),
            summary=schedule_summary,
            artifacts=artifact_paths,
        ),
    )
    trend_summary = summarize_schedule_runs(db_path=db_path, base_dir=docs_path, limit=20)
    recent_runs = fetch_schedule_runs(db_path=db_path, base_dir=docs_path, limit=5)
    schedule_summary["history"] = {
        "run_id": run_id,
        "recent_status_counts": trend_summary.get("status_counts", {}),
        "runs_total": trend_summary.get("runs_total", 0),
        "latest_run_timestamp": trend_summary.get("latest_run_timestamp"),
        "recent_runs": [
            {
                "id": item.get("id"),
                "run_timestamp": item.get("run_timestamp"),
                "status": item.get("status"),
                "jobs": item.get("jobs", []),
            }
            for item in recent_runs
        ],
    }
    update_schedule_run(
        db_path=db_path,
        run_id=run_id,
        summary=schedule_summary,
        artifacts=artifact_paths,
        status=str(schedule_summary["status"]),
        base_dir=docs_path,
    )
    summary_path.write_text(json.dumps(schedule_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines.append(f"Schedule run id: {run_id}")
    if args is not None:
        setattr(args, "_atlas_exit_code", exit_code)

    return "\n".join(lines)
