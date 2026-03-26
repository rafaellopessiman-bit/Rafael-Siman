import sqlite3

conn = sqlite3.connect("data/ebooks_catalog.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    """
    SELECT c.text, rank
    FROM chunks_fts
    INNER JOIN chunks c ON chunks_fts.rowid = c.id
    INNER JOIN documents d ON d.id = c.document_id
    WHERE chunks_fts MATCH '"typescript" OR "javascript" OR "nodejs"'
    AND d.file_path LIKE '%1000 examples%'
    ORDER BY rank LIMIT 3
    """
).fetchall()
for r in rows:
    print(f"rank={float(r['rank']):.2f}")
    print(r["text"][:300])
    print()
conn.close()
