from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Iterable

from .chunking import chunk_text
from .path_utils import normalize_path, normalize_paths


SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv"}


@dataclass(frozen=True)
class UpsertResult:
    action: str
    document_id: int
    chunks_written: int
    normalized_path: str


class DocumentStore:
    def __init__(self, db_path: str | Path, base_dir: str | Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.base_dir = Path(base_dir) if base_dir is not None else None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    def initialize_database(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    content_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    UNIQUE(document_id, chunk_index)
                );

                CREATE INDEX IF NOT EXISTS idx_documents_file_path
                    ON documents(file_path);

                CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                    ON chunks(document_id);

                CREATE INDEX IF NOT EXISTS idx_chunks_document_chunk_index
                    ON chunks(document_id, chunk_index);

                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    text,
                    content='chunks',
                    content_rowid='id'
                );
                """
            )
            
            # Populate FTS index if empty
            self._rebuild_fts_index(conn)

    def upsert_document(self, file_path: str | Path, content: str) -> UpsertResult:
        normalized_path = normalize_path(file_path, base_dir=self.base_dir)
        content_hash = self._hash_content(content)
        updated_at = self._utcnow()

        chunks = chunk_text(file_path=file_path, text=content)
        if not chunks:
            chunks = [""]

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, content_hash FROM documents WHERE file_path = ?",
                (normalized_path,),
            ).fetchone()

            if existing is None:
                cursor = conn.execute(
                    """
                    INSERT INTO documents (file_path, content_hash, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_path, content_hash, updated_at),
                )
                document_id = int(cursor.lastrowid)
                action = "inserted"
            else:
                document_id = int(existing["id"])
                if existing["content_hash"] == content_hash:
                    existing_chunk_count = conn.execute(
                        "SELECT COUNT(*) AS total FROM chunks WHERE document_id = ?",
                        (document_id,),
                    ).fetchone()["total"]
                    return UpsertResult(
                        action="unchanged",
                        document_id=document_id,
                        chunks_written=int(existing_chunk_count),
                        normalized_path=normalized_path,
                    )

                conn.execute(
                    """
                    UPDATE documents
                    SET content_hash = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (content_hash, updated_at, document_id),
                )
                # Remove old chunks from both tables
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                conn.execute(
                    """
                    DELETE FROM chunks_fts
                    WHERE rowid NOT IN (
                        SELECT id FROM chunks
                    )
                    """
                )
                action = "updated"

            conn.executemany(
                """
                INSERT INTO chunks (document_id, chunk_index, text)
                VALUES (?, ?, ?)
                """,
                [(document_id, index, chunk) for index, chunk in enumerate(chunks)],
            )
            
            # Update FTS index with new chunks
            conn.execute(
                """
                INSERT INTO chunks_fts(rowid, text)
                SELECT id, text FROM chunks
                WHERE document_id = ?
                """,
                (document_id,),
            )

        return UpsertResult(
            action=action,
            document_id=document_id,
            chunks_written=len(chunks),
            normalized_path=normalized_path,
        )

    def upsert_documents(self, documents: Iterable[Any]) -> list[UpsertResult]:
        results: list[UpsertResult] = []
        for item in documents:
            file_path, content = self._coerce_document(item)
            results.append(self.upsert_document(file_path=file_path, content=content))
        return results

    def remove_orphans(self, current_paths: Iterable[str | Path]) -> int:
        normalized_current = set(normalize_paths(current_paths, base_dir=self.base_dir))

        with self._connect() as conn:
            stored_paths = {
                row["file_path"]
                for row in conn.execute("SELECT file_path FROM documents").fetchall()
            }

            orphan_paths = sorted(stored_paths - normalized_current)

            if not orphan_paths:
                return 0

            placeholders = ", ".join("?" for _ in orphan_paths)
            conn.execute(
                f"DELETE FROM documents WHERE file_path IN ({placeholders})",
                orphan_paths,
            )

        return len(orphan_paths)

    def sync_local_files(self, current_file_paths: Iterable[str | Path]) -> int:
        return self.remove_orphans(current_file_paths)

    def fetch_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, content_hash, updated_at
                FROM documents
                ORDER BY file_path
                """
            ).fetchall()

            documents: list[dict[str, Any]] = []
            for row in rows:
                chunks = conn.execute(
                    """
                    SELECT text
                    FROM chunks
                    WHERE document_id = ?
                    ORDER BY chunk_index
                    """,
                    (row["id"],),
                ).fetchall()

                documents.append(
                    {
                        "id": int(row["id"]),
                        "file_path": row["file_path"],
                        "content_hash": row["content_hash"],
                        "updated_at": row["updated_at"],
                        "content": "\n\n".join(chunk["text"] for chunk in chunks),
                    }
                )

        return documents

    def fetch_all_chunks(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.text
                FROM chunks c
                INNER JOIN documents d ON d.id = c.document_id
                ORDER BY d.file_path, c.chunk_index
                """
            ).fetchall()
        return [row["text"] for row in rows]

    def fetch_chunks_with_metadata(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.file_path,
                    c.chunk_index,
                    c.text
                FROM chunks c
                INNER JOIN documents d ON d.id = c.document_id
                ORDER BY d.file_path, c.chunk_index
                """
            ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "document_id": int(row["document_id"]),
                "file_path": row["file_path"],
                "chunk_index": int(row["chunk_index"]),
                "text": row["text"],
            }
            for row in rows
        ]

    def count_documents(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM documents").fetchone()
        return int(row["total"])

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS total FROM chunks").fetchone()
        return int(row["total"])

    def search_chunks_by_text_fts(self, query_text: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Search chunks using SQLite FTS5 full-text search.
        Much faster than rebuilding BM25 corpus on every query.
        
        Returns chunks with relevance score.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id,
                    c.document_id,
                    d.file_path,
                    c.chunk_index,
                    c.text,
                    rank
                FROM chunks_fts
                INNER JOIN chunks c ON chunks_fts.rowid = c.id
                INNER JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query_text, limit),
            ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "document_id": int(row["document_id"]),
                "file_path": row["file_path"],
                "chunk_index": int(row["chunk_index"]),
                "text": row["text"],
                "score": float(row["rank"]),  # FTS rank is negative (more negative = better match)
                "content_preview": row["text"][:200] + ("..." if len(row["text"]) > 200 else ""),
            }
            for row in rows
        ]

    def _rebuild_fts_index(self, conn: sqlite3.Connection | None = None) -> None:
        """Rebuild FTS5 index from chunks table. Call after bulk updates."""
        should_close = False
        if conn is None:
            conn = self._connect()
            should_close = True
        
        try:
            # Clear and rebuild FTS index
            conn.execute("DELETE FROM chunks_fts")
            conn.execute(
                """
                INSERT INTO chunks_fts(rowid, text)
                SELECT id, text FROM chunks
                """
            )
        finally:
            if should_close:
                conn.close()

    def index_directory(self, documents_dir: str | Path) -> dict[str, int]:
        documents_root = Path(documents_dir)
        files = sorted(
            path
            for path in documents_root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        removed = self.remove_orphans(files)

        inserted = 0
        updated = 0
        unchanged = 0

        for file_path in files:
            content = self._read_text(file_path)
            result = self.upsert_document(file_path=file_path, content=content)
            if result.action == "inserted":
                inserted += 1
            elif result.action == "updated":
                updated += 1
            elif result.action == "unchanged":
                unchanged += 1

        return {
            "documents_seen": len(files),
            "documents_inserted": inserted,
            "documents_updated": updated,
            "documents_unchanged": unchanged,
            "documents_removed": removed,
            "chunks_total": self.count_chunks(),
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode=WAL")   # concurrent reads + one writer
        conn.execute("PRAGMA synchronous=NORMAL") # safe + ~2x faster than FULL
        return conn

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _utcnow() -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    @staticmethod
    def _read_text(file_path: Path) -> str:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return file_path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _coerce_document(item: Any) -> tuple[str | Path, str]:
        if isinstance(item, tuple) and len(item) >= 2:
            return item[0], item[1]

        if isinstance(item, dict):
            path = item.get("file_path", item.get("path"))
            if path is None:
                raise ValueError("Documento sem file_path/path")
            if "content" in item:
                content = item["content"]
            elif "text" in item:
                content = item["text"]
            else:
                raise ValueError("Documento sem content/text")
            return path, content

        path = getattr(item, "file_path", None)
        if path is None:
            path = getattr(item, "path", None)
        if path is None:
            raise ValueError("Objeto de documento sem file_path/path")

        if hasattr(item, "content"):
            content = getattr(item, "content")
        elif hasattr(item, "text"):
            content = getattr(item, "text")
        else:
            raise ValueError("Objeto de documento sem content/text")

        return path, content


# =========================
# Compatibility wrappers
# =========================

def initialize_database(db_path, base_dir=None):
    DocumentStore(db_path=db_path, base_dir=base_dir).initialize_database()


def fetch_all_documents(db_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_documents()


def fetch_all_chunks(db_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_all_chunks()


def upsert_documents(db_path, documents, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).upsert_documents(documents)


def sync_local_files(db_path, current_file_paths, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).sync_local_files(current_file_paths)
