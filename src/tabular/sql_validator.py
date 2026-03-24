from __future__ import annotations

import re
from typing import Iterable


from src.exceptions import AtlasBlockedQueryError, AtlasValidationError


SQL_KEYWORDS = {
    "select", "from", "where", "group", "by", "order", "limit", "asc", "desc",
    "and", "or", "not", "as", "is", "null", "like", "ilike", "in", "between",
    "count", "sum", "avg", "min", "max", "distinct", "dataset", "true", "false"
}

BLOCKED_PATTERNS = [
    r"--",
    r"/\*",
    r"\*/",
    r"\b(insert|update|delete|drop|alter|create|attach|copy|pragma|vacuum|truncate|merge|replace)\b",
    r"\bjoin\b",
    r"\bunion\b",
    r"\bwith\b",
]


def sanitize_sql(sql: str) -> str:
    sql = sql.strip()

    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()

    return sql.rstrip(";").strip()


def validate_sql(sql: str) -> str:
    cleaned = sanitize_sql(sql)
    normalized = cleaned.casefold()

    if not cleaned:
        raise AtlasValidationError("SQL vazio")

    if ";" in cleaned:
        raise AtlasValidationError("Múltiplas statements não são permitidas")

    if not re.match(r"^select\b", normalized, flags=re.IGNORECASE):
        raise AtlasValidationError("Apenas SELECT é permitido")

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            raise AtlasValidationError(f"SQL bloqueado pelo validador: {pattern}")

    if not re.search(r"\bfrom\s+dataset\b", normalized, flags=re.IGNORECASE):
        raise AtlasValidationError("A query deve usar apenas a tabela fixa dataset")

    if re.search(r"\bfrom\s+\(", normalized, flags=re.IGNORECASE):
        raise AtlasValidationError("Subquery em FROM não é permitida")

    return cleaned


def _split_sql_list(section: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0

    for ch in section:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)

    return parts


def _strip_alias(expr: str) -> str:
    expr = expr.strip()
    expr = re.sub(r"\s+as\s+[a-zA-Z_][a-zA-Z0-9_]*$", "", expr, flags=re.IGNORECASE)

    tokens = expr.split()
    if len(tokens) >= 2:
        last = tokens[-1]
        prev = tokens[-2]
        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", last) and prev not in {"=", ">", "<", ">=", "<=", "<>", "!="}:
            expr = " ".join(tokens[:-1])

    return expr.strip()


def _remove_string_literals(sql: str) -> str:
    sql = re.sub(r"'([^']|'')*'", " ", sql)
    sql = re.sub(r'"([^"]|"")*"', " ", sql)
    return sql


def _extract_identifiers(fragment: str) -> list[str]:
    fragment = _remove_string_literals(fragment)
    fragment = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(", " ", fragment)
    tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", fragment)

    cols: list[str] = []
    for token in tokens:
        lowered = token.casefold()
        if lowered in SQL_KEYWORDS:
            continue
        cols.append(token)
    return cols


def extract_referenced_columns_from_sql(sql: str) -> list[str]:
    cleaned = validate_sql(sql)
    normalized = cleaned.casefold()

    select_match = re.search(r"select\s+(.*?)\s+from\s+dataset\b", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if not select_match:
        return []

    select_section = select_match.group(1)
    select_parts = _split_sql_list(select_section)

    collected: list[str] = []

    for expr in select_parts:
        expr = _strip_alias(expr)
        if expr.strip() == "*":
            return []
        for identifier in _extract_identifiers(expr):
            collected.append(identifier)

    tail_match = re.search(
        r"\bfrom\s+dataset\b(.*)$",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if tail_match:
        tail = tail_match.group(1)
        for identifier in _extract_identifiers(tail):
            collected.append(identifier)

    deduped: list[str] = []
    seen: set[str] = set()
    for col in collected:
        lowered = col.casefold()
        if lowered not in seen:
            seen.add(lowered)
            deduped.append(col)

    return deduped


def validate_referenced_columns(
    referenced_columns: Iterable[str],
    allowed_columns: Iterable[str],
    *,
    sql_text: str | None = None,
) -> list[str]:
    allowed_map = {str(col).casefold(): str(col) for col in allowed_columns}
    llm_columns = [str(col).strip() for col in referenced_columns if str(col).strip()]
    llm_normalized = {col.casefold() for col in llm_columns}

    invalid_llm = sorted(col for col in llm_columns if col.casefold() not in allowed_map)
    if invalid_llm:
        raise AtlasValidationError(f"referenced_columns contém coluna inválida: {', '.join(invalid_llm)}")

    extracted = extract_referenced_columns_from_sql(sql_text) if sql_text else []
    invalid_extracted = sorted(col for col in extracted if col.casefold() not in allowed_map)
    if invalid_extracted:
        raise AtlasValidationError(f"SQL referencia coluna inexistente: {', '.join(invalid_extracted)}")

    extracted_normalized = {col.casefold() for col in extracted}

    if llm_normalized and extracted_normalized and llm_normalized != extracted_normalized:
        raise AtlasValidationError("Divergência entre SQL e referenced_columns")

    canonical = extracted if extracted else llm_columns
    deduped: list[str] = []
    seen: set[str] = set()

    for col in canonical:
        lowered = col.casefold()
        if lowered not in seen:
            seen.add(lowered)
            deduped.append(allowed_map.get(lowered, col))

    return deduped


sanitize_sql_query = sanitize_sql
get_referenced_columns = extract_referenced_columns_from_sql
