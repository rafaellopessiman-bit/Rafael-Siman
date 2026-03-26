from __future__ import annotations

import re
from pathlib import Path
from typing import Any


THEME_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ia_aplicada", ("llm", "rag", "agent", "agents", "prompt", "embedding", "vector", "nlp", "machine learning", "deep learning", "artificial intelligence")),
    ("arquitetura", ("architecture", "clean architecture", "ddd", "domain-driven", "microservice", "microservices", "distributed systems", "design pattern", "system design", "cqrs", "event sourcing")),
    ("backend", ("api", "rest", "grpc", "backend", "server", "nestjs", "node", "django", "flask", "fastapi", "spring", "http")),
    ("bancos", ("sql", "mongodb", "postgres", "postgresql", "mysql", "redis", "database", "query", "index", "transaction")),
    ("cloud", ("docker", "kubernetes", "aws", "azure", "gcp", "cloud", "devops", "terraform", "observability", "linux")),
    ("debugging", ("debug", "debugging", "troubleshoot", "profiling", "performance", "latency", "trace", "testing")),
)

STACK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("python", r"\bpython\b"),
    ("typescript", r"\btypescript\b|\bts\b"),
    ("javascript", r"\bjavascript\b|\bnode(?:\.js)?\b"),
    ("java", r"\bjava\b|\bspring\b"),
    ("csharp", r"\bc#\b|\b\.net\b|\bdotnet\b"),
    ("go", r"\bgo\b|\bgolang\b"),
    ("rust", r"\brust\b"),
    ("nestjs", r"\bnestjs\b|\bnest\b"),
    ("django", r"\bdjango\b"),
    ("fastapi", r"\bfastapi\b"),
    ("flask", r"\bflask\b"),
    ("mongodb", r"\bmongodb\b|\batlas\b"),
    ("postgres", r"\bpostgres(?:ql)?\b"),
    ("mysql", r"\bmysql\b"),
    ("redis", r"\bredis\b"),
    ("docker", r"\bdocker\b"),
    ("kubernetes", r"\bkubernetes\b|\bk8s\b"),
    ("aws", r"\baws\b"),
    ("azure", r"\bazure\b"),
    ("gcp", r"\bgcp\b|\bgoogle cloud\b"),
    ("rag", r"\brag\b|retrieval augmented generation"),
    ("langchain", r"\blangchain\b"),
)

CONCEPT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("clean_architecture", r"clean architecture"),
    ("ddd", r"\bddd\b|domain-driven design"),
    ("cqrs", r"\bcqrs\b"),
    ("event_sourcing", r"event sourcing"),
    ("microservices", r"microservices?"),
    ("observability", r"observability|metrics|tracing|logging"),
    ("testing", r"\btesting\b|\btest\b|pytest|jest|tdd"),
    ("debugging", r"debugging|troubleshooting|profiling"),
    ("prompt_engineering", r"prompt engineering|prompting"),
    ("embeddings", r"embedding|embeddings"),
    ("vector_search", r"vector search|similarity search"),
    ("agents", r"agentic|agents? orchestration|multi-agent|agent"),
    ("rag", r"\brag\b|retrieval augmented generation"),
    ("distributed_systems", r"distributed systems?"),
    ("performance", r"performance|latency|throughput|optimization"),
)

MAX_STACK_ITEMS = 8
MAX_CONCEPT_ITEMS = 10


def infer_document_metadata(
    file_path: str | Path,
    content: str,
    base_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(file_path)
    metadata = dict(base_metadata or {})
    text = _normalize_text(f"{path.stem}\n{' '.join(path.parts)}\n{content[:8000]}")

    title = _clean_value(metadata.get("title")) or _humanize_title(path.stem)
    author = _clean_value(metadata.get("author")) or _infer_author_from_stem(path.stem)
    theme = _clean_value(metadata.get("theme")) or _infer_theme(text)
    stack = _normalize_list(metadata.get("stack")) or _infer_matches(text, STACK_PATTERNS, MAX_STACK_ITEMS)
    concepts = _normalize_list(metadata.get("concepts")) or _infer_matches(text, CONCEPT_PATTERNS, MAX_CONCEPT_ITEMS)

    metadata.update(
        {
            "title": title,
            "author": author,
            "theme": theme,
            "stack": stack,
            "concepts": concepts,
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
        }
    )

    return {key: value for key, value in metadata.items() if value not in (None, "", [], {})}


def build_catalog_text(metadata: dict[str, Any] | None) -> str:
    if not metadata:
        return ""

    lines: list[str] = []

    title = _clean_value(metadata.get("title"))
    if title:
        lines.append(f"Titulo: {title}")

    author = _clean_value(metadata.get("author"))
    if author:
        lines.append(f"Autor: {author}")

    theme = _clean_value(metadata.get("theme"))
    if theme:
        lines.append(f"Tema: {theme}")

    page_count = metadata.get("page_count")
    if isinstance(page_count, int) and page_count > 0:
        lines.append(f"Paginas: {page_count}")

    stack = _normalize_list(metadata.get("stack"))
    if stack:
        lines.append("Stack: " + ", ".join(stack))

    concepts = _normalize_list(metadata.get("concepts"))
    if concepts:
        lines.append("Conceitos: " + ", ".join(concepts))

    return "\n".join(lines)


def build_indexable_text(content: str, metadata: dict[str, Any] | None = None) -> str:
    clean_content = (content or "").strip()
    catalog_text = build_catalog_text(metadata)

    if not catalog_text:
        return clean_content

    if not clean_content:
        return catalog_text

    return f"[CATALOGO]\n{catalog_text}\n[/CATALOGO]\n\n{clean_content}"


def _infer_theme(text: str) -> str | None:
    best_theme = None
    best_score = 0

    for theme, keywords in THEME_RULES:
        score = sum(1 for keyword in keywords if keyword in text)
        if score > best_score:
            best_theme = theme
            best_score = score

    return best_theme


def _infer_matches(text: str, patterns: tuple[tuple[str, str], ...], limit: int) -> list[str]:
    matches: list[str] = []
    for label, pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matches.append(label)
        if len(matches) >= limit:
            break
    return matches


def _infer_author_from_stem(stem: str) -> str | None:
    parts = [part.strip() for part in re.split(r"\s+-\s+|\s+—\s+|\s+_\s+", stem) if part.strip()]
    if len(parts) < 2:
        return None
    candidate = parts[-1]
    if len(candidate.split()) > 5:
        return None
    return candidate


def _humanize_title(stem: str) -> str:
    text = re.sub(r"[_\.]+", " ", stem)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    return text or stem


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).casefold()


def _clean_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[,;|]", value)
    else:
        items = list(value)

    normalized: list[str] = []
    for item in items:
        text = _clean_value(item)
        if text and text not in normalized:
            normalized.append(text)
    return normalized
