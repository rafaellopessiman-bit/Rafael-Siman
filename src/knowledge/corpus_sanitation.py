from __future__ import annotations

import re
from typing import Any


def sanitize_documents(documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    sanitized_documents: list[dict[str, Any]] = []
    sanitized_count = 0
    changed_characters = 0

    for document in documents:
        content = str(document.get("content", ""))
        sanitized_content = _sanitize_text(content)
        changed = sanitized_content != content

        metadata = dict(document.get("metadata") or {})
        if changed:
            sanitized_count += 1
            changed_characters += abs(len(content) - len(sanitized_content))
            metadata["sanitized"] = True

        sanitized_documents.append(
            {
                **document,
                "content": sanitized_content,
                "metadata": metadata,
            }
        )

    return sanitized_documents, {
        "documents": sanitized_count,
        "changed_characters": changed_characters,
    }


def _sanitize_text(content: str) -> str:
    if not content:
        return ""

    sanitized = content.replace("\r\n", "\n").replace("\r", "\n")
    sanitized = sanitized.replace("\x00", "")
    sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", sanitized)
    sanitized = re.sub(r"[ \t]+", " ", sanitized)
    sanitized = re.sub(r" ?\n ?", "\n", sanitized)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()
