import inspect
import src.main as main


def test_handle_index_is_thin_facade_over_private_cli_index(monkeypatch):
    calls = []

    def mock_index(*args, **kwargs):
        calls.append((args, kwargs))
        return "index::ok"

    monkeypatch.setattr(main, "_handle_index", mock_index)

    sig = inspect.signature(main.handle_index)
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

    result = main.handle_index(*args, **kwargs)

    assert result == "index::ok"
    assert len(calls) == 1
