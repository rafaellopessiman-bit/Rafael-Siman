import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import os
from typing import Any

from src.core.config import get_settings
from src.core.llm_client import generate_fast_completion
from src.core.metrics import profile_operation
from src.core.output import (
    render_knowledge_response,
    render_plan_response,
    render_tabular_response,
)
from src.core.prompt_builder import build_knowledge_prompt
from src.core.schemas import KnowledgeResponse, SourceDocument, TabularResponse
from src.exceptions import (
    AtlasBlockedQueryError,
    AtlasExecutionError,
)
from src.knowledge.confidence import assess_confidence
from src.knowledge.evaluation import (
    detect_regressions,
    evaluate_retrieval,
    format_report,
    load_eval_queries,
    save_baseline,
)
from src.knowledge.loader import load_documents
from src.knowledge.retriever import retrieve_documents
from src.knowledge.telemetry import TraceCollector, format_trace_compact
from src.main_cli_audit import _handle_audit
from src.main_cli_history import _handle_history
from src.main_cli_index import _handle_index
from src.main_cli_parser import build_parser as _build_parser
from src.main_cli_report import _handle_report
from src.main_cli_schedule import _handle_schedule
from src.main_cli_schedule_history import _handle_schedule_history
from src.main_cli_watch import _handle_watch
from src.main_tabular_compat import _handle_table_compat
from src.planner.planner import generate_plan
from src.storage.document_store import fetch_all_documents
from src.tabular.executor import execute_validated_sql
from src.tabular.schema_extractor import extract_table_schema
from src.tabular.sql_generator import generate_sql_from_question
from src.tabular.sql_validator import validate_sql


def build_parser() -> argparse.ArgumentParser:
    return _build_parser()



def handle_index(args: argparse.Namespace | None = None) -> str:
    return _handle_index(args)


def handle_audit(args: argparse.Namespace | None = None) -> str:
    return _handle_audit(args)


def handle_history(args: argparse.Namespace | None = None) -> str:
    return _handle_history(args)


def handle_history_schedule(args: argparse.Namespace | None = None) -> str:
    return _handle_schedule_history(args)


def handle_report(args: argparse.Namespace | None = None) -> str:
    return _handle_report(args)


def handle_schedule(args: argparse.Namespace | None = None) -> str:
    return _handle_schedule(args)


def handle_watch(args: argparse.Namespace | None = None) -> str:
    return _handle_watch(args)



def _to_source_document(document):
    file_name = document.get("file_name") or document.get("name") or ""
    file_path = document.get("file_path") or document.get("path") or ""
    score = float(document.get("score", 0))

    content_preview = (
        document.get("content_preview")
        or document.get("preview")
        or document.get("content", "")
    )
    content_preview = str(content_preview)[:220]

    payload = {
        "file_name": file_name,
        "file_path": file_path,
        "score": score,
        "content_preview": content_preview,
    }

    try:
        return SourceDocument(**payload)
    except Exception:
        return payload

# =========================================================
# Compatibility block recovered after main.py refactor
# =========================================================

def _resolve_database_path(settings) -> str:
    return getattr(settings, "database_path", "data/atlas_local.db")


def _load_knowledge_documents(args: argparse.Namespace | None = None):
    settings = get_settings()
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    docs_path = getattr(args, "documents_path", None) or getattr(settings, "documents_path", "data/entrada")

    indexed_documents = fetch_all_documents(db_path=db_path, base_dir=docs_path)

    if indexed_documents:
        return indexed_documents

    return load_documents(docs_path)


def _normalize_tabular_result(result, validated_sql: str):
    if isinstance(result, dict):
        if "sql" not in result:
            return {**result, "sql": validated_sql}
        return result

    if hasattr(result, "sql"):
        return result

    try:
        setattr(result, "sql", validated_sql)
    except Exception:
        pass

    return result


def _summarize_tabular_result(result: Any) -> str:
    def _get(name: str, default=None):
        if isinstance(result, dict):
            return result.get(name, default)
        return getattr(result, name, default)

    row_count = _get("row_count", 0)
    columns = _get("columns", []) or []
    rows = _get("rows", []) or []

    if row_count == 0:
        return "Consulta executada sem linhas retornadas."

    if row_count == 1 and len(columns) == 1 and len(rows) == 1 and len(rows[0]) == 1:
        return f"Valor: {rows[0][0]}"

    return f"Consulta executada com sucesso. Linhas: {row_count}. Colunas: {', '.join(columns)}"


