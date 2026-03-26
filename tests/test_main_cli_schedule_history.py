import json

import src.main_cli_schedule_history as cli


def test_handle_schedule_history_renders_text(monkeypatch):
    class DummySettings:
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "count_schedule_runs", lambda **kwargs: 2)
    monkeypatch.setattr(
        cli,
        "fetch_schedule_runs",
        lambda **kwargs: [
            {
                "id": 8,
                "run_timestamp": "2026-03-25T12:00:00+00:00",
                "status": "partial",
                "jobs": ["audit", "evaluate"],
                "summary": {"history": {"recent_status_counts": {"partial": 2, "ok": 1}}},
                "artifacts": {},
                "created_at": "2026-03-25T12:00:05+00:00",
            }
        ],
    )
    monkeypatch.setattr(
        cli,
        "summarize_schedule_runs",
        lambda **kwargs: {"runs_total": 2, "status_counts": {"partial": 1, "ok": 1}, "latest_run_timestamp": "2026-03-25T12:00:00+00:00"},
    )

    class Args:
        database_path = "data/ebooks.db"
        limit = 5
        offset = 0
        status = None
        output = "text"

    result = cli._handle_schedule_history(Args())

    assert "=== Atlas Local | History Schedule ===" in result
    assert "Banco: data/ebooks.db" in result
    assert "Tendencia recente: {'partial': 1, 'ok': 1}" in result
    assert "status=partial" in result


def test_handle_schedule_history_renders_json_when_empty(monkeypatch):
    class DummySettings:
        database_path = "data/ebooks.db"

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "count_schedule_runs", lambda **kwargs: 0)
    monkeypatch.setattr(cli, "fetch_schedule_runs", lambda **kwargs: [])
    monkeypatch.setattr(cli, "summarize_schedule_runs", lambda **kwargs: {"runs_total": 0, "status_counts": {}, "latest_run_timestamp": None})

    class Args:
        database_path = None
        limit = 3
        offset = 2
        status = "error"
        output = "json"

    payload = json.loads(cli._handle_schedule_history(Args()))

    assert payload["status"] == "not_found"
    assert payload["query"]["status"] == "error"
    assert payload["total_count"] == 0
