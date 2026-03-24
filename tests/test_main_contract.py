import argparse
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


def test_build_parser_is_thin_facade_over_private_cli_parser(monkeypatch):
    sentinel = object()
    monkeypatch.setattr(main, "_build_parser", lambda: sentinel)
    assert main.build_parser() is sentinel
