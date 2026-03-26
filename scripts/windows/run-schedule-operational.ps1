#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db',
    [string]$OutputDir = 'data\processados\schedule',
    [string]$EvalQueriesPath = 'data\eval_queries.json',
    [string]$EvalBaselinePath = 'data\eval_baseline.json',
    [int]$EvalTopK = 5,
    [string]$NotifyWebhookUrl = '',
    [ValidateSet('raw', 'teams', 'slack')]
    [string]$NotifyFormat = 'raw',
    [ValidateSet('always', 'on-error', 'on-issues', 'never')]
    [string]$NotifyOn = 'on-issues'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LogFile = Join-Path $LogDir 'schedule-operational.log'
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Log([string]$Message) {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$timestamp  $Message" | Tee-Object -FilePath $LogFile -Append | Out-Host
}

Write-Host "`n=== Atlas Local | Schedule Operacional ===" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host '[ERRO] Python venv nao encontrada. Execute bootstrap.ps1 primeiro.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SourcePath)) {
    Write-Host "[ERRO] Pasta da biblioteca nao encontrada: $SourcePath" -ForegroundColor Red
    exit 1
}

$arguments = @(
    '-m', 'src.main', 'schedule',
    '--path', $SourcePath,
    '--db-path', $DatabasePath,
    '--jobs', 'audit', 'report', 'ocr-pending', 'evaluate',
    '--output-dir', $OutputDir,
    '--report-output', 'xlsx',
    '--reindex-after-ocr',
    '--eval-queries', $EvalQueriesPath,
    '--eval-baseline', $EvalBaselinePath,
    '--eval-top-k', $EvalTopK
)

if ($NotifyWebhookUrl) {
    $arguments += @('--notify-webhook-url', $NotifyWebhookUrl, '--notify-format', $NotifyFormat, '--notify-on', $NotifyOn)
}

Push-Location $Root
try {
    Log "Origem: $SourcePath"
    Log "Banco: $DatabasePath"
    Log "OutputDir: $OutputDir"
    Log "EvalQueries: $EvalQueriesPath"
    Log "EvalBaseline: $EvalBaselinePath"
    Log "NotifyFormat: $NotifyFormat"

    $output = & $PythonExe @arguments 2>&1
    $exitCode = $LASTEXITCODE

    if ($output) {
        Log (($output | Out-String).TrimEnd())
    }

    if ($exitCode -ne 0) {
        Log "Schedule operacional finalizado com erro. ExitCode=$exitCode"
        exit $exitCode
    }

    Log 'Schedule operacional concluido com sucesso.'
}
finally {
    Pop-Location
}

Write-Host "`nRotina concluida. Log: $LogFile`n" -ForegroundColor Green
