from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from src.storage.chunking import chunk_text
from src.storage.document_store import DocumentStore
from src.storage.path_utils import normalize_path


SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv"}
TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
DEFAULT_TOP_K = 3


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


class SimpleBM25:
    def __init__(self, corpus_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.corpus_tokens = corpus_tokens
        self.k1 = k1
        self.b = b
        self.doc_lens = [len(doc) for doc in corpus_tokens]
        self.avgdl = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0

        self.doc_freqs: Counter[str] = Counter()
        self.term_freqs: list[Counter[str]] = []

        for doc in corpus_tokens:
            tf = Counter(doc)
            self.term_freqs.append(tf)
            self.doc_freqs.update(tf.keys())

        self.num_docs = len(corpus_tokens)

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        if not self.corpus_tokens or not query_tokens:
            return [0.0] * self.num_docs

        scores: list[float] = []

        for doc_index, tf in enumerate(self.term_freqs):
            doc_len = self.doc_lens[doc_index]
            score = 0.0

            for token in query_tokens:
                term_frequency = tf.get(token, 0)
                if term_frequency == 0:
                    continue

                df = self.doc_freqs.get(token, 0)
                idf = math.log(1.0 + ((self.num_docs - df + 0.5) / (df + 0.5)))

                denominator = term_frequency + self.k1 * (
                    1.0 - self.b + self.b * (doc_len / self.avgdl if self.avgdl else 0.0)
                )

                score += idf * ((term_frequency * (self.k1 + 1.0)) / denominator)

            scores.append(score)

        return scores


def load_knowledge_documents(
    input_dir: str | Path,
    db_path: str | Path,
    base_dir: str | Path | None = None,
) -> list[dict]:
    chunks = load_knowledge_chunks(input_dir=input_dir, db_path=db_path, base_dir=base_dir)
    if not chunks:
        return []

    retrieval_source = chunks[0]["retrieval_source"]
    return _group_documents_from_chunks(chunks, retrieval_source=retrieval_source)


def load_knowledge_chunks(
    input_dir: str | Path,
    db_path: str | Path,
    base_dir: str | Path | None = None,
) -> list[dict]:
    base_dir = Path(base_dir) if base_dir is not None else Path(input_dir)

    sqlite_chunks = _load_chunks_from_sqlite(db_path=db_path, base_dir=base_dir)
    if sqlite_chunks:
        for chunk in sqlite_chunks:
            chunk["retrieval_source"] = "sqlite"
        return sqlite_chunks

    disk_chunks = _load_chunks_from_disk(input_dir=input_dir, base_dir=base_dir)
    for chunk in disk_chunks:
        chunk["retrieval_source"] = "disk"
    return disk_chunks


def retrieve_relevant_documents(
    query: str,
    input_dir: str | Path,
    db_path: str | Path,
    base_dir: str | Path | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    chunks = load_knowledge_chunks(input_dir=input_dir, db_path=db_path, base_dir=base_dir)
    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]
    tokenized_chunks = [tokenize(text) for text in texts]
    query_tokens = tokenize(query)

    bm25 = SimpleBM25(tokenized_chunks)
    scores = bm25.get_scores(query_tokens)

    if query_tokens and max(scores or [0.0]) <= 0.0:
        query_set = set(query_tokens)
        scores = [float(len(query_set.intersection(set(tokens)))) for tokens in tokenized_chunks]

    ranked = sorted(
        enumerate(chunks),
        key=lambda item: (-scores[item[0]], item[1]["file_path"], item[1]["chunk_index"]),
    )

    doc_scores: dict[str, float] = {}
    matched_chunks_by_doc: dict[str, list[str]] = defaultdict(list)

    for index, chunk in ranked:
        score = float(scores[index])
        if score <= 0 and doc_scores:
            continue

        file_path = chunk["file_path"]
        doc_scores[file_path] = max(doc_scores.get(file_path, 0.0), score)

        if len(matched_chunks_by_doc[file_path]) < 2 and chunk["text"] not in matched_chunks_by_doc[file_path]:
            matched_chunks_by_doc[file_path].append(chunk["text"])

        if len(doc_scores) >= top_k and all(
            fp in matched_chunks_by_doc and len(matched_chunks_by_doc[fp]) >= 1
            for fp in doc_scores
        ):
            break

    retrieval_source = chunks[0]["retrieval_source"]

    if not doc_scores:
        return _group_documents_from_chunks(chunks, retrieval_source=retrieval_source)[:top_k]

    documents = _group_documents_from_chunks(
        chunks,
        retrieval_source=retrieval_source,
        doc_scores=doc_scores,
        matched_chunks_by_doc=matched_chunks_by_doc,
    )

    filtered = [doc for doc in documents if doc["file_path"] in doc_scores]
    filtered.sort(key=lambda doc: (-doc["score"], doc["file_path"]))
    return filtered[:top_k]


search_documents = retrieve_relevant_documents


def build_answer_context(documents: Iterable[dict], max_chunks_per_document: int = 2) -> str:
    blocks: list[str] = []

    for document in documents:
        excerpts = document.get("matched_chunks") or [document.get("content", "")]
        excerpts = [excerpt.strip() for excerpt in excerpts if excerpt and excerpt.strip()]
        excerpts = excerpts[:max_chunks_per_document]

        block_lines = [f"Arquivo: {document.get('file_path', document.get('path', 'desconhecido'))}"]
        for excerpt in excerpts:
            block_lines.append(f"- {excerpt}")

        blocks.append("\n".join(block_lines))

    return "\n\n---\n\n".join(blocks)


def _load_chunks_from_sqlite(
    db_path: str | Path,
    base_dir: str | Path | None = None,
) -> list[dict]:
    store = DocumentStore(db_path=db_path, base_dir=base_dir)
    if store.count_chunks() == 0:
        return []
    return store.fetch_chunks_with_metadata()


def _load_chunks_from_disk(
    input_dir: str | Path,
    base_dir: str | Path,
) -> list[dict]:
    chunks: list[dict] = []

    for file_path in _iter_supported_files(input_dir):
        content = _read_text(file_path)
        normalized_path = normalize_path(file_path, base_dir=base_dir)
        for index, chunk in enumerate(chunk_text(file_path=file_path, text=content)):
            chunks.append(
                {
                    "file_path": normalized_path,
                    "chunk_index": index,
                    "text": chunk,
                }
            )

    return chunks


def _group_documents_from_chunks(
    chunks: list[dict],
    retrieval_source: str,
    doc_scores: dict[str, float] | None = None,
    matched_chunks_by_doc: dict[str, list[str]] | None = None,
) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk["file_path"]].append(chunk)

    documents: list[dict] = []

    for file_path, items in grouped.items():
        items.sort(key=lambda item: item["chunk_index"])
        content = "\n\n".join(item["text"] for item in items)
        matched_chunks = list((matched_chunks_by_doc or {}).get(file_path, []))
        preview_source = matched_chunks[0] if matched_chunks else items[0]["text"]

        documents.append(
            {
                "name": Path(file_path).name,
                "extension": Path(file_path).suffix,
                "size": len(content.encode("utf-8")),
                "size_bytes": len(content.encode("utf-8")),
                "path": file_path,
                "file_path": file_path,
                "content": content,
                "preview": preview_source.replace("\n", " ").strip()[:220],
                "score": float((doc_scores or {}).get(file_path, 0.0)),
                "matched_chunks": matched_chunks,
                "retrieval_source": retrieval_source,
            }
        )

    documents.sort(key=lambda doc: (-doc["score"], doc["file_path"]))
    return documents


def _iter_supported_files(input_dir: str | Path) -> list[Path]:
    root = Path(input_dir)
    if not root.exists():
        return []

    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def _read_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="utf-8", errors="ignore")


__all__ = [
    "DEFAULT_TOP_K",
    "SimpleBM25",
    "build_answer_context",
    "load_knowledge_chunks",
    "load_knowledge_documents",
    "retrieve_relevant_documents",
    "search_documents",
    "tokenize",
]
