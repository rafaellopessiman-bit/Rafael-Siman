import inspect

import src.main as main


def test_handle_report_is_thin_facade_over_private_cli_report(monkeypatch):
    calls = []

    def mock_report(*args, **kwargs):
        calls.append((args, kwargs))
        return "report::ok"

    monkeypatch.setattr(main, "_handle_report", mock_report)

    sig = inspect.signature(main.handle_report)
    args = []
    kwargs = {}
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            args.append("teste")
        elif param.kind is inspect.Parameter.VAR_POSITIONAL:
            args.append("teste_extra")
        elif param.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[name] = "teste"
        elif param.kind is inspect.Parameter.VAR_KEYWORD:
            kwargs["extra"] = "teste"

    result = main.handle_report(*args, **kwargs)

    assert result == "report::ok"
    assert len(calls) == 1
