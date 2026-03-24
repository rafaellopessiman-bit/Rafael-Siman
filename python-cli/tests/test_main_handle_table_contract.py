from src import main


class _FakeTabularResponse:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_main_handle_table_returns_rendered_string_on_success(monkeypatch):
    monkeypatch.setattr(main, "TabularResponse", _FakeTabularResponse)
    monkeypatch.setattr(main, "extract_table_schema", lambda file_path: {"fake": "schema"})
    monkeypatch.setattr(main, "generate_sql_from_question", lambda question, schema: "select produto from data")
    monkeypatch.setattr(main, "validate_sql", lambda sql: sql)
    monkeypatch.setattr(main, "execute_validated_sql", lambda file_path, sql: [{"produto": "caneta"}])
    monkeypatch.setattr(main, "_normalize_tabular_result", lambda result, sql: {"rows": result, "sql": sql})
    monkeypatch.setattr(main, "_summarize_tabular_result", lambda result: "1 linha")

    captured = {}

    def _fake_render(response):
        captured["status"] = response.status
        captured["question"] = response.question
        captured["answer"] = response.answer
        captured["result"] = response.result
        return f"rendered::{response.status}::{response.answer}"

    monkeypatch.setattr(main, "render_tabular_response", _fake_render)

    output = main.handle_table("dados.csv", "qual produto?")

    assert isinstance(output, str)
    assert output == "rendered::ok::1 linha"
    assert captured["status"] == "ok"
    assert captured["question"] == "qual produto?"
    assert captured["answer"] == "1 linha"
    assert captured["result"] == {
        "rows": [{"produto": "caneta"}],
        "sql": "select produto from data",
    }


def test_main_handle_table_returns_rendered_string_on_blocked(monkeypatch):
    monkeypatch.setattr(main, "TabularResponse", _FakeTabularResponse)
    monkeypatch.setattr(main, "extract_table_schema", lambda file_path: {"fake": "schema"})
    monkeypatch.setattr(main, "generate_sql_from_question", lambda question, schema: "drop table dataset")

    def _raise_blocked(sql):
        raise main.AtlasBlockedQueryError("bloqueado no validador")

    monkeypatch.setattr(main, "validate_sql", _raise_blocked)

    captured = {}

    def _fake_render(response):
        captured["status"] = response.status
        captured["answer"] = response.answer
        captured["warnings"] = response.warnings
        captured["errors"] = response.errors
        captured["result"] = response.result
        return f"rendered::{response.status}"

    monkeypatch.setattr(main, "render_tabular_response", _fake_render)

    output = main.handle_table("dados.csv", "apague a tabela")

    assert output == "rendered::blocked"
    assert captured["status"] == "blocked"
    assert captured["answer"] == "A query foi bloqueada pelo validador de segurança."
    assert captured["warnings"] == ["bloqueado no validador"]
    assert captured["errors"] == ["bloqueado no validador"]
    assert captured["result"] is None


def test_main_handle_table_returns_rendered_string_on_execution_error(monkeypatch):
    monkeypatch.setattr(main, "TabularResponse", _FakeTabularResponse)
    monkeypatch.setattr(main, "extract_table_schema", lambda file_path: {"fake": "schema"})
    monkeypatch.setattr(main, "generate_sql_from_question", lambda question, schema: "select produto from data")
    monkeypatch.setattr(main, "validate_sql", lambda sql: sql)

    def _raise_execution(file_path, sql):
        raise main.AtlasExecutionError("falha no duckdb")

    monkeypatch.setattr(main, "execute_validated_sql", _raise_execution)

    captured = {}

    def _fake_render(response):
        captured["status"] = response.status
        captured["answer"] = response.answer
        captured["warnings"] = response.warnings
        captured["errors"] = response.errors
        captured["result"] = response.result
        return f"rendered::{response.status}"

    monkeypatch.setattr(main, "render_tabular_response", _fake_render)

    output = main.handle_table("dados.csv", "qual produto?")

    assert output == "rendered::error"
    assert captured["status"] == "error"
    assert captured["answer"] == "A rota tabular falhou durante validação ou execução."
    assert captured["warnings"] == ["falha no duckdb"]
    assert captured["errors"] == ["falha no duckdb"]
    assert captured["result"] is None


def test_main_handle_table_is_thin_facade_over_private_compat(monkeypatch):
    captured = {}

    def _fake_handle_table_compat(file_path, question, **kwargs):
        captured["file_path"] = file_path
        captured["question"] = question
        captured["kwargs"] = kwargs
        return "delegated::ok"

    monkeypatch.setattr(main, "_handle_table_compat", _fake_handle_table_compat)

    output = main.handle_table("dados.csv", "qual produto?")

    assert output == "delegated::ok"
    assert captured["file_path"] == "dados.csv"
    assert captured["question"] == "qual produto?"
    assert captured["kwargs"]["extract_table_schema"] is main.extract_table_schema
    assert captured["kwargs"]["generate_sql_from_question"] is main.generate_sql_from_question
    assert captured["kwargs"]["validate_sql"] is main.validate_sql
    assert captured["kwargs"]["execute_validated_sql"] is main.execute_validated_sql
    assert captured["kwargs"]["normalize_tabular_result"] is main._normalize_tabular_result
    assert captured["kwargs"]["summarize_tabular_result"] is main._summarize_tabular_result
    assert captured["kwargs"]["tabular_response_cls"] is main.TabularResponse
    assert captured["kwargs"]["render_tabular_response"] is main.render_tabular_response
    assert captured["kwargs"]["blocked_error_cls"] is main.AtlasBlockedQueryError
    assert captured["kwargs"]["execution_error_cls"] is main.AtlasExecutionError
