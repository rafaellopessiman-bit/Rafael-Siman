#Requires -Version 5.1
<#
.SYNOPSIS
  Verifica saúde de todos os componentes do atlas_local.
.DESCRIPTION
  Testa Docker, MongoDB, API NestJS, Swagger, paths de dados
  e espaço em disco. Gera relatório em logs/diagnostics.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ReportFile = Join-Path $Root "logs\diagnostics\health_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
$Pass = 0; $Warn = 0; $Fail = 0

# Garante pasta de log
$diagDir = Join-Path $Root 'logs\diagnostics'
if (-not (Test-Path $diagDir)) { New-Item -ItemType Directory -Path $diagDir -Force | Out-Null }

function Write-Result([string]$Label, [string]$Status, [string]$Detail = '') {
    $color = switch ($Status) { 'OK' { 'Green' } 'WARN' { 'Yellow' } default { 'Red' } }
    $line = "[$Status] $Label"
    if ($Detail) { $line += " -- $Detail" }
    Write-Host "  $line" -ForegroundColor $color
    $line | Out-File -FilePath $ReportFile -Append -Encoding utf8
    switch ($Status) { 'OK' { $script:Pass++ } 'WARN' { $script:Warn++ } default { $script:Fail++ } }
}

Write-Host "`n=== Atlas Local | Health Check ===" -ForegroundColor Cyan
"Health Check -- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $ReportFile -Encoding utf8

# Docker daemon
$dockerOk = $false
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    docker info 2>&1 | Out-Null
    $dockerOk = ($LASTEXITCODE -eq 0)
}
Write-Result 'Docker daemon' $(if ($dockerOk) { 'OK' } else { 'FAIL' })

# Container MongoDB
if ($dockerOk) {
    $mongoHealth = docker inspect --format='{{.State.Health.Status}}' atlas-local-db 2>$null
    Write-Result 'MongoDB container' $(if ($mongoHealth -eq 'healthy') { 'OK' } elseif ($mongoHealth) { 'WARN' } else { 'FAIL' }) $mongoHealth
}

# Container NestJS
if ($dockerOk) {
    $nestState = docker inspect --format='{{.State.Status}}' atlas-local-nestjs 2>$null
    Write-Result 'NestJS container' $(if ($nestState -eq 'running') { 'OK' } else { 'FAIL' }) $nestState
}

# API Health endpoint
try {
    $resp = Invoke-WebRequest -Uri 'http://localhost:3000/health' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Result 'API /health' $(if ($resp.StatusCode -eq 200) { 'OK' } else { 'WARN' }) "HTTP $($resp.StatusCode)"
} catch {
    Write-Result 'API /health' 'FAIL' $_.Exception.Message
}

# Swagger
try {
    $resp = Invoke-WebRequest -Uri 'http://localhost:3000/api' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Result 'Swagger /api' $(if ($resp.StatusCode -eq 200) { 'OK' } else { 'WARN' }) "HTTP $($resp.StatusCode)"
} catch {
    Write-Result 'Swagger /api' 'FAIL' 'Não acessível'
}

# Pastas de dados
foreach ($dir in @('data\entrada', 'data\indice', 'data\processados', 'data\backup')) {
    $p = Join-Path $Root $dir
    $exists = Test-Path $p
    Write-Result "Pasta $dir" $(if ($exists) { 'OK' } else { 'WARN' }) $(if (-not $exists) { 'Não existe' })
}

# SQLite local
$dbPath = Join-Path $Root 'data\atlas_local.db'
Write-Result 'SQLite atlas_local.db' $(if (Test-Path $dbPath) { 'OK' } else { 'WARN' }) $(if (Test-Path $dbPath) { "$('{0:N0}' -f (Get-Item $dbPath).Length) bytes" } else { 'Ainda não criado' })

# .env
$envPath = Join-Path $Root '.env'
Write-Result '.env presente' $(if (Test-Path $envPath) { 'OK' } else { 'FAIL' })

# Python venv
$venvPy = Join-Path $Root '.venv\Scripts\python.exe'
Write-Result 'Python venv' $(if (Test-Path $venvPy) { 'OK' } else { 'WARN' })

# Espaço em disco
$drive = (Get-Item $Root).PSDrive
$freeGB = [math]::Round($drive.Free / 1GB, 1)
Write-Result "Disco $($drive.Name): livre" $(if ($freeGB -gt 5) { 'OK' } elseif ($freeGB -gt 1) { 'WARN' } else { 'FAIL' }) "$freeGB GB"

# Resumo
Write-Host "`n--- Resumo ---" -ForegroundColor Cyan
Write-Host "  OK   : $Pass" -ForegroundColor Green
Write-Host "  WARN : $Warn" -ForegroundColor Yellow
Write-Host "  FAIL : $Fail" -ForegroundColor $(if ($Fail -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Relatório: $ReportFile`n" -ForegroundColor DarkGray
