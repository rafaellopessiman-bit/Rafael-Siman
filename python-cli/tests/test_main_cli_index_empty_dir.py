import src.main_cli_index as cli


def test_handle_index_returns_clean_message_when_loader_finds_no_supported_documents(monkeypatch):
    class DummySettings:
        documents_path = "dados_vazios"
        database_path = "data/atlas_local.db"

    calls = {"initialize": 0, "upsert": 0}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())

    def fake_load_documents(_path):
        raise cli.AtlasLoadError("Nenhum arquivo textual suportado foi encontrado em: dados_vazios")

    def fake_initialize_database(*args, **kwargs):
        calls["initialize"] += 1

    def fake_upsert_documents(*args, **kwargs):
        calls["upsert"] += 1
        return []

    monkeypatch.setattr(cli, "load_documents", fake_load_documents)
    monkeypatch.setattr(cli, "initialize_database", fake_initialize_database)
    monkeypatch.setattr(cli, "upsert_documents", fake_upsert_documents)

    result = cli._handle_index()

    assert "=== Atlas Local | Index ===" in result
    assert "Origem: dados_vazios" in result
    assert "Aviso: Nenhum arquivo textual suportado foi encontrado em: dados_vazios" in result
    assert "Operação abortada. Banco inalterado." in result
    assert calls["initialize"] == 0
    assert calls["upsert"] == 0
