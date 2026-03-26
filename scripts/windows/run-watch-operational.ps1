#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db',
    [int]$IntervalSeconds = 30,
    [int]$MaxCycles = 0,
    [ValidateSet('manual', 'ocr-required', 'full-auto')]
    [string]$RemediationPolicy = 'full-auto',
    [string]$PdfOcrCommand = 'ocrmypdf',
    [string]$PdfOcrLanguage = 'eng',
    [string]$ImageOcrCommand = 'tesseract',
    [string]$ImageOcrLanguage = 'eng',
    [string]$IsolateFlags = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LogFile = Join-Path $LogDir 'watch-operational.log'
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Log([string]$Message) {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$timestamp  $Message" | Tee-Object -FilePath $LogFile -Append | Out-Host
}

Write-Host "`n=== Atlas Local | Watch Operacional ===" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host '[ERRO] Python venv nao encontrada. Execute bootstrap.ps1 primeiro.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SourcePath)) {
    Write-Host "[ERRO] Pasta da biblioteca nao encontrada: $SourcePath" -ForegroundColor Red
    exit 1
}

$arguments = @(
    '-m', 'src.main', 'watch',
    '--path', $SourcePath,
    '--db-path', $DatabasePath,
    '--interval-seconds', $IntervalSeconds,
    '--remediation-policy', $RemediationPolicy,
    '--pdf-ocr-command', $PdfOcrCommand,
    '--pdf-ocr-language', $PdfOcrLanguage,
    '--image-ocr-command', $ImageOcrCommand,
    '--image-ocr-language', $ImageOcrLanguage
)

if ($MaxCycles -gt 0) {
    $arguments += @('--max-cycles', $MaxCycles)
}

if ($IsolateFlags) {
    $arguments += @('--isolate-flags', $IsolateFlags)
}

Push-Location $Root
try {
    Log "Origem: $SourcePath"
    Log "Banco: $DatabasePath"
    Log "IntervalSeconds: $IntervalSeconds"
    Log "MaxCycles: $MaxCycles"
    Log "RemediationPolicy: $RemediationPolicy"

    $output = & $PythonExe @arguments 2>&1
    $exitCode = $LASTEXITCODE

    if ($output) {
        Log (($output | Out-String).TrimEnd())
    }

    if ($exitCode -ne 0) {
        Log "Watch operacional finalizado com erro. ExitCode=$exitCode"
        exit $exitCode
    }

    Log 'Watch operacional concluido com sucesso.'
}
finally {
    Pop-Location
}

Write-Host "`nRotina concluida. Log: $LogFile`n" -ForegroundColor Green
