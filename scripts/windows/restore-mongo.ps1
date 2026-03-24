#Requires -Version 5.1
<#
.SYNOPSIS
  Restaura backup do MongoDB Atlas Local.
.DESCRIPTION
  Lista backups disponíveis e permite restaurar um específico
  via mongorestore dentro do container.
.PARAMETER BackupName
  Nome da pasta de backup (ex: mongo_20260324_120000).
  Se omitido, lista os backups disponíveis.
#>
param(
    [string]$BackupName
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $Root 'data\backup'

Write-Host "`n=== Atlas Local | Restore ===" -ForegroundColor Cyan

# Listar backups disponíveis
$mongoBackups = Get-ChildItem -Path $BackupDir -Directory -Filter 'mongo_*' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending

if (-not $mongoBackups) {
    Write-Host 'Nenhum backup MongoDB encontrado em data\backup\' -ForegroundColor Yellow
    exit 0
}

if (-not $BackupName) {
    Write-Host "`nBackups disponíveis:" -ForegroundColor White
    foreach ($b in $mongoBackups) {
        $size = (Get-ChildItem $b.FullName -Recurse -File | Measure-Object -Sum Length).Sum
        $sizeKB = [math]::Round($size / 1KB, 0)
        Write-Host "  $($b.Name)  ($sizeKB KB)" -ForegroundColor DarkGray
    }
    Write-Host "`nUso: .\restore-mongo.ps1 -BackupName mongo_20260324_120000`n" -ForegroundColor White
    exit 0
}

$selectedPath = Join-Path $BackupDir $BackupName
if (-not (Test-Path $selectedPath)) {
    Write-Host "Backup não encontrado: $selectedPath" -ForegroundColor Red
    exit 1
}

# Confirmar
Write-Host "Restaurar: $BackupName" -ForegroundColor Yellow
$confirm = Read-Host "Continuar? (s/N)"
if ($confirm -notin @('s', 'S', 'sim', 'y', 'yes')) {
    Write-Host 'Restore cancelado.' -ForegroundColor DarkGray
    exit 0
}

# Ler credenciais do .env (fallback para defaults de desenvolvimento)
$envFilePath = Join-Path $Root '.env'
$_mongoUser = 'admin'
$_mongoPass = 'AtlasLocal2026!Secure'
$_mongoDB   = 'atlas_local_db'
if (Test-Path $envFilePath) {
    $envContent = Get-Content $envFilePath -Raw
    if ($envContent -match '(?m)^MONGODB_USER=(.+)$')  { $_mongoUser = $Matches[1].Trim() }
    if ($envContent -match '(?m)^MONGODB_PASSWORD=(.+)$') { $_mongoPass = $Matches[1].Trim() }
    if ($envContent -match '(?m)^MONGODB_DB=(.+)$')   { $_mongoDB   = $Matches[1].Trim() }
}
$_mongoUri = "mongodb://${_mongoUser}:${_mongoPass}@localhost:27017/${_mongoDB}?authSource=admin"

# Copiar para container e restaurar
docker cp $selectedPath atlas-local-db:/tmp/restore 2>&1 | Out-Null
$restoreResult = docker exec atlas-local-db mongorestore --uri="$_mongoUri" --drop /tmp/restore 2>&1
docker exec atlas-local-db rm -rf /tmp/restore 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] mongorestore falhou: $restoreResult" -ForegroundColor Red
    exit 1
}

Write-Host "Restore concluído com sucesso.`n" -ForegroundColor Green
