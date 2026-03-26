#Requires -Version 5.1
param(
    [string]$DatabasePath = 'data\ebooks_catalog.db'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'
$DbFullPath = Join-Path $Root $DatabasePath

Write-Host "`n=== Atlas Local | Catalog Stats ===" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host '[ERRO] Python venv nao encontrada.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DbFullPath)) {
    Write-Host "Banco nao encontrado: $DbFullPath" -ForegroundColor Yellow
    exit 2
}

$pythonSnippet = @'
import sqlite3
from pathlib import Path

db_path = Path(r'__DB_PATH__')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

docs_total = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
chunks_total = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
pdf_total = conn.execute("SELECT COUNT(*) FROM documents WHERE file_extension = '.pdf'").fetchone()[0]

themes = conn.execute(
    """
    SELECT COALESCE(json_extract(metadata_json, '$.theme'), 'sem_tema') AS theme, COUNT(*) AS total
    FROM documents
    GROUP BY theme
    ORDER BY total DESC, theme ASC
    LIMIT 10
    """
).fetchall()

stacks = conn.execute(
    """
    SELECT value AS stack, COUNT(*) AS total
    FROM documents, json_each(metadata_json, '$.stack')
    GROUP BY value
    ORDER BY total DESC, stack ASC
    LIMIT 10
    """
).fetchall()

print(f'Documentos: {docs_total}')
print(f'Chunks: {chunks_total}')
print(f'PDFs: {pdf_total}')
print('--- Top themes ---')
for row in themes:
    print(f"{row['theme']}: {row['total']}")
print('--- Top stacks ---')
for row in stacks:
    print(f"{row['stack']}: {row['total']}")
'@

$pythonSnippet = $pythonSnippet.Replace('__DB_PATH__', $DbFullPath)

$tempScript = Join-Path $env:TEMP 'atlas_ebooks_catalog_stats.py'
Set-Content -Path $tempScript -Value $pythonSnippet -Encoding UTF8

try {
    & $PythonExe $tempScript
}
finally {
    Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
}

Write-Host ''
