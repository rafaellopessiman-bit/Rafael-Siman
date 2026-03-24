import pytest

from src.exceptions import AtlasBlockedQueryError
from src.tabular.sql_validator import validate_sql


def test_validate_sql_allows_simple_select():
    sql = "SELECT SUM(quantidade) FROM dataset;"
    validated = validate_sql(sql)
    assert validated == "SELECT SUM(quantidade) FROM dataset"


def test_validate_sql_blocks_mutation():
    with pytest.raises(AtlasBlockedQueryError):
        validate_sql("DROP TABLE dataset;")


def test_validate_sql_blocks_multiple_statements():
    with pytest.raises(AtlasBlockedQueryError):
        validate_sql("SELECT * FROM dataset; SELECT 1;")


def test_validate_sql_blocks_external_reader():
    with pytest.raises(AtlasBlockedQueryError):
        validate_sql("SELECT * FROM read_csv('dados.csv')")


def test_validate_sql_blocks_non_dataset_source():
    with pytest.raises(AtlasBlockedQueryError):
        validate_sql("SELECT * FROM outra_tabela")
