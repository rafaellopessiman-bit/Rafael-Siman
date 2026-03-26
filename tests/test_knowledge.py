from types import SimpleNamespace

import pytest

from src import main


def test_load_knowledge_documents_prefers_sqlite_index(monkeypatch):
    indexed_documents = [
        {
            "file_name": "config.json",
            "file_path": "data\\entrada\\config.json",
            "content": '{ "cliente": "Atlas", "prioridade": "alta" }',
        }
    ]

    monkeypatch.setattr(
        main, "get_settings",
        lambda: SimpleNamespace(documents_path="data/entrada", database_path="data/atlas_local.db"),
    )
    monkeypatch.setattr(main, "fetch_all_documents", lambda **kw: indexed_documents)

    def should_not_load(_):
        pytest.fail("load_documents não deveria ser chamado quando há índice no SQLite.")

    monkeypatch.setattr(main, "load_documents", should_not_load)

    documents = main._load_knowledge_documents()

    assert documents == indexed_documents


def test_load_knowledge_documents_falls_back_to_runtime_loader(monkeypatch):
    runtime_documents = [
        {
            "file_name": "config.json",
            "file_path": "data\\entrada\\config.json",
            "content": '{ "cliente": "Atlas", "prioridade": "alta" }',
        }
    ]

    monkeypatch.setattr(main, "fetch_all_documents", lambda **kw: [])
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(documents_path="data/entrada", database_path="data/atlas_local.db"),
    )
    monkeypatch.setattr(main, "load_documents", lambda path: runtime_documents)

    documents = main._load_knowledge_documents()

    assert documents == runtime_documents


def test_handle_ask_returns_insufficient_context_without_llm(monkeypatch):
    documents = [
        {
            "file_name": "config.json",
            "file_path": "data\\entrada\\config.json",
            "content": '{ "cliente": "Atlas", "prioridade": "alta" }',
            "score": 0.3,
        }
    ]

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(top_k=5, documents_path="data/entrada", database_path="data/atlas_local.db"),
    )
    monkeypatch.setattr(main, "_load_knowledge_documents", lambda args=None: documents)
    monkeypatch.setattr(main, "retrieve_documents", lambda question, docs, top_k, **kw: documents)

    def should_not_call_llm(*args, **kwargs):
        pytest.fail("O LLM não deveria ser chamado quando falta evidência suficiente.")

    monkeypatch.setattr(main, "generate_fast_completion", should_not_call_llm)

    output = main.handle_ask("Qual é o CPF do cliente?")

    assert "Status: insufficient_context" in output
    assert "Score" in output or "evidência" in output.lower()


def test_handle_ask_returns_ok_with_mocked_llm(monkeypatch):
    documents = [
        {
            "file_name": "config.json",
            "file_path": "data\\entrada\\config.json",
            "content": '{ "cliente": "Atlas", "prioridade": "alta", "status": "ativo" }',
            "score": 1.2,
        }
    ]

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(top_k=5, documents_path="data/entrada", database_path="data/atlas_local.db"),
    )
    monkeypatch.setattr(main, "_load_knowledge_documents", lambda args=None: documents)
    monkeypatch.setattr(main, "retrieve_documents", lambda question, docs, top_k, **kw: documents)
    monkeypatch.setattr(
        main,
        "generate_fast_completion",
        lambda prompt, temperature=0.0: "O cliente é Atlas e a prioridade é alta.",
    )

    output = main.handle_ask("O que os documentos dizem sobre cliente e prioridade?")

    assert "Status: ok" in output
    assert "O cliente é Atlas e a prioridade é alta." in output
    assert "config.json" in output


def test_load_knowledge_documents_accepts_cli_overrides(monkeypatch):
    indexed_documents = [{"file_name": "book.pdf", "file_path": "E:/E-book/book.pdf", "content": "conteudo"}]
    captured = {}

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(documents_path="data/entrada", database_path="data/atlas_local.db"),
    )

    def fake_fetch_all_documents(**kwargs):
        captured.update(kwargs)
        return indexed_documents

    monkeypatch.setattr(main, "fetch_all_documents", fake_fetch_all_documents)

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks_catalog.db"

    documents = main._load_knowledge_documents(Args())

    assert documents == indexed_documents
    assert captured["db_path"] == "data/ebooks_catalog.db"
    assert captured["base_dir"] == "E:/E-book"
