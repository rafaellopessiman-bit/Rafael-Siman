from __future__ import annotations

from typing import Any, Callable


def _handle_table_compat(
    file_path: str,
    question: str,
    *,
    extract_table_schema: Callable[[str], Any],
    generate_sql_from_question: Callable[[str, Any], str],
    validate_sql: Callable[[str], str],
    execute_validated_sql: Callable[[str, str], Any],
    normalize_tabular_result: Callable[[Any, str], Any],
    summarize_tabular_result: Callable[[Any], str],
    tabular_response_cls: type,
    render_tabular_response: Callable[[Any], str],
    blocked_error_cls: type[BaseException],
    execution_error_cls: type[BaseException],
) -> str:
    table_schema = extract_table_schema(file_path)

    try:
        raw_sql = generate_sql_from_question(question, table_schema)
        validated_sql = validate_sql(raw_sql)
        result = execute_validated_sql(file_path, validated_sql)
        result = normalize_tabular_result(result, validated_sql)

        response = tabular_response_cls(
            status="ok",
            question=question,
            answer=summarize_tabular_result(result),
            table_schema=table_schema,
            result=result,
        )
        return render_tabular_response(response)

    except blocked_error_cls as exc:
        response = tabular_response_cls(
            status="blocked",
            question=question,
            answer="A query foi bloqueada pelo validador de segurança.",
            table_schema=table_schema,
            warnings=[str(exc)],
            errors=[str(exc)],
            result=None,
        )
        return render_tabular_response(response)

    except execution_error_cls as exc:
        response = tabular_response_cls(
            status="error",
            question=question,
            answer="A rota tabular falhou durante validação ou execução.",
            table_schema=table_schema,
            warnings=[str(exc)],
            errors=[str(exc)],
            result=None,
        )
        return render_tabular_response(response)
