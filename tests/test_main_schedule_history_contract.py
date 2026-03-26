import inspect

import src.main as main


def test_handle_history_schedule_is_thin_facade_over_private_cli_schedule_history(monkeypatch):
    calls = []

    def mock_history(*args, **kwargs):
        calls.append((args, kwargs))
        return "history-schedule::ok"

    monkeypatch.setattr(main, "_handle_schedule_history", mock_history)

    sig = inspect.signature(main.handle_history_schedule)
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

    result = main.handle_history_schedule(*args, **kwargs)

    assert result == "history-schedule::ok"
    assert len(calls) == 1
