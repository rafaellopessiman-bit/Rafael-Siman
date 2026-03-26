#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LockFile = Join-Path $LogDir 'ebooks-index.lock.json'
$LogFile = Join-Path $LogDir 'ebooks-index.log'

function Log([string]$Message) {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$timestamp  $Message" | Tee-Object -FilePath $LogFile -Append | Out-Host
}

Write-Host "`n=== Atlas Local | Parar Indexacao Biblioteca Tecnica ===" -ForegroundColor Cyan

$targets = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(?:\.exe)?$' -and
    $_.CommandLine -match '-m\s+src\.main\s+index' -and
    $_.CommandLine -match '--db-path\s+data[\\/]ebooks_catalog\.db'
})

if ($targets.Count -eq 0) {
    Write-Host 'Nenhum processo de indexacao da biblioteca tecnica encontrado.' -ForegroundColor DarkGray
    if (Test-Path $LockFile) {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    }
    exit 0
}

$processIds = $targets | Select-Object -ExpandProperty ProcessId
Write-Host "Processos encontrados: $($processIds -join ', ')" -ForegroundColor Yellow

foreach ($targetProcessId in $processIds) {
    try {
        Stop-Process -Id $targetProcessId -Force -ErrorAction Stop
        Log "Processo de indexacao encerrado. PID=$targetProcessId"
    }
    catch {
        if (-not (Get-Process -Id $targetProcessId -ErrorAction SilentlyContinue)) {
            Log "Processo ja havia sido encerrado. PID=$targetProcessId"
            continue
        }

        Write-Host "[ERRO] Falha ao encerrar PID ${targetProcessId}: $($_.Exception.Message)" -ForegroundColor Red
        throw
    }
}

if (Test-Path $LockFile) {
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    Log 'Lock file da biblioteca tecnica removido.'
}

Write-Host 'Indexacao da biblioteca tecnica interrompida.' -ForegroundColor Green
Write-Host ''
