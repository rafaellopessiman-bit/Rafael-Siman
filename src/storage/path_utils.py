from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def normalize_path(path: str | Path, base_dir: str | Path | None = None) -> str:
    """
    Normaliza paths para comparação estável e persistência no SQLite.

    Regras:
    - se path for relativo e base_dir existir, ancora em base_dir antes de resolver
    - resolve(strict=False)
    - tenta converter para relativo ao base_dir
    - separador POSIX (/)
    - casefold no Windows
    """
    raw_path = Path(path).expanduser()

    base_resolved: Path | None = None
    if base_dir is not None:
        base_resolved = Path(base_dir).expanduser().resolve(strict=False)

    if not raw_path.is_absolute() and base_resolved is not None:
        raw_path = base_resolved / raw_path

    resolved = raw_path.resolve(strict=False)

    if base_resolved is not None:
        try:
            resolved = resolved.relative_to(base_resolved)
        except ValueError:
            pass

    normalized = resolved.as_posix()

    if os.name == "nt":
        normalized = normalized.casefold()

    return normalized


def normalize_paths(paths: Iterable[str | Path], base_dir: str | Path | None = None) -> list[str]:
    return sorted({normalize_path(path, base_dir=base_dir) for path in paths})
