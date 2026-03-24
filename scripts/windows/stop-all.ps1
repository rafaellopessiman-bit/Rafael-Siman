#Requires -Version 5.1
<#
.SYNOPSIS
  Para o ambiente atlas_local preservando volumes.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogFile = Join-Path $Root 'logs\app\stop-all.log'

function Log([string]$Msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Msg" | Tee-Object -FilePath $LogFile -Append
}

Write-Host "`n=== Atlas Local | Stop ===" -ForegroundColor Cyan

Push-Location $Root
try {
    docker compose down 2>&1 | ForEach-Object { Log $_ }
} finally {
    Pop-Location
}

Log 'Containers parados. Volumes preservados.'
Write-Host 'Containers parados. Volumes do MongoDB preservados.' -ForegroundColor Green
Write-Host "Para remover volumes: docker compose down -v`n" -ForegroundColor DarkGray
