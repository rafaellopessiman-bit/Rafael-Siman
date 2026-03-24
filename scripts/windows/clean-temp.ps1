#Requires -Version 5.1
<#
.SYNOPSIS
  Limpa arquivos temporários, logs antigos e caches expirados.
.PARAMETER DaysOld
  Remove logs com mais de N dias (padrão: 30).
#>
param(
    [int]$DaysOld = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Removed = 0

Write-Host "`n=== Atlas Local | Limpeza ===" -ForegroundColor Cyan

# --- data/temp ---
$tempDir = Join-Path $Root 'data\temp'
if (Test-Path $tempDir) {
    $tempFiles = @(Get-ChildItem $tempDir -File -Recurse -ErrorAction SilentlyContinue)
    foreach ($f in $tempFiles) {
        Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue
        $Removed++
    }
    Write-Host "  data\temp: $($tempFiles.Count) arquivos removidos" -ForegroundColor Green
} else {
    Write-Host '  data\temp: pasta não existe' -ForegroundColor DarkGray
}

# --- Logs antigos ---
$logsDir = Join-Path $Root 'logs'
if (Test-Path $logsDir) {
    $cutoff = (Get-Date).AddDays(-$DaysOld)
    $oldLogs = @(Get-ChildItem $logsDir -File -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff })
    foreach ($f in $oldLogs) {
        Remove-Item $f.FullName -Force -ErrorAction SilentlyContinue
        $Removed++
    }
    Write-Host "  logs (>$DaysOld dias): $($oldLogs.Count) arquivos removidos" -ForegroundColor Green
}

# --- __pycache__ ---
$pycacheDirs = @(Get-ChildItem $Root -Directory -Recurse -Filter '__pycache__' -ErrorAction SilentlyContinue)
foreach ($d in $pycacheDirs) {
    Remove-Item $d.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $Removed++
}
Write-Host "  __pycache__: $($pycacheDirs.Count) pastas removidas" -ForegroundColor Green

# --- .pytest_cache ---
$pytestCache = Join-Path $Root '.pytest_cache'
if (Test-Path $pytestCache) {
    Remove-Item $pytestCache -Recurse -Force -ErrorAction SilentlyContinue
    $Removed++
    Write-Host '  .pytest_cache: removido' -ForegroundColor Green
}

# --- Dangling Docker images ---
$dockerOk = $false
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    docker info 2>&1 | Out-Null
    $dockerOk = ($LASTEXITCODE -eq 0)
}
if ($dockerOk) {
    $dangling = docker images -f 'dangling=true' -q 2>$null
    if ($dangling) {
        docker image prune -f 2>&1 | Out-Null
        Write-Host '  Docker dangling images: removidas' -ForegroundColor Green
    } else {
        Write-Host '  Docker dangling images: nenhuma' -ForegroundColor DarkGray
    }
}

Write-Host "`nTotal de itens removidos: $Removed`n" -ForegroundColor Cyan
