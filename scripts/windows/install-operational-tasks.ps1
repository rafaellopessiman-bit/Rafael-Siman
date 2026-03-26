#Requires -Version 5.1
param(
    [string]$SourcePath = 'E:\E-book',
    [string]$DatabasePath = 'data\ebooks_catalog.db',
    [string]$ScheduleOutputDir = 'data\processados\schedule',
    [int]$WatchIntervalSeconds = 30,
    [ValidateSet('manual', 'ocr-required', 'full-auto')]
    [string]$WatchRemediationPolicy = 'full-auto',
    [string]$ScheduleAt = '08:00',
    [int]$ScheduleRepeatHours = 4,
    [string]$TaskPrefix = 'Atlas Local',
    [switch]$PreviewOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$WatchScript = Join-Path $Root 'scripts\windows\run-watch-operational.ps1'
$ScheduleScript = Join-Path $Root 'scripts\windows\run-schedule-operational.ps1'

function Write-Step([string]$Message) {
    Write-Host $Message -ForegroundColor Cyan
}

function New-OperationalTaskAction([string]$ScriptPath, [string[]]$ExtraArgs) {
    $args = @(
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $ScriptPath)
    ) + $ExtraArgs

    return New-ScheduledTaskAction -Execute $PowerShellExe -Argument ($args -join ' ')
}

function Register-OperationalTask(
    [string]$TaskName,
    [Microsoft.Management.Infrastructure.CimInstance]$Action,
    [Microsoft.Management.Infrastructure.CimInstance[]]$Triggers,
    [string]$Description
) {
    if ($PreviewOnly) {
        Write-Host "[PREVIEW] Registraria task: $TaskName" -ForegroundColor Yellow
        Write-Host "          Descricao: $Description" -ForegroundColor DarkYellow
        return
    }

    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType InteractiveToken -RunLevel Limited

    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Triggers `
        -Description $Description `
        -Settings $settings `
        -Principal $principal | Out-Null

    Write-Host "[OK] Task registrada: $TaskName" -ForegroundColor Green
}

Write-Host "`n=== Atlas Local | Instalar Tasks Operacionais ===" -ForegroundColor Cyan

if (-not (Test-Path $WatchScript)) {
    throw "Script de watch nao encontrado: $WatchScript"
}

if (-not (Test-Path $ScheduleScript)) {
    throw "Script de schedule nao encontrado: $ScheduleScript"
}

if (-not (Test-Path $SourcePath)) {
    throw "Pasta da biblioteca nao encontrada: $SourcePath"
}

$watchTaskName = "$TaskPrefix - Watch Operacional"
$scheduleTaskName = "$TaskPrefix - Schedule Operacional"

$watchAction = New-OperationalTaskAction `
    -ScriptPath $WatchScript `
    -ExtraArgs @(
        '-SourcePath', ('"{0}"' -f $SourcePath),
        '-DatabasePath', ('"{0}"' -f $DatabasePath),
        '-IntervalSeconds', $WatchIntervalSeconds,
        '-RemediationPolicy', $WatchRemediationPolicy
    )

$scheduleAction = New-OperationalTaskAction `
    -ScriptPath $ScheduleScript `
    -ExtraArgs @(
        '-SourcePath', ('"{0}"' -f $SourcePath),
        '-DatabasePath', ('"{0}"' -f $DatabasePath),
        '-OutputDir', ('"{0}"' -f $ScheduleOutputDir)
    )

$watchTrigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
if ($ScheduleRepeatHours -gt 0) {
    $scheduleTrigger = New-ScheduledTaskTrigger `
        -Once `
        -At $ScheduleAt `
        -RepetitionInterval (New-TimeSpan -Hours $ScheduleRepeatHours) `
        -RepetitionDuration (New-TimeSpan -Days 3650)
}
else {
    $scheduleTrigger = New-ScheduledTaskTrigger -Daily -At $ScheduleAt
}

Write-Step "Configurando task do watch"
Register-OperationalTask `
    -TaskName $watchTaskName `
    -Action $watchAction `
    -Triggers @($watchTrigger) `
    -Description 'Atlas Local watch operacional com remediacao automatica e snapshot persistido.'

Write-Step "Configurando task do schedule"
Register-OperationalTask `
    -TaskName $scheduleTaskName `
    -Action $scheduleAction `
    -Triggers @($scheduleTrigger) `
    -Description 'Atlas Local schedule operacional com audit, report, OCR pendente e evaluate.'

Write-Host "`nConcluido." -ForegroundColor Green