def handle_ask(question: str, args: argparse.Namespace | None = None) -> str:
    with profile_operation("ask"):
        settings = get_settings()
        db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
        debug = getattr(args, "debug", False) or os.environ.get("ATLAS_DEBUG") == "1"
        documents = _load_knowledge_documents(args)

        trace_collector = TraceCollector() if debug else None
        ranked_documents = retrieve_documents(
            question, documents, settings.top_k, db_path=db_path,
            trace_collector=trace_collector,
        )

        positive_matches = [document for document in ranked_documents if document["score"] > 0]

        confidence = assess_confidence(ranked_documents)

        if not confidence.should_answer:
            response = KnowledgeResponse(
                status="insufficient_context",
                answer="Não encontrei evidência suficiente nos documentos locais para responder com segurança.",
                warnings=confidence.warnings,
                sources=[],
            )
            return render_knowledge_response(response)

        prompt = build_knowledge_prompt(question, positive_matches)
        answer = generate_fast_completion(prompt, temperature=0.0)
        sources = [_to_source_document(document) for document in positive_matches]

        warnings = confidence.warnings.copy()
        if confidence.level in ("low", "medium"):
            warnings.insert(0, confidence.explanation)

        response = KnowledgeResponse(
            status="ok",
            answer=answer,
            sources=sources,
            warnings=warnings,
        )
        output = render_knowledge_response(response)

        if trace_collector and trace_collector.trace:
            output += "\n\n" + format_trace_compact(trace_collector.trace)

        return output

def _coerce_plan_result(result):
    from types import SimpleNamespace

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if {"status", "objective", "answer"}.issubset(result.keys()):
            return SimpleNamespace(**result)

        answer = result.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer

        return str(result)

    return result


def handle_plan(objective: str) -> str:
    with profile_operation("plan"):
        result = generate_plan(objective)
        result = _coerce_plan_result(result)

        if isinstance(result, str):
            return result

        return render_plan_response(result)


def handle_table(file_path: str, question: str) -> str:
    with profile_operation("table"):
        return _handle_table_compat(
            file_path,
            question,
            extract_table_schema=extract_table_schema,
            generate_sql_from_question=generate_sql_from_question,
            validate_sql=validate_sql,
            execute_validated_sql=execute_validated_sql,
            normalize_tabular_result=_normalize_tabular_result,
            summarize_tabular_result=_summarize_tabular_result,
            tabular_response_cls=TabularResponse,
            render_tabular_response=render_tabular_response,
            blocked_error_cls=AtlasBlockedQueryError,
            execution_error_cls=AtlasExecutionError,
        )


def handle_evaluate(args: argparse.Namespace | None = None) -> str:
    settings = get_settings()
    db_path = getattr(args, "database_path", None) or _resolve_database_path(settings)
    queries_path = getattr(args, "eval_queries_path", "data/eval_queries.json")
    baseline_path = getattr(args, "baseline_path", "data/eval_baseline.json")
    top_k = getattr(args, "top_k", 5) or 5
    save_bl = getattr(args, "save_baseline", False)

    eval_queries = load_eval_queries(queries_path)
    report = evaluate_retrieval(eval_queries, db_path=db_path, top_k=top_k)

    regressions = detect_regressions(report, baseline_path)
    report.regressions = regressions

    if save_bl:
        save_baseline(report, baseline_path)

    return format_report(report)


# =========================================================
# Compatibility imports from main_compat
# =========================================================


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "index":
        print(handle_index(args))
        return 0

    if args.command == "audit":
        print(handle_audit(args))
        return 0

    if args.command == "history":
        print(handle_history(args))
        return 0

    if args.command == "history-schedule":
        print(handle_history_schedule(args))
        return 0

    if args.command == "report":
        print(handle_report(args))
        return 0

    if args.command == "schedule":
        print(handle_schedule(args))
        return int(getattr(args, "_atlas_exit_code", 0) or 0)

    if args.command == "watch":
        print(handle_watch(args))
        return 0

    if args.command == "evaluate":
        print(handle_evaluate(args))
        return 0

    if args.command == "ask":
        print(handle_ask(" ".join(args.question), args))
        return 0

    if args.command == "plan":
        print(handle_plan(" ".join(args.objective)))
        return 0

    if args.command == "table":
        print(handle_table(args.file_path, " ".join(args.question)))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

