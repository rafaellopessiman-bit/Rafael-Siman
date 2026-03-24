#Requires -Version 5.1
<#
.SYNOPSIS
  Coleta diagnóstico completo do ambiente para suporte.
.DESCRIPTION
  Reúne versões, status de containers, paths, espaço em disco
  e configurações em um arquivo único para análise.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$diagDir = Join-Path $Root 'logs\diagnostics'
if (-not (Test-Path $diagDir)) { New-Item -ItemType Directory -Path $diagDir -Force | Out-Null }
$ReportFile = Join-Path $diagDir "diagnostics_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

function Section([string]$Title) {
    "`n=== $Title ===" | Out-File -FilePath $ReportFile -Append -Encoding utf8
}

function Info([string]$Line) {
    $Line | Out-File -FilePath $ReportFile -Append -Encoding utf8
}

Write-Host "`n=== Atlas Local | Diagnóstico ===" -ForegroundColor Cyan
"Atlas Local Diagnostics -- $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $ReportFile -Encoding utf8

# --- Sistema ---
Section 'Sistema Operacional'
Info "OS       : $([System.Environment]::OSVersion.VersionString)"
Info "Hostname : $env:COMPUTERNAME"
Info "User     : $env:USERNAME"
Info "RAM      : $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)) GB"

$drive = (Get-Item $Root).PSDrive
Info "Disco $($drive.Name): $([math]::Round($drive.Free / 1GB, 1)) GB livres / $([math]::Round(($drive.Used + $drive.Free) / 1GB, 1)) GB total"

# --- Versões ---
Section 'Versões de Ferramentas'
$tools = @(
    @{ Name = 'Docker'; Cmd = { docker --version 2>$null } },
    @{ Name = 'Docker Compose'; Cmd = { docker compose version 2>$null } },
    @{ Name = 'Node.js'; Cmd = { node --version 2>$null } },
    @{ Name = 'npm'; Cmd = { npm --version 2>$null } },
    @{ Name = 'Python'; Cmd = { python --version 2>$null } },
    @{ Name = 'pip'; Cmd = { pip --version 2>$null } },
    @{ Name = 'git'; Cmd = { git --version 2>$null } }
)
foreach ($t in $tools) {
    $ver = try { & $t.Cmd } catch { 'Não encontrado' }
    Info "$($t.Name.PadRight(18)): $ver"
}

# --- Docker containers ---
Section 'Containers Docker'
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $containers = docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>$null
    if ($containers) { $containers | ForEach-Object { Info $_ } }
    else { Info 'Nenhum container encontrado ou Docker parado.' }
} else {
    Info 'Docker CLI nao encontrado.'
}

# --- Docker images atlas ---
Section 'Imagens Docker (atlas-related)'
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' 2>$null |
        Select-String -Pattern 'atlas|mongodb|nestjs|REPOSITORY' |
        ForEach-Object { Info $_ }
}

# --- Docker volumes ---
Section 'Volumes Docker'
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker volume ls --format 'table {{.Name}}\t{{.Driver}}' 2>$null |
        ForEach-Object { Info $_ }
}

# --- .env (sem valores sensíveis) ---
Section '.env Keys (sem valores)'
$envPath = Join-Path $Root '.env'
if (Test-Path $envPath) {
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^([A-Z_]+)\s*=') {
            Info "  $($Matches[1]) = ***"
        }
    }
} else {
    Info '.env não encontrado'
}

# --- Pastas e tamanhos ---
Section 'Estrutura de Dados'
foreach ($dir in @('data\entrada', 'data\indice', 'data\processados', 'data\backup', 'data\temp')) {
    $p = Join-Path $Root $dir
    if (Test-Path $p) {
        $count = @(Get-ChildItem $p -File -Recurse -ErrorAction SilentlyContinue).Count
        Info "  $($dir.PadRight(25)): $count arquivos"
    } else {
        Info "  $($dir.PadRight(25)): não existe"
    }
}

# --- Python deps ---
Section 'Pacotes Python Instalados'
$venvPip = Join-Path $Root '.venv\Scripts\pip.exe'
if (Test-Path $venvPip) {
    & $venvPip list --format=columns 2>$null | Select-Object -First 30 | ForEach-Object { Info "  $_" }
    Info "  ... (primeiros 30)"
} else {
    Info 'venv não encontrada'
}

# --- Testes rápidos ---
Section 'Resultado do Último Health Check'
$lastHealth = Get-ChildItem (Join-Path $Root 'logs\diagnostics') -Filter 'health_*.txt' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
if ($lastHealth) {
    Get-Content $lastHealth.FullName | ForEach-Object { Info "  $_" }
} else {
    Info 'Nenhum health check anterior encontrado.'
}

Write-Host "Diagnóstico salvo: $ReportFile" -ForegroundColor Green
Write-Host "Envie este arquivo para suporte se necessário.`n" -ForegroundColor DarkGray
