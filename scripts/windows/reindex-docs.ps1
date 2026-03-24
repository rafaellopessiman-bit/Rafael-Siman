#Requires -Version 5.1
<#
.SYNOPSIS
  Reindexação de documentos locais via CLI Python.
.DESCRIPTION
  Ativa a venv e executa python -m src.main index.
  Loga resultado em logs/maintenance.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogFile = Join-Path $Root 'logs\maintenance\reindex.log'

# Garantir pastas
$logDir = Join-Path $Root 'logs\maintenance'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Log([string]$Msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Msg" | Tee-Object -FilePath $LogFile -Append
}

Write-Host "`n=== Atlas Local | Reindex ===" -ForegroundColor Cyan

# Ativar venv
$venvActivate = Join-Path $Root '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $venvActivate)) {
    Write-Host '[ERRO] Python venv não encontrada. Execute bootstrap.ps1 primeiro.' -ForegroundColor Red
    exit 1
}

Log 'Iniciando reindexação...'

Push-Location $Root
try {
    & $venvActivate
    $output = python -m src.main index 2>&1 | Out-String
    Log $output
    Write-Host $output
} catch {
    Log "Falha: $_"
    Write-Host "[ERRO] $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

Log 'Reindexação concluída.'
Write-Host "Log: $LogFile`n" -ForegroundColor DarkGray
