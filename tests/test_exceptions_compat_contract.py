import src.exceptions as canonical
import src.src.exceptions as compat


def _exception_surface(module):
    return sorted(
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and isinstance(value, type)
        and issubclass(value, Exception)
    )


def test_nested_exceptions_surface_matches_canonical():
    assert _exception_surface(compat) == _exception_surface(canonical)
