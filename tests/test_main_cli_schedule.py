import json

import src.main_cli_schedule as cli


def test_run_pdf_ocr_batch_returns_error_when_command_is_missing(monkeypatch):
    monkeypatch.setattr(cli.shutil, "which", lambda command: None)

    result = cli.run_pdf_ocr_batch(["E:/E-book/scan.pdf"], ocr_command="missing")

    assert result["status"] == "error"
    assert result["processed"] == 0


def test_handle_schedule_runs_audit_report_and_ocr(monkeypatch, tmp_path):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        pdf_ocr_command = "ocrmypdf"
        pdf_ocr_language = "por+eng"
        schedule_eval_queries_path = "data/eval_queries.json"
        schedule_eval_baseline_path = "data/eval_baseline.json"
        schedule_eval_top_k = 5
        schedule_notify_webhook_url = None
        schedule_notify_on = "on-issues"
        schedule_notify_timeout_seconds = 10
        schedule_notify_format = "raw"

    audit_payload = {
        "status": "ok",
        "remediation": {"ocr_required_paths": ["E:/E-book/scan.pdf"]},
    }

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "_handle_audit", lambda args=None: json.dumps(audit_payload))
    monkeypatch.setattr(
        cli,
        "generate_report_artifact",
        lambda **kwargs: {"written": True, "output_path": str(tmp_path / "report.xlsx")},
    )
    monkeypatch.setattr(
        cli,
        "run_pdf_ocr_batch",
        lambda **kwargs: {
            "status": "ok",
            "candidate_count": 1,
            "processed": 1,
            "outputs": [{"input_path": "E:/E-book/scan.pdf", "output_path": "E:/E-book/scan.ocr.pdf"}],
            "errors": [],
        },
    )
    monkeypatch.setattr(
        cli,
        "run_reindex_after_ocr",
        lambda **kwargs: {
            "status": "ok",
            "candidate_count": 1,
            "processed": 1,
            "indexed": 1,
            "errors": [],
            "remediation_counts": {"index": 1},
        },
    )

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output_dir = str(tmp_path)
        jobs = ["all"]
        report_output = "xlsx"
        report_output_path = None
        audit_output_path = None
        pdf_ocr_command = None
        pdf_ocr_language = None
        ocr_in_place = False
        reindex_after_ocr = True
        workers = None
        batch_size = None
        similarity_threshold = None
        isolate_flags = None
        notify_webhook_url = None
        notify_on = None
        notify_timeout_seconds = None
        notify_format = None
        eval_queries_path = None
        eval_baseline_path = None
        eval_top_k = None

    args = Args()
    result = cli._handle_schedule(args)

    assert "Audit JSON:" in result
    assert "Report artifact:" in result
    assert "OCR pending candidatos: 1" in result
    assert "Reindex after OCR indexados: 1" in result
    assert "Schedule summary:" in result
    assert "Schedule run id:" in result
    assert (tmp_path / next(path.name for path in tmp_path.iterdir() if path.name.startswith("audit-"))).exists()


def test_handle_schedule_sends_webhook_when_configured(monkeypatch, tmp_path):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        pdf_ocr_command = "ocrmypdf"
        pdf_ocr_language = "por+eng"
        schedule_eval_queries_path = "data/eval_queries.json"
        schedule_eval_baseline_path = "data/eval_baseline.json"
        schedule_eval_top_k = 5
        schedule_notify_webhook_url = "https://example.test/webhook"
        schedule_notify_on = "always"
        schedule_notify_timeout_seconds = 7
        schedule_notify_format = "slack"

    audit_payload = {
        "status": "ok",
        "remediation": {
            "ocr_required_paths": [],
            "isolated_paths": ["E:/E-book/bad.txt"],
            "review_paths": [],
            "counts": {"isolate": 1},
        },
    }
    captured = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "_handle_audit", lambda args=None: json.dumps(audit_payload))
    monkeypatch.setattr(
        cli,
        "generate_report_artifact",
        lambda **kwargs: {"written": True, "output_path": str(tmp_path / "report.xlsx")},
    )
    monkeypatch.setattr(
        cli,
        "send_json_webhook",
        lambda url, payload, timeout_seconds: captured.update({"url": url, "payload": payload, "timeout": timeout_seconds}) or {
            "status": "ok",
            "status_code": 202,
            "body": "accepted",
        },
    )
    monkeypatch.setattr(cli, "record_schedule_run", lambda **kwargs: 42)
    monkeypatch.setattr(cli, "summarize_schedule_runs", lambda **kwargs: {"runs_total": 3, "status_counts": {"ok": 2, "partial": 1}, "latest_run_timestamp": "2026-03-25T11:00:00+00:00"})
    monkeypatch.setattr(cli, "fetch_schedule_runs", lambda **kwargs: [{"id": 42, "run_timestamp": "2026-03-25T11:00:00+00:00", "status": "ok", "jobs": ["audit", "report"]}])
    monkeypatch.setattr(cli, "update_schedule_run", lambda **kwargs: None)

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output_dir = str(tmp_path)
        jobs = ["audit", "report"]
        report_output = "xlsx"
        report_output_path = None
        audit_output_path = None
        pdf_ocr_command = None
        pdf_ocr_language = None
        ocr_in_place = False
        reindex_after_ocr = False
        workers = None
        batch_size = None
        similarity_threshold = None
        isolate_flags = None
        notify_webhook_url = None
        notify_on = None
        notify_timeout_seconds = None
        notify_format = None
        eval_queries_path = None
        eval_baseline_path = None
        eval_top_k = None

    args = Args()
    result = cli._handle_schedule(args)

    assert "Webhook notify: ok (202)" in result
    assert captured["url"] == "https://example.test/webhook"
    assert captured["timeout"] == 7
    assert captured["payload"]["text"] == "Atlas Local Schedule: OK"
    assert len(captured["payload"]["blocks"]) >= 2


