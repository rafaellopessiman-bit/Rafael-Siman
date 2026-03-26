from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from src.knowledge.catalog import build_catalog_text, build_indexable_text

from .chunking import chunk_text
from .path_utils import normalize_path, normalize_paths

SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".docx", ".xlsx"}


@dataclass(frozen=True)
class UpsertResult:
    action: str
    document_id: int
    chunks_written: int
    normalized_path: str


@dataclass(frozen=True)
class DocumentAuditHistoryRecord:
    file_path: str
    audit_timestamp: str
    flags: list[str]
    remediation_action: str
    should_index: bool
    source_command: str
    duplicate_of: str | None = None


@dataclass(frozen=True)
class ScheduleRunRecord:
    run_timestamp: str
    status: str
    jobs: list[str]
    summary: dict[str, Any]
    artifacts: dict[str, Any]


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
                    file_name TEXT NOT NULL DEFAULT '',
                    file_extension TEXT NOT NULL DEFAULT '',
                    content_hash TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    catalog_text TEXT NOT NULL DEFAULT '',
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

                CREATE TABLE IF NOT EXISTS document_audit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    audit_timestamp TEXT NOT NULL,
                    flags_json TEXT NOT NULL DEFAULT '[]',
                    remediation_action TEXT NOT NULL,
                    should_index INTEGER NOT NULL DEFAULT 1,
                    source_command TEXT NOT NULL DEFAULT 'audit',
                    duplicate_of TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_document_audit_history_file_path
                    ON document_audit_history(file_path);

                CREATE INDEX IF NOT EXISTS idx_document_audit_history_timestamp
                    ON document_audit_history(audit_timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_document_audit_history_lookup
                    ON document_audit_history(file_path, source_command, remediation_action, audit_timestamp DESC, id DESC);

                CREATE TABLE IF NOT EXISTS schedule_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    jobs_json TEXT NOT NULL DEFAULT '[]',
                    summary_json TEXT NOT NULL DEFAULT '{}',
                    artifacts_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_schedule_runs_timestamp
                    ON schedule_runs(run_timestamp DESC, id DESC);

                CREATE INDEX IF NOT EXISTS idx_schedule_runs_status
                    ON schedule_runs(status, run_timestamp DESC);

                CREATE TABLE IF NOT EXISTS watch_snapshots (
                    watch_path TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                );
                """
            )

            self._ensure_documents_schema(conn)

            # Populate FTS index if empty
            self._rebuild_fts_index(conn)

    def upsert_document(
        self,
        file_path: str | Path,
        content: str,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> UpsertResult:
        normalized_path = normalize_path(file_path, base_dir=self.base_dir)
        normalized_metadata = self._normalize_metadata(file_path=file_path, metadata=metadata)
        indexable_content = build_indexable_text(content=content, metadata=normalized_metadata)
        metadata_json = json.dumps(normalized_metadata, ensure_ascii=False, sort_keys=True)
        catalog_text = build_catalog_text(normalized_metadata)
        content_hash = self._hash_content(f"{indexable_content}\n{metadata_json}")
        updated_at = self._utcnow()
        path_obj = Path(file_path)

        chunks = chunk_text(file_path=file_path, text=indexable_content)
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
                conn.execute(
                    """
                    UPDATE documents
                    SET file_name = ?, file_extension = ?, metadata_json = ?, catalog_text = ?
                    WHERE id = ?
                    """,
                    (path_obj.name, path_obj.suffix.lower(), metadata_json, catalog_text, document_id),
                )
                action = "inserted"
            else:
                document_id = int(existing["id"])
                if existing["content_hash"] == content_hash and not force:
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
                    SET content_hash = ?, updated_at = ?, file_name = ?, file_extension = ?, metadata_json = ?, catalog_text = ?
                    WHERE id = ?
                    """,
                    (content_hash, updated_at, path_obj.name, path_obj.suffix.lower(), metadata_json, catalog_text, document_id),
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

    def upsert_documents(self, documents: Iterable[Any], force: bool = False) -> list[UpsertResult]:
        results: list[UpsertResult] = []
        for item in documents:
            file_path, content, metadata = self._coerce_document(item)
            results.append(
                self.upsert_document(
                    file_path=file_path,
                    content=content,
                    metadata=metadata,
                    force=force,
                )
            )
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

    def record_audit_history(
        self,
        records: Iterable[DocumentAuditHistoryRecord],
    ) -> int:
        rows = list(records)
        if not rows:
            return 0

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO document_audit_history (
                    file_path,
                    audit_timestamp,
                    flags_json,
                    remediation_action,
                    should_index,
                    source_command,
                    duplicate_of,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        normalize_path(record.file_path, base_dir=self.base_dir),
                        record.audit_timestamp,
                        json.dumps(record.flags, ensure_ascii=False, sort_keys=True),
                        record.remediation_action,
                        1 if record.should_index else 0,
                        record.source_command,
                        normalize_path(record.duplicate_of, base_dir=self.base_dir)
                        if record.duplicate_of
                        else None,
                        self._utcnow(),
                    )
                    for record in rows
                ],
            )

        return len(rows)

    def fetch_audit_history(
        self,
        file_path: str | Path,
        limit: int = 20,
        offset: int = 0,
        source_command: str | None = None,
        remediation_action: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clause, parameters = self._build_audit_history_filters(
            file_path=file_path,
            source_command=source_command,
            remediation_action=remediation_action,
        )
        parameters.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT
                    file_path,
                    audit_timestamp,
                    flags_json,
                    remediation_action,
                    should_index,
                    source_command,
                    duplicate_of,
                    created_at
                FROM document_audit_history
                WHERE {where_clause}
                ORDER BY audit_timestamp DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                tuple(parameters),
            ).fetchall()

        return [
            {
                "file_path": row["file_path"],
                "audit_timestamp": row["audit_timestamp"],
                "flags": json.loads(row["flags_json"] or "[]"),
                "remediation_action": row["remediation_action"],
                "should_index": bool(row["should_index"]),
                "source_command": row["source_command"],
                "duplicate_of": row["duplicate_of"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def count_audit_history(
        self,
        file_path: str | Path,
        source_command: str | None = None,
        remediation_action: str | None = None,
    ) -> int:
        where_clause, parameters = self._build_audit_history_filters(
            file_path=file_path,
            source_command=source_command,
            remediation_action=remediation_action,
        )
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM document_audit_history
                WHERE {where_clause}
                """,
                tuple(parameters),
            ).fetchone()
        return int(row["total"] if row else 0)

    def summarize_audit_history(
        self,
        file_path: str | Path,
        source_command: str | None = None,
        remediation_action: str | None = None,
    ) -> dict[str, Any]:
        where_clause, parameters = self._build_audit_history_filters(
            file_path=file_path,
            source_command=source_command,
            remediation_action=remediation_action,
        )

        with self._connect() as conn:
            action_rows = conn.execute(
                f"""
                SELECT remediation_action, COUNT(*) AS total
                FROM document_audit_history
                WHERE {where_clause}
                GROUP BY remediation_action
                ORDER BY remediation_action
                """,
                tuple(parameters),
            ).fetchall()

            latest_row = conn.execute(
                f"""
                SELECT
                    audit_timestamp,
                    remediation_action,
                    should_index,
                    source_command,
                    duplicate_of,
                    flags_json
                FROM document_audit_history
                WHERE {where_clause}
                ORDER BY audit_timestamp DESC, id DESC
                LIMIT 1
                """,
                tuple(parameters),
            ).fetchone()

        latest_decision = None
        if latest_row is not None:
            latest_decision = {
                "audit_timestamp": latest_row["audit_timestamp"],
                "remediation_action": latest_row["remediation_action"],
                "should_index": bool(latest_row["should_index"]),
                "source_command": latest_row["source_command"],
                "duplicate_of": latest_row["duplicate_of"],
                "flags": json.loads(latest_row["flags_json"] or "[]"),
            }

        return {
            "action_counts": {
                row["remediation_action"]: int(row["total"])
                for row in action_rows
            },
            "latest_decision": latest_decision,
        }

    def fetch_latest_audit_decisions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH ranked_history AS (
                    SELECT
                        file_path,
                        audit_timestamp,
                        flags_json,
                        remediation_action,
                        should_index,
                        source_command,
                        duplicate_of,
                        created_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY file_path
                            ORDER BY audit_timestamp DESC, id DESC
                        ) AS row_number
                    FROM document_audit_history
                )
                SELECT
                    file_path,
                    audit_timestamp,
                    flags_json,
                    remediation_action,
                    should_index,
                    source_command,
                    duplicate_of,
                    created_at
                FROM ranked_history
                WHERE row_number = 1
                ORDER BY file_path
                """
            ).fetchall()

        return [
            {
                "file_path": row["file_path"],
                "audit_timestamp": row["audit_timestamp"],
                "flags": json.loads(row["flags_json"] or "[]"),
                "remediation_action": row["remediation_action"],
                "should_index": bool(row["should_index"]),
                "source_command": row["source_command"],
                "duplicate_of": row["duplicate_of"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def record_schedule_run(self, record: ScheduleRunRecord) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO schedule_runs (
                    run_timestamp,
                    status,
                    jobs_json,
                    summary_json,
                    artifacts_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.run_timestamp,
                    record.status,
                    json.dumps(record.jobs, ensure_ascii=False),
                    json.dumps(record.summary, ensure_ascii=False),
                    json.dumps(record.artifacts, ensure_ascii=False),
                    self._utcnow(),
                ),
            )
        return int(cursor.lastrowid)

    def update_schedule_run(self, run_id: int, summary: dict[str, Any], artifacts: dict[str, Any], status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE schedule_runs
                SET status = ?, summary_json = ?, artifacts_json = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(summary, ensure_ascii=False),
                    json.dumps(artifacts, ensure_ascii=False),
                    int(run_id),
                ),
            )

    def count_schedule_runs(self, status: str | None = None) -> int:
        where_clause = ""
        parameters: list[Any] = []
        if status:
            where_clause = "WHERE status = ?"
            parameters.append(status)

        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM schedule_runs
                {where_clause}
                """,
                tuple(parameters),
            ).fetchone()
        return int(row["total"] if row else 0)

    def fetch_schedule_runs(self, limit: int = 20, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        where_clause = ""
        parameters: list[Any] = []
        if status:
            where_clause = "WHERE status = ?"
            parameters.append(status)
        parameters.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, run_timestamp, status, jobs_json, summary_json, artifacts_json, created_at
                FROM schedule_runs
                {where_clause}
                ORDER BY run_timestamp DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                tuple(parameters),
            ).fetchall()

        return [
            {
                "id": int(row["id"]),
                "run_timestamp": row["run_timestamp"],
                "status": row["status"],
                "jobs": json.loads(row["jobs_json"] or "[]"),
                "summary": json.loads(row["summary_json"] or "{}"),
                "artifacts": json.loads(row["artifacts_json"] or "{}"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def summarize_schedule_runs(self, limit: int = 20, status: str | None = None) -> dict[str, Any]:
        where_clause = ""
        parameters: list[Any] = []
        if status:
            where_clause = "WHERE status = ?"
            parameters.append(status)
        parameters.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT status, run_timestamp
                FROM schedule_runs
                {where_clause}
                ORDER BY run_timestamp DESC, id DESC
                LIMIT ?
                """,
                tuple(parameters),
            ).fetchall()

        status_counts: dict[str, int] = {}
        latest_run_timestamp = None
        for index, row in enumerate(rows):
            status = str(row["status"])
            status_counts[status] = status_counts.get(status, 0) + 1
            if index == 0:
                latest_run_timestamp = row["run_timestamp"]

        return {
            "runs_total": len(rows),
            "status_counts": status_counts,
            "latest_run_timestamp": latest_run_timestamp,
        }

    def fetch_watch_snapshot(self, watch_path: str | Path) -> dict[str, tuple[int, int]]:
        normalized_watch_path = normalize_path(watch_path, base_dir=None)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT snapshot_json
                FROM watch_snapshots
                WHERE watch_path = ?
                """,
                (normalized_watch_path,),
            ).fetchone()

        if row is None:
            return {}

        try:
            raw_snapshot = json.loads(row["snapshot_json"] or "{}")
        except json.JSONDecodeError:
            return {}

        if not isinstance(raw_snapshot, dict):
            return {}

        snapshot: dict[str, tuple[int, int]] = {}
        for file_path, value in raw_snapshot.items():
            if not isinstance(file_path, str):
                continue
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                continue
            try:
                snapshot[file_path] = (int(value[0]), int(value[1]))
            except (TypeError, ValueError):
                continue
        return snapshot

    def upsert_watch_snapshot(self, watch_path: str | Path, snapshot: dict[str, tuple[int, int]]) -> None:
        normalized_watch_path = normalize_path(watch_path, base_dir=None)
        serializable_snapshot = {
            str(file_path): [int(value[0]), int(value[1])]
            for file_path, value in snapshot.items()
            if isinstance(value, tuple) and len(value) == 2
        }

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO watch_snapshots (watch_path, snapshot_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(watch_path) DO UPDATE SET
                    snapshot_json = excluded.snapshot_json,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_watch_path,
                    json.dumps(serializable_snapshot, ensure_ascii=False, sort_keys=True),
                    self._utcnow(),
                ),
            )

    def _build_audit_history_filters(
        self,
        file_path: str | Path,
        source_command: str | None = None,
        remediation_action: str | None = None,
    ) -> tuple[str, list[Any]]:
        normalized_path = normalize_path(file_path, base_dir=self.base_dir)
        filters = ["file_path = ?"]
        parameters: list[Any] = [normalized_path]

        if source_command:
            filters.append("source_command = ?")
            parameters.append(source_command)

        if remediation_action:
            filters.append("remediation_action = ?")
            parameters.append(remediation_action)

        return " AND ".join(filters), parameters

    def fetch_documents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, file_path, content_hash, updated_at
                    , file_name, file_extension, metadata_json, catalog_text
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
                        "file_name": row["file_name"],
                        "file_extension": row["file_extension"],
                        "content_hash": row["content_hash"],
                        "metadata": self._deserialize_metadata(row["metadata_json"]),
                        "catalog_text": row["catalog_text"],
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
                    d.file_name,
                    d.file_extension,
                    d.metadata_json,
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
                "file_name": row["file_name"],
                "file_extension": row["file_extension"],
                "metadata": self._deserialize_metadata(row["metadata_json"]),
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
    def _deserialize_metadata(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _normalize_metadata(file_path: str | Path, metadata: dict[str, Any] | None) -> dict[str, Any]:
        path = Path(file_path)
        base = {
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
        }
        if metadata:
            base.update(metadata)
        return base

    @staticmethod
    def _ensure_documents_schema(conn: sqlite3.Connection) -> None:
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        required_columns = {
            "file_name": "ALTER TABLE documents ADD COLUMN file_name TEXT NOT NULL DEFAULT ''",
            "file_extension": "ALTER TABLE documents ADD COLUMN file_extension TEXT NOT NULL DEFAULT ''",
            "metadata_json": "ALTER TABLE documents ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
            "catalog_text": "ALTER TABLE documents ADD COLUMN catalog_text TEXT NOT NULL DEFAULT ''",
        }
        for name, statement in required_columns.items():
            if name not in columns:
                conn.execute(statement)

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
    def _coerce_document(item: Any) -> tuple[str | Path, str, dict[str, Any] | None]:
        if isinstance(item, tuple) and len(item) >= 2:
            metadata = item[2] if len(item) >= 3 and isinstance(item[2], dict) else None
            return item[0], item[1], metadata

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
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else None
            return path, content, metadata

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

        metadata = getattr(item, "metadata", None)
        metadata = metadata if isinstance(metadata, dict) else None
        return path, content, metadata


# =========================
# Compatibility wrappers
# =========================

def initialize_database(db_path, base_dir=None):
    DocumentStore(db_path=db_path, base_dir=base_dir).initialize_database()


def fetch_all_documents(db_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_documents()


def fetch_all_chunks(db_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_all_chunks()


def upsert_documents(db_path, documents, base_dir=None, force=False):
    return DocumentStore(db_path=db_path, base_dir=base_dir).upsert_documents(documents, force=force)


def sync_local_files(db_path, current_file_paths, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).sync_local_files(current_file_paths)


def record_document_audit_history(db_path, records, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).record_audit_history(records)


def fetch_document_audit_history(
    db_path,
    file_path,
    base_dir=None,
    limit=20,
    offset=0,
    source_command=None,
    remediation_action=None,
):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_audit_history(
        file_path,
        limit=limit,
        offset=offset,
        source_command=source_command,
        remediation_action=remediation_action,
    )


def count_document_audit_history(
    db_path,
    file_path,
    base_dir=None,
    source_command=None,
    remediation_action=None,
):
    return DocumentStore(db_path=db_path, base_dir=base_dir).count_audit_history(
        file_path,
        source_command=source_command,
        remediation_action=remediation_action,
    )


def summarize_document_audit_history(
    db_path,
    file_path,
    base_dir=None,
    source_command=None,
    remediation_action=None,
):
    return DocumentStore(db_path=db_path, base_dir=base_dir).summarize_audit_history(
        file_path,
        source_command=source_command,
        remediation_action=remediation_action,
    )


def fetch_latest_document_audit_decisions(db_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_latest_audit_decisions()


def record_schedule_run(db_path, record, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).record_schedule_run(record)


def update_schedule_run(db_path, run_id, summary, artifacts, status, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).update_schedule_run(run_id, summary, artifacts, status)


def count_schedule_runs(db_path, base_dir=None, status=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).count_schedule_runs(status=status)


def fetch_schedule_runs(db_path, base_dir=None, limit=20, offset=0, status=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_schedule_runs(limit=limit, offset=offset, status=status)


def summarize_schedule_runs(db_path, base_dir=None, limit=20, status=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).summarize_schedule_runs(limit=limit, status=status)


def fetch_watch_snapshot(db_path, watch_path, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).fetch_watch_snapshot(watch_path)


def upsert_watch_snapshot(db_path, watch_path, snapshot, base_dir=None):
    return DocumentStore(db_path=db_path, base_dir=base_dir).upsert_watch_snapshot(watch_path, snapshot)
