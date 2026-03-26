#Requires -Version 5.1
<#
.SYNOPSIS
  Executa OCR em lote apenas nos PDFs marcados como ocr_required pelo audit.
.DESCRIPTION
  Consome o JSON gerado por `python -m src.main audit --output json` e chama ocrmypdf
  apenas para caminhos PDF presentes em remediation.ocr_required_paths.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$AuditJsonPath,

    [string]$OcrCommand = 'ocrmypdf',
    [string]$Language = 'eng',
    [switch]$InPlace
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LogFile = Join-Path $LogDir 'ocr-flagged-pdfs.log'

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

function Log([string]$Msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $Msg" | Tee-Object -FilePath $LogFile -Append
}

if (-not (Test-Path $AuditJsonPath)) {
    Write-Host "[ERRO] Audit JSON nao encontrado: $AuditJsonPath" -ForegroundColor Red
    exit 1
}

$commandInfo = Get-Command $OcrCommand -ErrorAction SilentlyContinue
if (-not $commandInfo) {
    Write-Host "[ERRO] Comando OCR nao encontrado: $OcrCommand" -ForegroundColor Red
    exit 1
}

$payload = Get-Content -Raw -Path $AuditJsonPath | ConvertFrom-Json
$paths = @($payload.remediation.ocr_required_paths | Where-Object { $_ -and $_.ToLower().EndsWith('.pdf') })

Write-Host "`n=== Atlas Local | OCR PDFs Sinalizados ===" -ForegroundColor Cyan
Write-Host "Audit JSON: $AuditJsonPath"
Write-Host "Candidatos PDF: $($paths.Count)"

if ($paths.Count -eq 0) {
    Log 'Nenhum PDF com ocr_required encontrado no audit.'
    exit 0
}

foreach ($pdfPath in $paths) {
    if (-not (Test-Path $pdfPath)) {
        Log "Arquivo nao encontrado: $pdfPath"
        continue
    }

    if ($InPlace) {
        $outputPath = $pdfPath
    }
    else {
        $dir = Split-Path -Parent $pdfPath
        $name = [System.IO.Path]::GetFileNameWithoutExtension($pdfPath)
        $outputPath = Join-Path $dir ("{0}.ocr.pdf" -f $name)
    }

    $args = @('--force-ocr', '-l', $Language, $pdfPath, $outputPath)
    Log ("Executando OCR: {0} -> {1}" -f $pdfPath, $outputPath)

    try {
        & $OcrCommand @args 2>&1 | Tee-Object -FilePath $LogFile -Append | Out-Host
    }
    catch {
        Log "Falha em $pdfPath: $_"
    }
}

Write-Host "Log: $LogFile`n" -ForegroundColor DarkGray
