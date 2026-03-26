from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.knowledge.corpus_filter import detect_duplicates

DEFAULT_ISOLATE_FLAGS = {
    "no_usable_chunks",
    "very_short_document",
    "repetitive_content",
    "numeric_heavy",
    "low_vocabulary_document",
}
OCR_REQUIRED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def _normalize_flags(raw_flags: str | list[str] | tuple[str, ...] | set[str] | frozenset[str] | None) -> tuple[str, ...]:
    if raw_flags is None:
        return tuple(sorted(DEFAULT_ISOLATE_FLAGS))

    if isinstance(raw_flags, str):
        values = [item.strip().lower() for item in raw_flags.split(",") if item.strip()]
        return tuple(dict.fromkeys(values))

    values = [str(item).strip().lower() for item in raw_flags if str(item).strip()]
    return tuple(dict.fromkeys(values))


@dataclass(frozen=True)
class RemediationPolicy:
    isolate_flags: frozenset[str]


@dataclass(frozen=True)
class DocumentRemediationDecision:
    file_path: str
    flags: list[str]
    action: str
    should_index: bool
    duplicate_of: str | None = None


def build_remediation_policy(
    isolate_flags: str | list[str] | tuple[str, ...] | set[str] | frozenset[str] | None = None,
) -> RemediationPolicy:
    return RemediationPolicy(isolate_flags=frozenset(_normalize_flags(isolate_flags)))


def build_document_remediation_plan(
    documents: list[dict[str, Any]],
    audit_report: Any,
    duplicate_report: Any | None = None,
    policy: RemediationPolicy | None = None,
) -> list[DocumentRemediationDecision]:
    duplicate_report = duplicate_report or detect_duplicates(documents)
    active_policy = policy or build_remediation_policy()

    flags_by_path: dict[str, set[str]] = {}
    duplicate_of_by_path: dict[str, str] = {}

    for duplicate in getattr(duplicate_report, "duplicates", []):
        file_path = str(duplicate.get("file_path", ""))
        if not file_path:
            continue
        flags_by_path.setdefault(file_path, set()).add("duplicate_document")
        duplicate_of = str(duplicate.get("_duplicate_of", "") or "")
        if duplicate_of:
            duplicate_of_by_path[file_path] = duplicate_of

    for outlier in getattr(audit_report, "outliers", []):
        file_path = str(getattr(outlier, "file_path", ""))
        if not file_path:
            continue
        flags_by_path.setdefault(file_path, set()).update(getattr(outlier, "reasons", []))

    for cluster in getattr(audit_report, "clusters", []):
        for member_path in getattr(cluster, "member_paths", []):
            file_path = str(member_path)
            if not file_path:
                continue
            flags_by_path.setdefault(file_path, set()).add("cluster_similar_document")

    decisions: list[DocumentRemediationDecision] = []
    for document in sorted(documents, key=lambda item: str(item.get("file_path", ""))):
        file_path = str(document.get("file_path", ""))
        flags = sorted(flags_by_path.get(file_path, set()))
        duplicate_of = duplicate_of_by_path.get(file_path)

        if "duplicate_document" in flags:
            action = "ignore_duplicate"
            should_index = False
        elif any(flag in active_policy.isolate_flags for flag in flags):
            action = "isolate"
            should_index = False
        elif flags:
            action = "index_with_review"
            should_index = True
        else:
            action = "index"
            should_index = True

        decisions.append(
            DocumentRemediationDecision(
                file_path=file_path,
                flags=flags,
                action=action,
                should_index=should_index,
                duplicate_of=duplicate_of,
            )
        )

    return decisions


def summarize_remediation_actions(
    decisions: list[DocumentRemediationDecision],
) -> dict[str, int]:
    counts = Counter(decision.action for decision in decisions)
    return dict(sorted(counts.items()))


def build_error_remediation_decisions(errors: list[str] | None) -> list[DocumentRemediationDecision]:
    decisions: list[DocumentRemediationDecision] = []
    for item in errors or []:
        file_path = _extract_error_file_path(item)
        if not file_path:
            continue

        flags = _extract_error_flags(file_path=file_path, error=item)
        if not flags:
            continue

        decisions.append(
            DocumentRemediationDecision(
                file_path=file_path,
                flags=flags,
                action="ocr_required",
                should_index=False,
            )
        )

    return decisions


def _extract_error_file_path(error: str) -> str | None:
    prefix = "Falha ao carregar "
    if not error.startswith(prefix):
        return None

    try:
        path_part, _ = error[len(prefix):].split(": ", 1)
    except ValueError:
        return None

    file_path = path_part.strip()
    return file_path or None


def _extract_error_flags(file_path: str, error: str) -> list[str]:
    suffix = Path(file_path).suffix.lower()
    normalized = error.casefold()

    if suffix not in OCR_REQUIRED_EXTENSIONS:
        return []

    flags: list[str] = []
    if suffix == ".pdf" and "pdf sem texto extraivel" in normalized:
        flags.append("ocr_required")
    if suffix in OCR_REQUIRED_EXTENSIONS - {".pdf"} and "imagem requer ocr" in normalized:
        flags.append("ocr_required")
    if "ocr para imagem indisponivel" in normalized or "ocr executado mas nao produziu texto" in normalized:
        flags.append("ocr_required")
    if "ocr para pdf indisponivel" in normalized:
        flags.append("ocr_required")

    return sorted(set(flags))
