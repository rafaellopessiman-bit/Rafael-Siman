from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from src.knowledge.corpus_filter import detect_duplicates
from src.storage.chunking import chunk_text

TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
MIN_DOCUMENT_CHARS = 200
MAX_REPETITION_RATIO = 0.4
HIGH_NUMERIC_DOCUMENT_RATIO = 0.35
LOW_UNIQUE_TOKEN_RATIO = 0.2
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_SIGNATURE_TERMS = 24


@dataclass
class DocumentOutlier:
    file_path: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class DocumentCluster:
    member_paths: list[str] = field(default_factory=list)
    shared_terms: list[str] = field(default_factory=list)
    average_similarity: float = 0.0


@dataclass
class CorpusAuditReport:
    total_documents: int = 0
    duplicate_count: int = 0
    duplicate_paths: list[str] = field(default_factory=list)
    outliers: list[DocumentOutlier] = field(default_factory=list)
    clusters: list[DocumentCluster] = field(default_factory=list)
    flag_counts: dict[str, int] = field(default_factory=dict)


@dataclass
class _DocumentFeatures:
    file_path: str
    char_count: int
    token_count: int
    unique_token_ratio: float
    numeric_ratio: float
    repetition_ratio: float
    usable_chunk_count: int
    signature_terms: set[str]


def audit_documents(
    documents: list[dict[str, Any]],
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> CorpusAuditReport:
    report = CorpusAuditReport(total_documents=len(documents))
    if not documents:
        return report

    duplicate_report = detect_duplicates(documents)
    report.duplicate_count = len(duplicate_report.duplicates)
    report.duplicate_paths = [str(item.get("file_path", "")) for item in duplicate_report.duplicates]

    features = [_extract_document_features(document) for document in documents]
    report.outliers = _detect_outliers(features)
    report.clusters = _cluster_documents(features, similarity_threshold=similarity_threshold)

    counter: Counter[str] = Counter()
    for item in report.outliers:
        counter.update(item.reasons)
    report.flag_counts = dict(counter)

    return report


def _extract_document_features(document: dict[str, Any]) -> _DocumentFeatures:
    content = str(document.get("content", "") or "")
    file_path = str(document.get("file_path", ""))
    stripped = content.strip()
    tokens = _tokenize(stripped)
    line_count = _non_empty_lines(stripped)
    repeated_lines = _repeated_line_ratio(stripped, line_count)
    total_chars = len(stripped)
    numeric_ratio = _numeric_ratio(stripped)
    usable_chunks = len(chunk_text(file_path=file_path, text=stripped)) if stripped else 0

    unique_token_ratio = (len(set(tokens)) / len(tokens)) if tokens else 0.0

    return _DocumentFeatures(
        file_path=file_path,
        char_count=total_chars,
        token_count=len(tokens),
        unique_token_ratio=unique_token_ratio,
        numeric_ratio=numeric_ratio,
        repetition_ratio=repeated_lines,
        usable_chunk_count=usable_chunks,
        signature_terms=_signature_terms(tokens),
    )


def _detect_outliers(features: list[_DocumentFeatures]) -> list[DocumentOutlier]:
    if not features:
        return []

    char_stats = _robust_stats([item.char_count for item in features])
    token_stats = _robust_stats([item.token_count for item in features])

    outliers: list[DocumentOutlier] = []
    for item in features:
        reasons: list[str] = []

        if item.usable_chunk_count == 0:
            reasons.append("no_usable_chunks")
        if 0 < item.char_count < MIN_DOCUMENT_CHARS:
            reasons.append("very_short_document")
        if item.repetition_ratio > MAX_REPETITION_RATIO:
            reasons.append("repetitive_content")
        if item.numeric_ratio > HIGH_NUMERIC_DOCUMENT_RATIO:
            reasons.append("numeric_heavy")
        if item.token_count >= 20 and item.unique_token_ratio < LOW_UNIQUE_TOKEN_RATIO:
            reasons.append("low_vocabulary_document")
        if _is_robust_outlier(item.char_count, char_stats):
            reasons.append("char_count_outlier")
        if _is_robust_outlier(item.token_count, token_stats):
            reasons.append("token_count_outlier")

        if reasons:
            outliers.append(DocumentOutlier(file_path=item.file_path, reasons=sorted(set(reasons))))

    return outliers


def _cluster_documents(
    features: list[_DocumentFeatures],
    similarity_threshold: float,
) -> list[DocumentCluster]:
    clusters: list[DocumentCluster] = []
    visited: set[int] = set()

    for index, item in enumerate(features):
        if index in visited or not item.signature_terms:
            continue

        component = {index}
        queue = [index]
        visited.add(index)

        while queue:
            current = queue.pop()
            for other_index, other in enumerate(features):
                if other_index in visited or other_index == current or not other.signature_terms:
                    continue
                similarity = _jaccard(features[current].signature_terms, other.signature_terms)
                if similarity >= similarity_threshold:
                    visited.add(other_index)
                    component.add(other_index)
                    queue.append(other_index)

        if len(component) < 2:
            continue

        members = [features[i] for i in sorted(component)]
        shared = set(members[0].signature_terms)
        for member in members[1:]:
            shared &= member.signature_terms

        similarities: list[float] = []
        member_list = list(component)
        for left in range(len(member_list)):
            for right in range(left + 1, len(member_list)):
                similarities.append(
                    _jaccard(
                        features[member_list[left]].signature_terms,
                        features[member_list[right]].signature_terms,
                    )
                )

        average_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        clusters.append(
            DocumentCluster(
                member_paths=[member.file_path for member in members],
                shared_terms=sorted(shared)[:8],
                average_similarity=round(average_similarity, 3),
            )
        )

    return clusters


def _tokenize(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_PATTERN.findall(text)]


def _signature_terms(tokens: list[str]) -> set[str]:
    filtered = [token for token in tokens if len(token) >= 4 and not token.isdigit()]
    counts = Counter(filtered)
    return {term for term, _ in counts.most_common(DEFAULT_SIGNATURE_TERMS)}


def _non_empty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _repeated_line_ratio(text: str, line_count: int) -> float:
    if line_count <= 1:
        return 0.0
    normalized = [re.sub(r"\s+", " ", line.strip().casefold()) for line in text.splitlines() if line.strip()]
    if not normalized:
        return 0.0
    counts = Counter(normalized)
    repeated = sum(count for count in counts.values() if count > 1)
    return repeated / len(normalized)


def _numeric_ratio(text: str) -> float:
    if not text:
        return 0.0
    digits = sum(1 for char in text if char.isdigit())
    return digits / len(text)


def _robust_stats(values: list[int]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    ordered = sorted(values)
    median = _median(ordered)
    deviations = [abs(value - median) for value in ordered]
    mad = _median(sorted(deviations))
    return median, mad


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    middle = len(values) // 2
    if len(values) % 2:
        return float(values[middle])
    return (values[middle - 1] + values[middle]) / 2.0


def _is_robust_outlier(value: int, stats: tuple[float, float], threshold: float = 3.5) -> bool:
    median, mad = stats
    if mad == 0:
        if median == 0:
            return value > 0
        return value >= (median * 3) or value <= (median / 3)
    robust_z = 0.6745 * (value - median) / mad
    return math.fabs(robust_z) > threshold


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)
