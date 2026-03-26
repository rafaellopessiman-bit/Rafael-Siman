from urllib import error

import src.integrations.webhook as webhook


def test_send_json_webhook_returns_ok_payload(monkeypatch):
    captured = {}

    class DummyResponse:
        status = 202

        def read(self):
            return b"accepted"

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request_obj, timeout):
        captured["url"] = request_obj.full_url
        captured["method"] = request_obj.get_method()
        captured["body"] = request_obj.data
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr(webhook.request, "urlopen", fake_urlopen)

    result = webhook.send_json_webhook("https://example.test/hook", {"status": "ok"}, timeout_seconds=12)

    assert result["status"] == "ok"
    assert result["status_code"] == 202
    assert captured["url"] == "https://example.test/hook"
    assert captured["method"] == "POST"
    assert captured["timeout"] == 12
    assert b'"status": "ok"' in captured["body"]


def test_send_json_webhook_returns_error_payload_on_url_error(monkeypatch):
    def fake_urlopen(request_obj, timeout):
        raise error.URLError("offline")

    monkeypatch.setattr(webhook.request, "urlopen", fake_urlopen)

    result = webhook.send_json_webhook("https://example.test/hook", {"status": "ok"})

    assert result["status"] == "error"
    assert result["status_code"] is None
    assert "offline" in result["message"]


def test_build_teams_webhook_payload_formats_schedule_summary():
    payload = webhook.build_webhook_payload(
        {
            "status": "partial",
            "schedule": {"jobs": ["audit", "evaluate"], "documents_path": "E:/E-book", "database_path": "data/ebooks.db"},
            "steps": {
                "evaluate": {"status": "partial", "regressions": ["REGRESSAO mrr: 1.0 -> 0.9"]},
                "audit": {"status": "ok", "ocr_required_count": 2, "isolated_count": 1, "review_count": 3},
            },
        },
        format_name="teams",
    )

    assert payload["@type"] == "MessageCard"
    assert payload["themeColor"] == "D9A441"
    assert payload["sections"][0]["facts"]
    assert any(section.get("title") == "Regressoes detectadas" for section in payload["sections"])
    assert any(section.get("title") == "Sinais operacionais" for section in payload["sections"])


def test_build_slack_webhook_payload_formats_schedule_summary():
    payload = webhook.build_webhook_payload(
        {
            "status": "ok",
            "schedule": {"jobs": ["audit", "report"], "documents_path": "E:/E-book", "database_path": "data/ebooks.db"},
            "steps": {
                "report": {"status": "ok"},
                "evaluate": {"status": "partial", "regressions": ["REGRESSAO top1_accuracy: 1.0 -> 0.8"]},
                "audit": {"status": "ok", "ocr_required_count": 1, "isolated_count": 2, "review_count": 0},
            },
        },
        format_name="slack",
    )

    assert payload["text"] == "Atlas Local Schedule: OK"
    assert payload["blocks"][0]["type"] == "section"
    assert len(payload["blocks"]) >= 3
