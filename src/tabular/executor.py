from __future__ import annotations

import csv
import importlib
from pathlib import Path
from time import perf_counter
from typing import Any

import duckdb

from src.exceptions import AtlasExecutionError, AtlasValidationError
from src.tabular.sql_generator import generate_sql
from src.tabular.sql_validator import validate_referenced_columns, validate_sql


_llm_client = importlib.import_module("src.core.llm_client")


def _extract_schema_via_module(csv_path: str | Path) -> Any | None:
    try:
        module = importlib.import_module("src.tabular.schema_extractor")
    except Exception:
        return None

    for name in ["extract_schema", "extract_table_schema", "get_table_schema", "infer_schema"]:
        fn = getattr(module, name, None)
        if callable(fn):
            return fn(csv_path)

    return None


def _fallback_schema(csv_path: str | Path) -> dict:
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
    return {
        "columns": [col.strip() for col in header if col.strip()],
        "path": str(csv_path),
    }


def _schema_columns(table_schema: Any) -> list[str]:
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
        names: list[str] = []
        for col in columns:
            if isinstance(col, str):
                names.append(col.strip())
            else:
                name = getattr(col, "name", None)
                if name:
                    names.append(str(name).strip())
        return [name for name in names if name]

    return []


def _load_table_schema(csv_path: str | Path) -> Any:
    schema = _extract_schema_via_module(csv_path)
    if schema is not None:
        return schema
    return _fallback_schema(csv_path)


def execute_sql(csv_path: str | Path, sql: str) -> dict:
    conn = None
    try:
        conn = duckdb.connect(database=":memory:")
        safe_csv_path = Path(csv_path).resolve().as_posix().replace("'", "''")

        try:
            conn.execute(
                f"CREATE VIEW dataset AS SELECT * FROM read_csv_auto('{safe_csv_path}', HEADER=TRUE)"
            )
        except Exception:
            loaded = False
            for sep in [",", ";", "	"]:
                try:
                    conn.execute(
                        f"CREATE VIEW dataset AS SELECT * FROM read_csv('{safe_csv_path}', delim='{sep}', header=true, strict_mode=false, null_padding=true)"
                    )
                    loaded = True
                    break
                except Exception:
                    continue

            if not loaded:
                raise

        cursor = conn.execute(sql)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in (cursor.description or [])]
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except Exception as exc:
        raise AtlasExecutionError(f"Falha ao executar SQL no DuckDB: {exc}") from exc
    finally:
        if conn is not None:
            conn.close()


def _render_answer(result: dict) -> str:
    row_count = int(result.get("row_count", 0))
    columns = result.get("columns", [])

    if row_count == 0:
        return "Consulta executada sem linhas retornadas."

    return f"Consulta executada com sucesso. Linhas: {row_count}. Colunas: {', '.join(columns)}"


def handle_table(csv_path: str | Path, question: str) -> dict:
    started = perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    try:
        model_name = getattr(_llm_client, "MODEL", None) or getattr(_llm_client, "DEFAULT_MODEL", None)
    except Exception:
        model_name = None

    try:
        table_schema = _load_table_schema(csv_path)
        allowed_columns = _schema_columns(table_schema)

        generated = generate_sql(question, table_schema)
        validated_sql = validate_sql(generated.sql)
        canonical_columns = validate_referenced_columns(
            generated.referenced_columns,
            allowed_columns,
            sql_text=validated_sql,
        )

        result = execute_sql(csv_path, validated_sql)
        elapsed_ms = int((perf_counter() - started) * 1000)

        return {
            "route": "tabular",
            "status": "ok",
            "answer": _render_answer(result),
            "sql": validated_sql,
            "referenced_columns": canonical_columns,
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "warnings": warnings,
            "errors": errors,
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }

    except AtlasValidationError as exc:
        errors.append(str(exc))
        elapsed_ms = int((perf_counter() - started) * 1000)
        return {
            "route": "tabular",
            "status": "blocked",
            "answer": None,
            "sql": None,
            "referenced_columns": [],
            "columns": [],
            "rows": [],
            "row_count": 0,
            "warnings": warnings,
            "errors": errors,
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }

    except AtlasExecutionError as exc:
        errors.append(str(exc))
        elapsed_ms = int((perf_counter() - started) * 1000)
        return {
            "route": "tabular",
            "status": "error",
            "answer": None,
            "sql": None,
            "referenced_columns": [],
            "columns": [],
            "rows": [],
            "row_count": 0,
            "warnings": warnings,
            "errors": errors,
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }


run_table = handle_table
query_table = handle_table
execute_table = handle_table


def execute_validated_sql(csv_path: str | Path, sql: str) -> dict:
    validated_sql = validate_sql(sql)
    return execute_sql(csv_path, validated_sql)
