import argparse
import builtins

import src.main as main
from src.main import build_parser


def test_build_parser_returns_argument_parser():
    parser = build_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_parser_exposes_ask_command_in_help():
    parser = build_parser()
    help_text = parser.format_help().lower()
    assert "ask" in help_text


def test_build_parser_parses_minimal_ask_invocation():
    parser = build_parser()
    namespace = parser.parse_args(["ask", "ping"])

    assert namespace.command == "ask"
    assert namespace.question == ["ping"]


def test_build_parser_parses_ask_overrides():
    parser = build_parser()
    namespace = parser.parse_args(["ask", "arquitetura backend", "--path", "E:/E-book", "--db-path", "data/ebooks_catalog.db"])

    assert namespace.command == "ask"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks_catalog.db"


def test_build_parser_parses_index_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "index",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--workers",
        "8",
        "--batch-size",
        "25",
        "--enable-pdf-ocr",
        "--pdf-ocr-command",
        "ocrmypdf-custom",
        "--pdf-ocr-language",
        "por+eng",
        "--enable-image-ocr",
        "--image-ocr-command",
        "tesseract-custom",
        "--image-ocr-language",
        "por",
        "--isolate-flags",
        "numeric_heavy,no_usable_chunks",
    ])

    assert namespace.command == "index"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.workers == 8
    assert namespace.batch_size == 25
    assert namespace.enable_pdf_ocr is True
    assert namespace.pdf_ocr_command == "ocrmypdf-custom"
    assert namespace.pdf_ocr_language == "por+eng"
    assert namespace.enable_image_ocr is True
    assert namespace.image_ocr_command == "tesseract-custom"
    assert namespace.image_ocr_language == "por"
    assert namespace.isolate_flags == "numeric_heavy,no_usable_chunks"


def test_build_parser_parses_audit_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "audit",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--workers",
        "4",
        "--batch-size",
        "50",
        "--enable-pdf-ocr",
        "--pdf-ocr-command",
        "ocrmypdf-custom",
        "--pdf-ocr-language",
        "por+eng",
        "--enable-image-ocr",
        "--image-ocr-command",
        "tesseract-custom",
        "--image-ocr-language",
        "por",
        "--similarity-threshold",
        "0.25",
        "--output",
        "json",
        "--reindex-selective",
        "--isolate-flags",
        "numeric_heavy",
    ])

    assert namespace.command == "audit"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.workers == 4
    assert namespace.batch_size == 50
    assert namespace.enable_pdf_ocr is True
    assert namespace.pdf_ocr_command == "ocrmypdf-custom"
    assert namespace.pdf_ocr_language == "por+eng"
    assert namespace.enable_image_ocr is True
    assert namespace.image_ocr_command == "tesseract-custom"
    assert namespace.image_ocr_language == "por"
    assert namespace.similarity_threshold == 0.25
    assert namespace.output == "json"
    assert namespace.reindex_selective is True
    assert namespace.isolate_flags == "numeric_heavy"


def test_build_parser_parses_history_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "history",
        "E:/E-book/doc.txt",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--limit",
        "5",
        "--offset",
        "10",
        "--source-command",
        "audit",
        "--action",
        "ocr_required",
        "--output",
        "json",
    ])

    assert namespace.command == "history"
    assert namespace.file_path == "E:/E-book/doc.txt"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.limit == 5
    assert namespace.offset == 10
    assert namespace.source_command == "audit"
    assert namespace.remediation_action == "ocr_required"
    assert namespace.output == "json"


def test_build_parser_parses_history_schedule_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "history-schedule",
        "--db-path",
        "data/ebooks.db",
        "--limit",
        "10",
        "--offset",
        "5",
        "--status",
        "partial",
        "--output",
        "json",
    ])

    assert namespace.command == "history-schedule"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.limit == 10
    assert namespace.offset == 5
    assert namespace.status == "partial"
    assert namespace.output == "json"


