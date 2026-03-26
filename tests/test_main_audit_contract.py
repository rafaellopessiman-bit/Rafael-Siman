import inspect

import src.main as main


def test_handle_audit_is_thin_facade_over_private_cli_audit(monkeypatch):
    calls = []

    def mock_audit(*args, **kwargs):
        calls.append((args, kwargs))
        return "audit::ok"

    monkeypatch.setattr(main, "_handle_audit", mock_audit)

    sig = inspect.signature(main.handle_audit)
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

    result = main.handle_audit(*args, **kwargs)

    assert result == "audit::ok"
    assert len(calls) == 1
