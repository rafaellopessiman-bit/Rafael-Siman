#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db',
    [string]$ScheduleOutputDir = 'data\processados\schedule',
    [string]$EvalQueriesPath = 'data\eval_queries.json',
    [string]$EvalBaselinePath = 'data\eval_baseline.json',
    [string]$TaskPrefix = 'Atlas Local'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ReportDir = Join-Path $Root 'logs\diagnostics'
$ReportFile = Join-Path $ReportDir "operational_health_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$Pass = 0; $Warn = 0; $Fail = 0

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

function Write-Result([string]$Label, [string]$Status, [string]$Detail = '') {
    $color = switch ($Status) { 'OK' { 'Green' } 'WARN' { 'Yellow' } default { 'Red' } }
    $line = "[$Status] $Label"
    if ($Detail) { $line += " -- $Detail" }
    Write-Host "  $line" -ForegroundColor $color
    $line | Out-File -FilePath $ReportFile -Append -Encoding utf8
    switch ($Status) { 'OK' { $script:Pass++ } 'WARN' { $script:Warn++ } default { $script:Fail++ } }
}

function Test-CommandAvailable([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "`n=== Atlas Local | Health Check Operacional ===" -ForegroundColor Cyan
"Operational Health Check -- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $ReportFile -Encoding utf8

$pythonExe = Join-Path $Root '.venv\Scripts\python.exe'
$watchScript = Join-Path $Root 'scripts\windows\run-watch-operational.ps1'
$scheduleScript = Join-Path $Root 'scripts\windows\run-schedule-operational.ps1'

Write-Result 'Python venv' $(if (Test-Path $pythonExe) { 'OK' } else { 'FAIL' }) $pythonExe
Write-Result 'Script watch operacional' $(if (Test-Path $watchScript) { 'OK' } else { 'FAIL' }) $watchScript
Write-Result 'Script schedule operacional' $(if (Test-Path $scheduleScript) { 'OK' } else { 'FAIL' }) $scheduleScript
Write-Result 'Pasta da biblioteca' $(if (Test-Path $SourcePath) { 'OK' } else { 'FAIL' }) $SourcePath

$dbFullPath = if ([System.IO.Path]::IsPathRooted($DatabasePath)) { $DatabasePath } else { Join-Path $Root $DatabasePath }
$dbDir = Split-Path -Parent $dbFullPath
Write-Result 'Diretorio do banco SQLite' $(if ($dbDir -and (Test-Path $dbDir)) { 'OK' } else { 'WARN' }) $dbDir

$outputFullPath = if ([System.IO.Path]::IsPathRooted($ScheduleOutputDir)) { $ScheduleOutputDir } else { Join-Path $Root $ScheduleOutputDir }
Write-Result 'Diretorio de output do schedule' $(if (Test-Path $outputFullPath) { 'OK' } else { 'WARN' }) $outputFullPath

$evalQueriesFull = if ([System.IO.Path]::IsPathRooted($EvalQueriesPath)) { $EvalQueriesPath } else { Join-Path $Root $EvalQueriesPath }
$evalBaselineFull = if ([System.IO.Path]::IsPathRooted($EvalBaselinePath)) { $EvalBaselinePath } else { Join-Path $Root $EvalBaselinePath }
Write-Result 'Arquivo de queries evaluate' $(if (Test-Path $evalQueriesFull) { 'OK' } else { 'WARN' }) $evalQueriesFull
Write-Result 'Arquivo baseline evaluate' $(if (Test-Path $evalBaselineFull) { 'OK' } else { 'WARN' }) $evalBaselineFull

Write-Result 'Tesseract no PATH' $(if (Test-CommandAvailable 'tesseract') { 'OK' } else { 'WARN' })
Write-Result 'OCRmyPDF no PATH' $(if (Test-CommandAvailable 'ocrmypdf') { 'OK' } else { 'WARN' })

try {
    $scheduleService = Get-Service -Name 'Schedule' -ErrorAction Stop
    Write-Result 'Servico Task Scheduler' $(if ($scheduleService.Status -eq 'Running') { 'OK' } else { 'WARN' }) $scheduleService.Status
}
catch {
    Write-Result 'Servico Task Scheduler' 'FAIL' $_.Exception.Message
}

$watchTaskName = "$TaskPrefix - Watch Operacional"
$scheduleTaskName = "$TaskPrefix - Schedule Operacional"

$watchTask = Get-ScheduledTask -TaskName $watchTaskName -ErrorAction SilentlyContinue
$scheduleTask = Get-ScheduledTask -TaskName $scheduleTaskName -ErrorAction SilentlyContinue

Write-Result 'Task watch registrada' $(if ($watchTask) { 'OK' } else { 'WARN' }) $watchTaskName
Write-Result 'Task schedule registrada' $(if ($scheduleTask) { 'OK' } else { 'WARN' }) $scheduleTaskName

if (Test-Path $pythonExe) {
    Push-Location $Root
    try {
        & $pythonExe -m src.main watch --help 1>$null 2>$null
        Write-Result 'CLI watch disponivel' $(if ($LASTEXITCODE -eq 0) { 'OK' } else { 'FAIL' })

        & $pythonExe -m src.main schedule --help 1>$null 2>$null
        Write-Result 'CLI schedule disponivel' $(if ($LASTEXITCODE -eq 0) { 'OK' } else { 'FAIL' })
    }
    finally {
        Pop-Location
    }
}

Write-Host "`n--- Resumo ---" -ForegroundColor Cyan
Write-Host "  OK   : $Pass" -ForegroundColor Green
Write-Host "  WARN : $Warn" -ForegroundColor Yellow
Write-Host "  FAIL : $Fail" -ForegroundColor $(if ($Fail -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Relatório: $ReportFile`n" -ForegroundColor DarkGray

if ($Fail -gt 0) {
    exit 1
}