def test_build_parser_parses_report_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "report",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--output",
        "xlsx",
        "--output-path",
        "data/processados/report.xlsx",
    ])

    assert namespace.command == "report"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.output == "xlsx"
    assert namespace.output_path == "data/processados/report.xlsx"


def test_build_parser_parses_schedule_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "schedule",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--jobs",
        "audit",
        "report",
        "ocr-pending",
        "evaluate",
        "--output-dir",
        "data/processados/schedule",
        "--report-output",
        "xlsx",
        "--ocr-in-place",
        "--reindex-after-ocr",
        "--notify-webhook-url",
        "https://example.test/webhook",
        "--notify-on",
        "always",
        "--notify-timeout-seconds",
        "15",
        "--notify-format",
        "teams",
        "--eval-queries",
        "data/eval_queries.json",
        "--eval-baseline",
        "data/eval_baseline.json",
        "--eval-top-k",
        "7",
        "--critical-regression-exit-code",
        "9",
    ])

    assert namespace.command == "schedule"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.jobs == ["audit", "report", "ocr-pending", "evaluate"]
    assert namespace.output_dir == "data/processados/schedule"
    assert namespace.report_output == "xlsx"
    assert namespace.ocr_in_place is True
    assert namespace.reindex_after_ocr is True
    assert namespace.notify_webhook_url == "https://example.test/webhook"
    assert namespace.notify_on == "always"
    assert namespace.notify_timeout_seconds == 15
    assert namespace.notify_format == "teams"
    assert namespace.eval_queries_path == "data/eval_queries.json"
    assert namespace.eval_baseline_path == "data/eval_baseline.json"
    assert namespace.eval_top_k == 7
    assert namespace.critical_regression_exit_code == 9


def test_build_parser_parses_watch_overrides():
    parser = build_parser()
    namespace = parser.parse_args([
        "watch",
        "--path",
        "E:/E-book",
        "--db-path",
        "data/ebooks.db",
        "--workers",
        "3",
        "--batch-size",
        "40",
        "--interval-seconds",
        "15",
        "--max-cycles",
        "4",
        "--remediation-policy",
        "full-auto",
        "--pdf-ocr-command",
        "ocrmypdf-custom",
        "--pdf-ocr-language",
        "por+eng",
        "--image-ocr-command",
        "tesseract-custom",
        "--image-ocr-language",
        "por",
        "--isolate-flags",
        "numeric_heavy,no_usable_chunks",
    ])

    assert namespace.command == "watch"
    assert namespace.documents_path == "E:/E-book"
    assert namespace.database_path == "data/ebooks.db"
    assert namespace.workers == 3
    assert namespace.batch_size == 40
    assert namespace.interval_seconds == 15
    assert namespace.max_cycles == 4
    assert namespace.remediation_policy == "full-auto"
    assert namespace.pdf_ocr_command == "ocrmypdf-custom"
    assert namespace.pdf_ocr_language == "por+eng"
    assert namespace.image_ocr_command == "tesseract-custom"
    assert namespace.image_ocr_language == "por"
    assert namespace.isolate_flags == "numeric_heavy,no_usable_chunks"


def test_main_schedule_returns_exit_code_from_args(monkeypatch):
    class DummyParser:
        def parse_args(self, argv=None):
            class Args:
                command = "schedule"
                _atlas_exit_code = 0

            return Args()

        def print_help(self):
            raise AssertionError("print_help nao deveria ser chamado")

    def fake_handle_schedule(args):
        args._atlas_exit_code = 7
        return "schedule::ok"

    monkeypatch.setattr(main, "build_parser", lambda: DummyParser())
    monkeypatch.setattr(main, "handle_schedule", fake_handle_schedule)
    monkeypatch.setattr(builtins, "print", lambda *args, **kwargs: None)

    assert main.main(["schedule"]) == 7


def test_build_parser_is_thin_facade_over_private_cli_parser(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(main, "_build_parser", lambda: sentinel)
    assert main.build_parser() is sentinel
