"""Debug script to check raw FTS5 + BM25 + fusion scores for typescript query."""
import sqlite3
import json

DB = "data/ebooks_catalog.db"

# ── 1. Check raw FTS5 chunk-level for top docs ──
def raw_fts(query_str, limit=20):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT d.file_path, c.text, rank
        FROM chunks_fts
        INNER JOIN chunks c ON chunks_fts.rowid = c.id
        INNER JOIN documents d ON d.id = c.document_id
        WHERE chunks_fts MATCH ?
        ORDER BY rank LIMIT ?
    """, (query_str, limit)).fetchall()
    conn.close()
    return rows

fts_query = '"typescript" OR "javascript" OR "nodejs"'
rows = raw_fts(fts_query, limit=20)
print("=== RAW FTS5 (limit=20) ===")
agg = {}
for i, r in enumerate(rows, 1):
    fp = r["file_path"]
    sc = abs(float(r["rank"]))
    if fp not in agg:
        agg[fp] = {"first_rank": i, "max_score": sc}
    agg[fp]["max_score"] = max(agg[fp]["max_score"], sc)

for fp in sorted(agg, key=lambda x: (agg[x]["first_rank"], -agg[x]["max_score"])):
    name = fp.replace("\\", "/").split("/")[-1]
    a = agg[fp]
    print(f"  rank={a['first_rank']:2d}  score={a['max_score']:7.2f}  {name}")

# ── 2. Check BM25 scores for the top files ──
print("\n=== BM25 SCORES (expanded query) ===")
from src.knowledge.retriever import _expand_query, _tokenize, _retrieve_by_bm25
from src.storage.document_store import DocumentStore

expanded = _expand_query("typescript javascript nodejs")
print(f"Expanded: {expanded[:200]}")

store = DocumentStore(db_path=DB)
documents = store.fetch_documents()
bm25_results = _retrieve_by_bm25(expanded, documents, top_k=10)

for d in bm25_results[:8]:
    name = str(d.get("file_path", "")).replace("\\", "/").split("/")[-1]
    print(f"  bm25_score={float(d.get('score',0)):7.2f}  {name}")

# ── 3. Check metadata for key files ──
print("\n=== METADATA ===")
conn = sqlite3.connect(DB)
for fp_like in ['angular2notes%', 'effective typescript%']:
    row = conn.execute("SELECT file_path, metadata_json FROM documents WHERE file_path LIKE ?", (f'%{fp_like}',)).fetchone()
    if row:
        md = json.loads(row[1]) if row[1] else {}
        print(f"  {row[0].split('/')[-1]}: stack={md.get('stack')}, theme={md.get('theme')}, concepts={md.get('concepts')}")
conn.close()

# ── 4. Simulate fusion ──
print("\n=== FUSION SIMULATION ===")
from src.knowledge.retriever import _aggregate_fts_results, _fuse_rankings

fts_rows_raw = raw_fts(fts_query, limit=20)
# Convert to dict list similar to search_chunks_by_text_fts
fts_results_list = [
    {"id": 0, "document_id": 0, "file_path": r["file_path"],
     "chunk_index": 0, "text": r["text"], "score": float(r["rank"]),
     "content_preview": r["text"][:200]} for r in fts_rows_raw
]
fts_aggregated = _aggregate_fts_results(fts_results_list, documents)
print("FTS aggregated order:")
for d in fts_aggregated[:6]:
    name = str(d.get("file_path", "")).replace("\\", "/").split("/")[-1]
    print(f"  fts_rank={d.get('_fts_rank')}  score={float(d.get('score',0)):7.2f}  {name}")

query_terms = set(_tokenize(expanded))
fused = _fuse_rankings(fts_aggregated, bm25_results, top_k=5, query_terms=query_terms)
print("\nFused results:")
for d in fused[:6]:
    name = str(d.get("file_path", "")).replace("\\", "/").split("/")[-1]
    print(f"  final_score={float(d.get('score',0)):7.2f}  {name}")
