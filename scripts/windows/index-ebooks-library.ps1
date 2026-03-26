#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db',
    [int]$Workers = 6,
    [int]$BatchSize = 25
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $Root 'logs\maintenance'
$LogFile = Join-Path $LogDir 'ebooks-index.log'
$LockFile = Join-Path $LogDir 'ebooks-index.lock.json'
$StdOutFile = Join-Path $LogDir 'ebooks-index.stdout.log'
$StdErrFile = Join-Path $LogDir 'ebooks-index.stderr.log'
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'
$DbFullPath = Join-Path $Root $DatabasePath

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Log([string]$Message) {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$timestamp  $Message" | Tee-Object -FilePath $LogFile -Append | Out-Host
}

function Remove-LockFile() {
    if (Test-Path $LockFile) {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    }
}

function Remove-LockFileIfOwnedBy([int]$PidValue) {
    if (-not (Test-Path $LockFile)) {
        return
    }

    try {
        $lock = Get-Content $LockFile -Raw | ConvertFrom-Json
        if ($null -ne $lock -and [int]$lock.pid -eq $PidValue) {
            Remove-LockFile
        }
    }
    catch {
        Remove-LockFile
    }
}

function Save-LockFile([int]$PidValue) {
    $payload = [pscustomobject]@{
        pid = $PidValue
        sourcePath = $SourcePath
        databasePath = $DatabasePath
        startedAt = (Get-Date).ToString('o')
    } | ConvertTo-Json

    Set-Content -Path $LockFile -Value $payload -Encoding UTF8
}

function Get-ExistingLockInfo() {
    if (-not (Test-Path $LockFile)) {
        return $null
    }

    try {
        return Get-Content $LockFile -Raw | ConvertFrom-Json
    }
    catch {
        Remove-LockFile
        return $null
    }
}

function Get-OrphanIndexProcesses() {
    $pythonPath = $PythonExe.Replace('\\', '\\\\')
    $dbArgA = $DatabasePath.Replace('\\', '\\\\')
    $dbArgB = $DatabasePath.Replace('\\', '/')

    return @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^python(?:\.exe)?$' -and
        $_.CommandLine -like "*$pythonPath*" -and
        $_.CommandLine -like '*-m src.main index*' -and
        ($_.CommandLine -like "*--db-path $dbArgA*" -or $_.CommandLine -like "*--db-path $dbArgB*")
    })
}

Write-Host "`n=== Atlas Local | Indexacao Biblioteca Tecnica ===" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host '[ERRO] Python venv nao encontrada. Execute bootstrap.ps1 primeiro.' -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $SourcePath)) {
    Write-Host "[ERRO] Pasta da biblioteca nao encontrada: $SourcePath" -ForegroundColor Red
    exit 1
}

$existingLock = Get-ExistingLockInfo
if ($null -ne $existingLock) {
    $runningProcess = Get-Process -Id $existingLock.pid -ErrorAction SilentlyContinue
    if ($runningProcess) {
        Log "Ja existe uma indexacao em andamento. PID=$($existingLock.pid) Banco=$($existingLock.databasePath) Inicio=$($existingLock.startedAt)"
        Write-Host 'Abortado para evitar duplicidade de indexacao.' -ForegroundColor Yellow
        exit 2
    }

    Remove-LockFile
}

$orphanProcesses = @(Get-OrphanIndexProcesses)
if ($orphanProcesses.Count -gt 0) {
    $pidList = ($orphanProcesses | Select-Object -ExpandProperty ProcessId) -join ', '
    Log "Foram encontrados processos de indexacao ja em execucao sem lock ativo. PIDs: $pidList"
    Write-Host 'Abortado para evitar uma nova execucao duplicada. Verifique o status da biblioteca tecnica.' -ForegroundColor Yellow
    exit 3
}

Log "Origem: $SourcePath"
Log "Banco: $DatabasePath"
Log "Workers: $Workers"
Log "Batch size: $BatchSize"

Push-Location $Root
try {
    foreach ($artifact in @($StdOutFile, $StdErrFile)) {
        if (Test-Path $artifact) {
            Remove-Item $artifact -Force -ErrorAction SilentlyContinue
        }
    }

    $process = Start-Process -FilePath $PythonExe `
        -ArgumentList @('-u', '-m', 'src.main', 'index', '--path', $SourcePath, '--db-path', $DatabasePath, '--workers', $Workers, '--batch-size', $BatchSize) `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $StdOutFile `
        -RedirectStandardError $StdErrFile `
        -PassThru

    Save-LockFile -PidValue $process.Id
    Log "Indexacao iniciada. PID: $($process.Id)"

    while (-not $process.HasExited) {
        Start-Sleep -Seconds 15
        $process.Refresh()

        $dbStatus = if (Test-Path $DbFullPath) {
            $dbInfo = Get-Item $DbFullPath
            "db=$('{0:N0}' -f $dbInfo.Length) bytes"
        }
        else {
            'db=pendente'
        }

        $cpuValue = if ($null -ne $process.CPU) {
            [math]::Round($process.CPU, 1)
        }
        else {
            0
        }

        Log "Heartbeat PID=$($process.Id) cpu=${cpuValue}s $dbStatus"
    }

    Log "Indexacao finalizada com exit code $($process.ExitCode)"

    if (Test-Path $StdOutFile) {
        $indexOutput = (Get-Content $StdOutFile -Raw).Trim()
        if ($indexOutput) {
            Log $indexOutput
        }
    }

    if (Test-Path $StdErrFile) {
        $indexErrors = (Get-Content $StdErrFile -Raw).Trim()
        if ($indexErrors) {
            Log "STDERR: $indexErrors"
        }
    }

    if (Test-Path $DbFullPath) {
        $statsOutput = & $PythonExe -c @"
import sqlite3
from pathlib import Path

db_path = Path(r'$DbFullPath')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

docs_total = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
chunks_total = conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0]
pdf_total = conn.execute("SELECT COUNT(*) FROM documents WHERE file_extension = '.pdf'").fetchone()[0]
themes = conn.execute(
    """
    SELECT COALESCE(json_extract(metadata_json, '$.theme'), 'sem_tema') AS theme, COUNT(*) AS total
    FROM documents
    GROUP BY theme
    ORDER BY total DESC, theme ASC
    LIMIT 5
    """
).fetchall()

print('=== Catalog Stats ===')
print(f'Documentos: {docs_total}')
print(f'Chunks: {chunks_total}')
print(f'PDFs: {pdf_total}')
for row in themes:
    print(f"Tema {row['theme']}: {row['total']}")
"@
        Log $statsOutput.TrimEnd()
    } else {
        Log 'Banco do catalogo ainda nao foi materializado ao final da execucao.'
    }

    Remove-LockFileIfOwnedBy -PidValue $process.Id
}
finally {
    Pop-Location
}

Write-Host "`nRotina concluida. Log: $LogFile`n" -ForegroundColor Green
