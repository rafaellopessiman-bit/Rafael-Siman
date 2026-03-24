import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from typing import Any
from src.core.config import get_settings
from src.core.metrics import profile_operation
from src.core.llm_client import generate_fast_completion
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
from src.knowledge.loader import load_documents
from src.knowledge.retriever import retrieve_documents
from src.planner.planner import generate_plan
from src.storage.document_store import fetch_all_documents
from src.tabular.executor import execute_validated_sql
from src.tabular.schema_extractor import extract_table_schema
from src.tabular.sql_generator import generate_sql_from_question
from src.tabular.sql_validator import validate_sql
from src.main_tabular_compat import _handle_table_compat
from src.main_cli_parser import build_parser as _build_parser
from src.main_cli_index import _handle_index


def build_parser() -> argparse.ArgumentParser:
    return _build_parser()



def handle_index() -> str:
    return _handle_index()



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


def _load_knowledge_documents():
    settings = get_settings()
    db_path = _resolve_database_path(settings)
    docs_path = getattr(settings, "documents_path", "data/entrada")

    indexed_documents = fetch_all_documents(db_path=db_path, base_dir=docs_path)

    if indexed_documents:
        return indexed_documents

    return load_documents(docs_path)


def _has_sufficient_evidence(question: str, positive_matches: list) -> bool:
    if not positive_matches:
        return False
    return max(float(doc.get("score", 0)) for doc in positive_matches) >= 1.0


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


def handle_ask(question: str) -> str:
    with profile_operation("ask"):
        settings = get_settings()
        documents = _load_knowledge_documents()
        ranked_documents = retrieve_documents(question, documents, settings.top_k)

        positive_matches = [document for document in ranked_documents if document["score"] > 0]

        if not positive_matches or not _has_sufficient_evidence(question, positive_matches):
            response = KnowledgeResponse(
                status="insufficient_context",
                answer="Não encontrei evidência suficiente nos documentos locais para responder com segurança.",
                warnings=["Cobertura de evidência insuficiente para a pergunta informada."],
                sources=[],
            )
            return render_knowledge_response(response)

        prompt = build_knowledge_prompt(question, positive_matches)
        answer = generate_fast_completion(prompt, temperature=0.0)
        sources = [_to_source_document(document) for document in positive_matches]

        response = KnowledgeResponse(
            status="ok",
            answer=answer,
            sources=sources,
        )
        return render_knowledge_response(response)

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


# =========================================================
# Compatibility imports from main_compat
# =========================================================


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "index":
        print(handle_index())
        return 0

    if args.command == "ask":
        print(handle_ask(" ".join(args.question)))
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

