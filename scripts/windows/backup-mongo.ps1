#Requires -Version 5.1
<#
.SYNOPSIS
  Backup do MongoDB Atlas Local e do SQLite local.
.DESCRIPTION
  Exporta dados do MongoDB via mongodump dentro do container
  e copia o SQLite local para data/backup com timestamp.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $Root 'data\backup'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$LogFile = Join-Path $Root 'logs\maintenance\backup.log'

# Garantir pastas
foreach ($d in @($BackupDir, (Join-Path $Root 'logs\maintenance'))) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

function Log([string]$Msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Msg" | Tee-Object -FilePath $LogFile -Append
}

Write-Host "`n=== Atlas Local | Backup ===" -ForegroundColor Cyan

# Ler credenciais do .env (fallback para defaults de desenvolvimento)
$envFilePath = Join-Path $Root '.env'
$_mongoUser = 'admin'
$_mongoPass = ''
$_mongoDB   = 'atlas_local_db'
if (Test-Path $envFilePath) {
    $envContent = Get-Content $envFilePath -Raw
    if ($envContent -match '(?m)^MONGODB_USER=(.+)$')  { $_mongoUser = $Matches[1].Trim() }
    if ($envContent -match '(?m)^MONGODB_PASSWORD=(.+)$') { $_mongoPass = $Matches[1].Trim() }
    if ($envContent -match '(?m)^MONGODB_DB=(.+)$')   { $_mongoDB   = $Matches[1].Trim() }
}
$_mongoUri = "mongodb://${_mongoUser}:${_mongoPass}@localhost:27017/${_mongoDB}?authSource=${_mongoDB}"

# --- MongoDB dump ---
$mongoBackupDir = Join-Path $BackupDir "mongo_$Timestamp"
New-Item -ItemType Directory -Path $mongoBackupDir -Force | Out-Null

Log 'Iniciando mongodump no container...'
$dumpResult = docker exec atlas-local-db mongodump --uri="$_mongoUri" --out=/tmp/dump 2>&1
if ($LASTEXITCODE -ne 0) {
    Log "mongodump falhou: $dumpResult"
    Write-Host '[WARN] mongodump falhou -- container pode estar parado.' -ForegroundColor Yellow
} else {
    docker cp atlas-local-db:/tmp/dump/. $mongoBackupDir 2>&1 | Out-Null
    docker exec atlas-local-db rm -rf /tmp/dump 2>&1 | Out-Null
    Log "MongoDB exportado para: $mongoBackupDir"
    Write-Host "  MongoDB -> $mongoBackupDir" -ForegroundColor Green
}

# --- SQLite local ---
$sqliteSrc = Join-Path $Root 'data\atlas_local.db'
if (Test-Path $sqliteSrc) {
    $sqliteDest = Join-Path $BackupDir "atlas_local_$Timestamp.db"
    Copy-Item $sqliteSrc $sqliteDest
    Log "SQLite copiado: $sqliteDest"
    Write-Host "  SQLite  -> $sqliteDest" -ForegroundColor Green
} else {
    Log 'SQLite atlas_local.db nao encontrado -- pulando.'
    Write-Host '  SQLite  -> não encontrado (indexação ainda não executada)' -ForegroundColor Yellow
}

# --- data/indice snapshot ---
$indiceSrc = Join-Path $Root 'data\indice'
if (Test-Path $indiceSrc) {
    $indiceDest = Join-Path $BackupDir "indice_$Timestamp"
    Copy-Item $indiceSrc $indiceDest -Recurse
    Log "Indice copiado: $indiceDest"
    Write-Host "  Índice  -> $indiceDest" -ForegroundColor Green
}

Write-Host "`nBackup concluído: $BackupDir`n" -ForegroundColor Green
