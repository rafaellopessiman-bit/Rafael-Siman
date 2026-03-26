from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.knowledge.corpus_filter import deduplicate_chunks, filter_chunks

DEFAULT_MAX_CHARS = 1000
DEFAULT_OVERLAP = 120


def chunk_text(
    file_path: str | Path,
    text: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[str]:
    if not text or not text.strip():
        return []

    suffix = Path(file_path).suffix.lower()

    if suffix == ".md":
        segments = _segment_markdown(text)
    elif suffix == ".json":
        segments = _segment_json(text)
    else:
        segments = _segment_text(text)

    chunks: list[str] = []
    for segment in segments:
        clean = segment.strip()
        if not clean:
            continue
        if len(clean) <= max_chars:
            chunks.append(clean)
        else:
            chunks.extend(_window_chunks(clean, max_chars=max_chars, overlap=overlap))

    if not chunks:
        chunks = _window_chunks(text.strip(), max_chars=max_chars, overlap=overlap)

    # Apply corpus quality filters: drop low-quality and deduplicate
    chunks, _ = filter_chunks(chunks)
    chunks, _ = deduplicate_chunks(chunks)

    return chunks


def _segment_text(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]
    if paragraphs:
        return paragraphs
    return [text.strip()]


def _segment_markdown(text: str) -> list[str]:
    pattern = re.compile(r"(^#{1,6}\s+.+$)", flags=re.MULTILINE)
    parts = pattern.split(text)

    if len(parts) == 1:
        return _segment_text(text)

    segments: list[str] = []
    preamble = parts[0].strip()
    if preamble:
        segments.append(preamble)

    idx = 1
    while idx < len(parts):
        heading = parts[idx].strip()
        body = parts[idx + 1].strip() if idx + 1 < len(parts) else ""
        segment = heading if not body else f"{heading}\n{body}"
        segments.append(segment.strip())
        idx += 2

    return segments


def _segment_json(text: str) -> list[str]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _segment_text(text)

    flattened_lines: list[str] = []
    _flatten_json(parsed, flattened_lines, prefix="")
    if not flattened_lines:
        return _segment_text(text)

    return _window_chunks("\n".join(flattened_lines), max_chars=DEFAULT_MAX_CHARS, overlap=DEFAULT_OVERLAP)


def _flatten_json(value: Any, output: list[str], prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten_json(child, output, child_prefix)
        return

    if isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            _flatten_json(child, output, child_prefix)
        return

    rendered = json.dumps(value, ensure_ascii=False)
    if prefix:
        output.append(f"{prefix}: {rendered}")
    else:
        output.append(rendered)


def _window_chunks(text: str, max_chars: int, overlap: int) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars deve ser > 0")
    if overlap < 0:
        raise ValueError("overlap deve ser >= 0")
    if overlap >= max_chars:
        raise ValueError("overlap deve ser menor que max_chars")

    text = text.strip()
    if not text:
        return []

    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap

    return chunks
