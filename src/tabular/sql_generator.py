from __future__ import annotations

import importlib
import json
from typing import Any

from src.tabular.schemas import SQLGenerationModel


_llm_client = importlib.import_module("src.core.llm_client")


def _extract_columns_from_schema(table_schema: Any) -> list[str]:
    if table_schema is None:
        return []

    if isinstance(table_schema, dict):
        columns = table_schema.get("columns", [])
        if columns and all(isinstance(col, dict) for col in columns):
            return [str(col.get("name", "")).strip() for col in columns if str(col.get("name", "")).strip()]
        if columns and all(isinstance(col, str) for col in columns):
            return [str(col).strip() for col in columns if str(col).strip()]

    columns = getattr(table_schema, "columns", None)
    if columns:
        if all(isinstance(col, dict) for col in columns):
            return [str(col.get("name", "")).strip() for col in columns if str(col.get("name", "")).strip()]
        names: list[str] = []
        for col in columns:
            name = getattr(col, "name", None)
            if name:
                names.append(str(name).strip())
            elif isinstance(col, str):
                names.append(col.strip())
        return [name for name in names if name]

    return []


def sanitize_sql(sql: str) -> str:
    sql = sql.strip()

    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()

    sql = sql.strip().rstrip(";").strip()
    return sql


def _build_sql_prompt(question: str, table_schema: Any) -> str:
    columns = _extract_columns_from_schema(table_schema)
    columns_text = ", ".join(columns) if columns else "SEM_COLUNAS_IDENTIFICADAS"

    schema_preview = columns
    if isinstance(table_schema, dict):
        schema_preview = table_schema

    return f"""
Você é um gerador de SQL para DuckDB local.

Retorne SOMENTE JSON válido no schema abaixo:

{{
  "sql": "string",
  "referenced_columns": ["string"]
}}

Regras obrigatórias:
- Gere apenas SELECT simples sobre a tabela fixa `dataset`.
- Não use JOIN.
- Não use CTE.
- Não use subquery.
- Não use UNION.
- Não use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, COPY, ATTACH ou PRAGMA.
- Use somente colunas existentes no schema fornecido.
- `referenced_columns` deve listar apenas colunas reais usadas na query.
- Não use markdown, comentários ou explicações.
- Se precisar filtrar texto, use comparação simples compatível com DuckDB.

Colunas disponíveis:
{columns_text}

Schema resumido:
{json.dumps(schema_preview, ensure_ascii=False)}

Pergunta do usuário:
{question}
""".strip()


def generate_sql(question: str, table_schema: Any) -> SQLGenerationModel:
    prompt = _build_sql_prompt(question, table_schema)
    structured = _llm_client.structured_call(prompt, SQLGenerationModel, temperature=0.0)
    structured.sql = sanitize_sql(structured.sql)
    structured.referenced_columns = [str(col).strip() for col in structured.referenced_columns if str(col).strip()]
    return structured


generate_sql_query = generate_sql
generate_structured_sql = generate_sql
build_sql_prompt = _build_sql_prompt


def generate_sql_from_question(question: str, table_schema):
    return generate_sql(question, table_schema).sql
