#Requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter()]
    [string]$TaskName = (
        "Enterprise Banking Analytics Pipeline"
    ),

    [Parameter()]
    [ValidateRange(0, 23)]
    [int]$Hour = 5,

    [Parameter()]
    [ValidateRange(0, 59)]
    [int]$Minute = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$PipelineScriptPath = (
    Resolve-Path (
        Join-Path `
            $PSScriptRoot `
            "run_scheduled_pipeline.ps1"
    )
).Path

$PowerShellExecutable = Join-Path `
    $env:ProgramFiles `
    "PowerShell\7\pwsh.exe"

if (
    -not (
        Test-Path `
            -LiteralPath $PowerShellExecutable `
            -PathType Leaf
    )
) {
    throw (
        "PowerShell 7 executable was not found: " +
        $PowerShellExecutable
    )
}

$PythonExecutable = (
    Get-Command python -ErrorAction Stop
).Source

if (
    -not (
        Test-Path `
            -LiteralPath $PythonExecutable `
            -PathType Leaf
    )
) {
    throw (
        "Python executable was not found: " +
        $PythonExecutable
    )
}

$UserId = (
    $env:USERDOMAIN +
    "\" +
    $env:USERNAME
)

$TriggerTime = (
    [datetime]::Today.AddHours(
        $Hour
    ).AddMinutes($Minute)
)

$ActionArguments = (
    '-NoProfile ' +
    '-NonInteractive ' +
    '-ExecutionPolicy Bypass ' +
    '-File "' +
    $PipelineScriptPath +
    '" ' +
    '-PythonExecutablePath "' +
    $PythonExecutable +
    '"'
)

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExecutable `
    -Argument $ActionArguments `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At $TriggerTime

$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Limited

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 2 `
    -RestartInterval (
        New-TimeSpan -Minutes 15
    ) `
    -ExecutionTimeLimit (
        New-TimeSpan -Hours 1
    )

$TaskDefinition = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description (
        "Rebuilds and validates the Enterprise " +
        "Banking Analytics Power BI serving " +
        "layer before the 6:00 AM semantic-model " +
        "refresh."
    )

$RegisteredTask = Register-ScheduledTask `
    -TaskName $TaskName `
    -InputObject $TaskDefinition `
    -Force

$RegisteredTask |
    Select-Object `
        TaskName,
        TaskPath,
        State

Write-Host (
    "Registered daily trigger at " +
    $TriggerTime.ToString("HH:mm") +
    " for " +
    $UserId +
    "."
)