def test_handle_schedule_runs_evaluate_and_persists_history(monkeypatch, tmp_path):
    class DummySettings:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        pdf_ocr_command = "ocrmypdf"
        pdf_ocr_language = "por+eng"
        schedule_eval_queries_path = "data/eval_queries.json"
        schedule_eval_baseline_path = "data/eval_baseline.json"
        schedule_eval_top_k = 5
        schedule_notify_webhook_url = None
        schedule_notify_on = "on-issues"
        schedule_notify_timeout_seconds = 10
        schedule_notify_format = "raw"

    captured = {}

    monkeypatch.setattr(cli, "get_settings", lambda: DummySettings())
    monkeypatch.setattr(cli, "load_eval_queries", lambda path: [object()])
    monkeypatch.setattr(
        cli,
        "evaluate_retrieval",
        lambda eval_queries, db_path, top_k, docs_path: type(
            "EvalReportStub",
            (),
            {
                "mrr": 0.9,
                "mean_precision_at_k": 0.7,
                "mean_ndcg_at_k": 0.8,
                "top1_accuracy": 1.0,
                "regressions": [],
            },
        )(),
    )
    monkeypatch.setattr(cli, "detect_regressions", lambda report, baseline_path: ["REGRESSAO mrr: 1.0 -> 0.9"])
    monkeypatch.setattr(cli, "format_report", lambda report: "evaluation report")
    monkeypatch.setattr(cli.Path, "exists", lambda self: True)
    monkeypatch.setattr(cli, "record_schedule_run", lambda **kwargs: captured.setdefault("run_id", 77))
    monkeypatch.setattr(cli, "summarize_schedule_runs", lambda **kwargs: {"runs_total": 4, "status_counts": {"partial": 2, "ok": 2}, "latest_run_timestamp": "2026-03-25T12:00:00+00:00"})
    monkeypatch.setattr(cli, "fetch_schedule_runs", lambda **kwargs: [{"id": 77, "run_timestamp": "2026-03-25T12:00:00+00:00", "status": "partial", "jobs": ["evaluate"]}])
    monkeypatch.setattr(cli, "update_schedule_run", lambda **kwargs: captured.update({"updated": kwargs}))

    class Args:
        documents_path = "E:/E-book"
        database_path = "data/ebooks.db"
        output_dir = str(tmp_path)
        jobs = ["evaluate"]
        report_output = "xlsx"
        report_output_path = None
        audit_output_path = None
        pdf_ocr_command = None
        pdf_ocr_language = None
        ocr_in_place = False
        reindex_after_ocr = False
        workers = None
        batch_size = None
        similarity_threshold = None
        isolate_flags = None
        notify_webhook_url = None
        notify_on = None
        notify_timeout_seconds = None
        notify_format = None
        eval_queries_path = str(tmp_path / "eval_queries.json")
        eval_baseline_path = str(tmp_path / "eval_baseline.json")
        eval_top_k = 5
        critical_regression_exit_code = 7

    args = Args()
    result = cli._handle_schedule(args)

    assert "Evaluate summary:" in result
    assert "Evaluate regressions: 1" in result
    assert "Evaluate critical regression: yes (exit_code=7)" in result
    assert "Schedule run id: 77" in result
    assert captured["updated"]["status"] == "partial"
    assert args._atlas_exit_code == 7
