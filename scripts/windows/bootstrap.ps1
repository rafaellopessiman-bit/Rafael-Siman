#Requires -Version 5.1
<#
.SYNOPSIS
  Valida e prepara o ambiente atlas_local no Windows 11.
.DESCRIPTION
  Verifica Docker Desktop, WSL2, Node.js, Python, .env,
  portas 3000/27017 e cria estrutura de pastas necessária.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Pass = 0; $Fail = 0

function Write-Check([string]$Label, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) {
        Write-Host "  [OK] $Label" -ForegroundColor Green
        if ($Detail) { Write-Host "       $Detail" -ForegroundColor DarkGray }
        $script:Pass++
    } else {
        Write-Host "  [FAIL] $Label" -ForegroundColor Red
        if ($Detail) { Write-Host "       $Detail" -ForegroundColor Yellow }
        $script:Fail++
    }
}

Write-Host "`n=== Atlas Local | Bootstrap ===" -ForegroundColor Cyan
Write-Host "Root: $Root`n"

# --- Docker Desktop ---
$dockerExe = Get-Command docker -ErrorAction SilentlyContinue
Write-Check 'Docker CLI' ($null -ne $dockerExe) $(if ($dockerExe) { (docker --version) } else { 'Instale Docker Desktop' })

if ($dockerExe) {
    $dockerInfo = docker info 2>&1
    $dockerRunning = $LASTEXITCODE -eq 0
    Write-Check 'Docker daemon rodando' $dockerRunning $(if (-not $dockerRunning) { 'Inicie o Docker Desktop' })
}

# --- WSL2 ---
$wslExe = Get-Command wsl -ErrorAction SilentlyContinue
if ($wslExe) {
    $wslStatus = wsl --status 2>&1 | Out-String
    $wsl2 = $wslStatus -match 'WSL 2|Versão padrão:\s*2|Default Version:\s*2'
    Write-Check 'WSL2' $wsl2 $(if (-not $wsl2) { 'Execute: wsl --set-default-version 2' })
} else {
    Write-Check 'WSL2' $false 'WSL não encontrado'
}

# --- Node.js ---
$nodeExe = Get-Command node -ErrorAction SilentlyContinue
Write-Check 'Node.js' ($null -ne $nodeExe) $(if ($nodeExe) { (node --version) } else { 'Instale Node 22 LTS' })

# --- Python ---
$pyExe = Get-Command python -ErrorAction SilentlyContinue
Write-Check 'Python' ($null -ne $pyExe) $(if ($pyExe) { (python --version) } else { 'Instale Python 3.12+' })

# --- Virtual env ---
$venvPath = Join-Path $Root '.venv\Scripts\python.exe'
Write-Check 'Python venv' (Test-Path $venvPath) $(if (-not (Test-Path $venvPath)) { 'Execute: python -m venv .venv' })

# --- .env ---
$envPath = Join-Path $Root '.env'
$envExamplePath = Join-Path $Root '.env.example'
if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
        Write-Check '.env' $true 'Criado a partir de .env.example -- preencha GROQ_API_KEY'
    } else {
        Write-Check '.env' $false 'Arquivo .env e .env.example não encontrados'
    }
} else {
    $envContent = Get-Content $envPath -Raw
    $hasKey = $envContent -match 'GROQ_API_KEY\s*=\s*\S+'
    Write-Check '.env' $true $(if ($hasKey) { 'GROQ_API_KEY configurada' } else { 'ATENÇÃO: GROQ_API_KEY vazia no .env' })
}

# --- Portas ---
function Test-PortFree([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -eq $listener)
}
Write-Check 'Porta 3000 livre' (Test-PortFree 3000) $(if (-not (Test-PortFree 3000)) { 'Porta 3000 em uso -- verifique processos' })
Write-Check 'Porta 27017 livre' (Test-PortFree 27017) $(if (-not (Test-PortFree 27017)) { 'Porta 27017 em uso -- verifique processos' })

# --- Pastas obrigatórias ---
$requiredDirs = @(
    'data\entrada', 'data\indice', 'data\processados',
    'data\backup', 'data\temp', 'logs\app', 'logs\maintenance', 'logs\diagnostics'
)
foreach ($dir in $requiredDirs) {
    $fullPath = Join-Path $Root $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
    }
}
Write-Check 'Pastas de dados e logs' $true "Criadas/verificadas: $($requiredDirs.Count) pastas"

# --- Resumo ---
Write-Host "`n--- Resumo ---" -ForegroundColor Cyan
Write-Host "  Passou : $Pass" -ForegroundColor Green
Write-Host "  Falhou : $Fail" -ForegroundColor $(if ($Fail -gt 0) { 'Red' } else { 'Green' })

if ($Fail -gt 0) {
    Write-Host "`nCorreja os itens acima antes de continuar.`n" -ForegroundColor Yellow
    exit 1
}
Write-Host "`nAmbiente pronto. Execute: scripts\windows\start-all.ps1`n" -ForegroundColor Green
exit 0
