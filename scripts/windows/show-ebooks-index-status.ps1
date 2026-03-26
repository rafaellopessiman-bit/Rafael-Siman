#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LockFile = Join-Path $LogDir 'ebooks-index.lock.json'
$LogFile = Join-Path $LogDir 'ebooks-index.log'
$DbPath = Join-Path $Root 'data\ebooks_catalog.db'

function Get-OrphanIndexProcesses() {
    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^python(?:\.exe)?$' -and
        $_.CommandLine -match '-m\s+src\.main\s+index' -and
        $_.CommandLine -match '--db-path\s+data[\\/]ebooks_catalog\.db'
    })
}

Write-Host "`n=== Atlas Local | Status Biblioteca Tecnica ===" -ForegroundColor Cyan

if (Test-Path $LockFile) {
    try {
        $lock = Get-Content $LockFile -Raw | ConvertFrom-Json
        $process = Get-Process -Id $lock.pid -ErrorAction SilentlyContinue

        if ($process) {
            $cpuValue = if ($null -ne $process.CPU) { [math]::Round($process.CPU, 1) } else { 0 }
            Write-Host "Status : rodando" -ForegroundColor Green
            Write-Host "PID    : $($lock.pid)" -ForegroundColor White
            Write-Host "Inicio : $($lock.startedAt)" -ForegroundColor White
            Write-Host "CPU(s) : $cpuValue" -ForegroundColor White
        }
        else {
            Write-Host 'Status : lock stale detectado' -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host 'Status : lock invalido' -ForegroundColor Yellow
    }
}
else {
    $orphanProcesses = @(Get-OrphanIndexProcesses)
    if ($orphanProcesses.Count -gt 0) {
        Write-Host 'Status : rodando sem lock ativo' -ForegroundColor Yellow
    }
    else {
        Write-Host 'Status : sem lock ativo' -ForegroundColor DarkGray
    }
}

$orphanProcesses = @(Get-OrphanIndexProcesses)
if ($orphanProcesses.Count -gt 0) {
    Write-Host "Processos de indexacao detectados: $($orphanProcesses.Count)" -ForegroundColor Yellow
    foreach ($proc in $orphanProcesses) {
        Write-Host "  PID $($proc.ProcessId) :: $($proc.CommandLine)" -ForegroundColor DarkGray
    }
}

if (Test-Path $DbPath) {
    $dbInfo = Get-Item $DbPath
    Write-Host "Banco  : $($dbInfo.FullName)" -ForegroundColor White
    Write-Host "Tamanho: $('{0:N0}' -f $dbInfo.Length) bytes" -ForegroundColor White
    Write-Host "Atualiz: $($dbInfo.LastWriteTime)" -ForegroundColor White
}
else {
    Write-Host 'Banco  : ainda nao materializado' -ForegroundColor Yellow
}

if (Test-Path $LogFile) {
    Write-Host "`n--- Ultimas linhas do log ---" -ForegroundColor Cyan
    Get-Content $LogFile -Tail 20
}

Write-Host ''
