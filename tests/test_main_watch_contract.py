import inspect

import src.main as main


def test_handle_watch_is_thin_facade_over_private_cli_watch(monkeypatch):
    calls = []

    def mock_watch(*args, **kwargs):
        calls.append((args, kwargs))
        return "watch::ok"

    monkeypatch.setattr(main, "_handle_watch", mock_watch)

    sig = inspect.signature(main.handle_watch)
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

    result = main.handle_watch(*args, **kwargs)

    assert result == "watch::ok"
    assert len(calls) == 1
