#Requires -Version 5.1
<#
.SYNOPSIS
  Sobe o ambiente completo atlas_local (MongoDB + NestJS).
.DESCRIPTION
  Executa docker compose up, aguarda health checks e mostra URLs.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogFile = Join-Path $Root 'logs\app\start-all.log'

function Log([string]$Msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Msg" | Tee-Object -FilePath $LogFile -Append
}

Write-Host "`n=== Atlas Local | Start ===" -ForegroundColor Cyan

# Verificar Docker
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host '[ERRO] Docker nao encontrado no PATH.' -ForegroundColor Red
    exit 1
}
docker info 2>&1 | Out-Null
$dockerRunning = ($LASTEXITCODE -eq 0)
if (-not $dockerRunning) {
    Write-Host '[ERRO] Docker Desktop não está rodando.' -ForegroundColor Red
    exit 1
}

# Subir containers
Log 'Subindo docker compose...'
Push-Location $Root
try {
    docker compose up -d --build 2>&1 | ForEach-Object { Log $_ }
} finally {
    Pop-Location
}

# Aguardar MongoDB health
Write-Host 'Aguardando MongoDB...' -ForegroundColor Yellow
$maxAttempts = 30
for ($i = 1; $i -le $maxAttempts; $i++) {
    $health = docker inspect --format='{{.State.Health.Status}}' atlas-local-db 2>$null
    if ($health -eq 'healthy') {
        Write-Host "  MongoDB healthy ($i tentativas)" -ForegroundColor Green
        Log "MongoDB healthy after $i checks"
        break
    }
    if ($i -eq $maxAttempts) {
        Write-Host '  MongoDB não ficou healthy a tempo.' -ForegroundColor Red
        Log 'MongoDB health timeout'
        exit 1
    }
    Start-Sleep -Seconds 2
}

# Aguardar NestJS health
Write-Host 'Aguardando NestJS...' -ForegroundColor Yellow
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri 'http://localhost:3000/health' -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Host "  NestJS healthy ($i tentativas)" -ForegroundColor Green
            Log "NestJS healthy after $i checks"
            break
        }
    } catch { }
    if ($i -eq $maxAttempts) {
        Write-Host '  NestJS não respondeu a tempo (pode estar iniciando).' -ForegroundColor Yellow
        Log 'NestJS health timeout -- may still be starting'
    }
    Start-Sleep -Seconds 3
}

# URLs
Write-Host "`n--- URLs ---" -ForegroundColor Cyan
Write-Host "  API     : http://localhost:3000" -ForegroundColor White
Write-Host "  Swagger : http://localhost:3000/api" -ForegroundColor White
Write-Host "  Health  : http://localhost:3000/health" -ForegroundColor White
Write-Host "  MongoDB : mongodb://localhost:27017" -ForegroundColor White

Log 'Start concluído.'
Write-Host "`nAtlas Local rodando.`n" -ForegroundColor Green
