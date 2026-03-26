#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'
$DbFullPath = Join-Path $Root $DatabasePath

Write-Host "`n=== Atlas Local | Consultas Biblioteca Tecnica ===" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host '[ERRO] Python venv nao encontrada.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DbFullPath)) {
    Write-Host "Banco nao encontrado: $DbFullPath" -ForegroundColor Yellow
    exit 2
}

$queries = @(
    'arquitetura clean architecture ddd',
    'mongodb indexing transactions',
    'rag agents embeddings',
    'debugging performance backend'
)

Push-Location $Root
try {
    foreach ($query in $queries) {
        Write-Host "`n--- Query: $query ---" -ForegroundColor Yellow
        & $PythonExe -m src.main ask $query --path $SourcePath --db-path $DatabasePath
    }
}
finally {
    Pop-Location
}

Write-Host ''
