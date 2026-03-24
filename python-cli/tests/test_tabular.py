import pytest

from src import main
from src.exceptions import AtlasBlockedQueryError, AtlasExecutionError
from src.tabular.schema_extractor import extract_table_schema


def test_extract_table_schema_reads_csv(tmp_path):
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,quantidade,preco\ncaneta,10,2.50\nlapis,5,1.25\n",
        encoding="utf-8",
    )

    schema = extract_table_schema(csv_path)

    assert schema.file_name == "dados.csv"
    assert schema.table_name == "dataset"
    assert [column.name for column in schema.columns] == ["produto", "quantidade", "preco"]
    assert [column.inferred_type for column in schema.columns] == ["TEXT", "INTEGER", "DOUBLE"]


def test_handle_table_returns_ok_with_mocked_sql_pipeline(monkeypatch, tmp_path):
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,quantidade,preco\ncaneta,10,2.50\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "generate_sql_from_question",
        lambda question, table_schema: "SELECT SUM(quantidade) FROM dataset",
    )
    monkeypatch.setattr(main, "validate_sql", lambda sql: sql)

    output = main.handle_table(str(csv_path), "Qual é a quantidade total de produtos?")

    assert "Status: ok" in output
    assert "Valor: 10" in output
    assert "dados.csv" in output
    assert "SELECT SUM(quantidade) FROM dataset" in output


def test_handle_table_returns_blocked_when_validator_blocks(monkeypatch, tmp_path):
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,quantidade,preco\ncaneta,10,2.50\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "generate_sql_from_question",
        lambda question, table_schema: "DROP TABLE dataset",
    )

    def raise_blocked(sql: str):
        raise AtlasBlockedQueryError("Query bloqueada pelo validador.")

    monkeypatch.setattr(main, "validate_sql", raise_blocked)

    output = main.handle_table(str(csv_path), "Apague a tabela")

    assert "Status: blocked" in output
    assert "A query foi bloqueada pelo validador de segurança." in output
    assert "Query bloqueada pelo validador." in output


def test_handle_table_returns_error_when_execution_fails(monkeypatch, tmp_path):
    csv_path = tmp_path / "dados.csv"
    csv_path.write_text(
        "produto,quantidade,preco\ncaneta,10,2.50\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        main,
        "generate_sql_from_question",
        lambda question, table_schema: "SELECT SUM(quantidade) FROM dataset",
    )
    monkeypatch.setattr(main, "validate_sql", lambda sql: sql)

    def raise_execution_error(file_path: str, sql: str):
        raise AtlasExecutionError("Falha simulada no DuckDB.")

    monkeypatch.setattr(main, "execute_validated_sql", raise_execution_error)

    output = main.handle_table(str(csv_path), "Qual é a quantidade total de produtos?")

    assert "Status: error" in output
    assert "A rota tabular falhou durante validação ou execução." in output
    assert "Falha simulada no DuckDB." in output
