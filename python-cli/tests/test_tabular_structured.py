from __future__ import annotations

from pathlib import Path

import pytest

from src.tabular.executor import handle_table
from src.tabular.schemas import SQLGenerationModel
from src.tabular.sql_validator import (
    extract_referenced_columns_from_sql,
    validate_referenced_columns,
    validate_sql,
)


def test_validate_sql_allows_simple_select() -> None:
    sql = validate_sql("SELECT produto, prioridade FROM dataset WHERE prioridade = 'alta'")
    assert sql.startswith("SELECT")


def test_extract_referenced_columns_from_sql_simple_select() -> None:
    cols = extract_referenced_columns_from_sql(
        "SELECT produto, COUNT(*) AS total FROM dataset WHERE prioridade = 'alta' GROUP BY produto ORDER BY produto"
    )
    lowered = {col.casefold() for col in cols}
    assert "produto" in lowered
    assert "prioridade" in lowered


def test_validate_referenced_columns_blocks_invalid_column() -> None:
    with pytest.raises(Exception):
        validate_referenced_columns(
            ["coluna_inexistente"],
            ["produto", "prioridade", "cliente"],
            sql_text="SELECT produto FROM dataset",
        )


def test_handle_table_blocks_invalid_llm_column(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,prioridade,cliente\ncaneta,alta,Atlas\n",
        encoding="utf-8",
    )

    def fake_generate_sql(question, table_schema):
        return SQLGenerationModel(
            sql="SELECT produto FROM dataset",
            referenced_columns=["coluna_inexistente"],
        )

    monkeypatch.setattr("src.tabular.executor.generate_sql", fake_generate_sql)

    result = handle_table(csv_path, "Qual produto tem prioridade alta?")

    assert result["route"] == "tabular"
    assert result["status"] == "blocked"
    assert any("inválida" in err or "inexistente" in err for err in result["errors"])


def test_handle_table_blocks_divergence_between_sql_and_referenced_columns(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,prioridade,cliente\ncaneta,alta,Atlas\n",
        encoding="utf-8",
    )

    def fake_generate_sql(question, table_schema):
        return SQLGenerationModel(
            sql="SELECT produto FROM dataset",
            referenced_columns=["cliente"],
        )

    monkeypatch.setattr("src.tabular.executor.generate_sql", fake_generate_sql)

    result = handle_table(csv_path, "Qual produto existe?")

    assert result["route"] == "tabular"
    assert result["status"] == "blocked"
    assert any("Divergência" in err or "diverg" in err.casefold() for err in result["errors"])


def test_handle_table_executes_when_sql_and_columns_match(tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,prioridade,cliente\ncaneta,alta,Atlas\nlapis,baixa,Outro\n",
        encoding="utf-8",
    )

    def fake_generate_sql(question, table_schema):
        return SQLGenerationModel(
            sql="SELECT produto, prioridade FROM dataset WHERE prioridade = 'alta'",
            referenced_columns=["produto", "prioridade"],
        )

    monkeypatch.setattr("src.tabular.executor.generate_sql", fake_generate_sql)

    result = handle_table(csv_path, "Qual produto tem prioridade alta?")

    assert result["route"] == "tabular"
    assert result["status"] == "ok"
    assert result["row_count"] == 1
    assert result["columns"] == ["produto", "prioridade"]
