#Requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter()]
    [string]$TaskName = (
        "Enterprise Banking Analytics Pipeline"
    ),

    [Parameter()]
    [ValidateRange(1, 168)]
    [int]$RequireFreshHours = 26,

    [Parameter()]
    [ValidateRange(0, 23)]
    [int]$ScheduleHourLocal = 5,

    [Parameter()]
    [ValidateRange(0, 240)]
    [int]$ScheduleGraceMinutes = 60,

    [Parameter()]
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$StatusPath = Join-Path `
    $ProjectRoot `
    "monitoring\scheduled_pipeline_status.json"

$AnalyticsPath = Join-Path `
    $ProjectRoot `
    "data\analytics"

$ServingFileNames = @(
    "dim_date_analytics.parquet"
    "dim_merchant_analytics.parquet"
    "fact_transaction_analytics.parquet"
)

$PipelineStatus = $null
$PipelineRunId = $null
$PipelineMessage = $null
$PipelineCompletedAt = $null
$PipelineAgeHours = $null
$PipelineFresh = $false
$PipelineMeetsSchedule = $false
$PipelineLogPath = $null
$PipelineExitCode = $null
$RecoverySucceeded = $null

if (
    Test-Path `
        -LiteralPath $StatusPath `
        -PathType Leaf
) {
    $StatusDocument = Get-Content `
        -LiteralPath $StatusPath `
        -Raw |
        ConvertFrom-Json -DateKind String

    $PipelineStatus = $StatusDocument.status
    $PipelineRunId = $StatusDocument.run_id
    $PipelineMessage = $StatusDocument.message
    $PipelineLogPath = $StatusDocument.log_path
    $PipelineExitCode = $StatusDocument.exit_code
    $RecoverySucceeded = (
        $StatusDocument.recovery_succeeded
    )

    if ($null -ne $StatusDocument.completed_at_utc) {
        $PipelineCompletedAt = (
            [DateTimeOffset]::Parse(
                $StatusDocument.completed_at_utc
            )
        )

        $PipelineAgeHours = [math]::Round(
            (
                [DateTimeOffset]::UtcNow -
                $PipelineCompletedAt.ToUniversalTime()
            ).TotalHours,
            2
        )

        $PipelineFresh = (
            $PipelineAgeHours -le $RequireFreshHours
        )
    }
}

$CheckTime = Get-Date
$ScheduledToday = $CheckTime.Date.AddHours(
    $ScheduleHourLocal
)

$ScheduleGraceBoundary = $ScheduledToday.AddMinutes(
    $ScheduleGraceMinutes
)

$RequiredRunAfter = if (
    $CheckTime -ge $ScheduleGraceBoundary
) {
    $ScheduledToday
}
else {
    $ScheduledToday.AddDays(-1)
}

if ($null -ne $PipelineCompletedAt) {
    $PipelineMeetsSchedule = (
        $PipelineCompletedAt.ToLocalTime().DateTime -ge
        $RequiredRunAfter
    )
}

$ScheduledTask = Get-ScheduledTask `
    -TaskName $TaskName `
    -ErrorAction SilentlyContinue

$ScheduledTaskInfo = $null

if ($null -ne $ScheduledTask) {
    $ScheduledTaskInfo = Get-ScheduledTaskInfo `
        -TaskName $TaskName
}

$GatewayService = Get-Service `
    -Name "PBIEgwService" `
    -ErrorAction SilentlyContinue

$ServingFiles = @(
    foreach ($FileName in $ServingFileNames) {
        $FilePath = Join-Path `
            $AnalyticsPath `
            $FileName

        $Exists = Test-Path `
            -LiteralPath $FilePath `
            -PathType Leaf

        $FileInfo = if ($Exists) {
            Get-Item -LiteralPath $FilePath
        }
        else {
            $null
        }

        [pscustomobject]@{
            Name = $FileName
            Exists = $Exists
            Bytes = if ($Exists) {
                $FileInfo.Length
            }
            else {
                $null
            }
            LastWriteTime = if ($Exists) {
                $FileInfo.LastWriteTime
            }
            else {
                $null
            }
        }
    }
)

$AllServingFilesExist = (
    @(
        $ServingFiles |
            Where-Object { -not $_.Exists }
    ).Count -eq 0
)

$TaskHealthy = (
    $null -ne $ScheduledTaskInfo -and
    $ScheduledTaskInfo.LastTaskResult -eq 0 -and
    $ScheduledTaskInfo.LastRunTime -ge $RequiredRunAfter -and
    $ScheduledTask.State -in @(
        "Ready",
        "Running"
    )
)

$GatewayHealthy = (
    $null -ne $GatewayService -and
    $GatewayService.Status -eq "Running"
)

$PipelineHealthy = (
    $PipelineStatus -eq "SUCCESS" -and
    $PipelineFresh -and
    $PipelineMeetsSchedule
)

$OverallHealthy = (
    $PipelineHealthy -and
    $TaskHealthy -and
    $GatewayHealthy -and
    $AllServingFilesExist
)

$HealthReport = [pscustomobject]@{
    OverallHealth = if ($OverallHealthy) {
        "HEALTHY"
    }
    else {
        "ATTENTION_REQUIRED"
    }
    CheckedAt = $CheckTime
    PipelineStatus = if ($null -ne $PipelineStatus) {
        $PipelineStatus
    }
    else {
        "NO_STATUS"
    }
    PipelineRunId = $PipelineRunId
    PipelineExitCode = $PipelineExitCode
    RecoverySucceeded = $RecoverySucceeded
    PipelineMessage = $PipelineMessage
    PipelineCompletedAt = $PipelineCompletedAt
    PipelineAgeHours = $PipelineAgeHours
    PipelineFresh = $PipelineFresh
    PipelineMeetsSchedule = $PipelineMeetsSchedule
    PipelineFreshnessLimitHours = $RequireFreshHours
    RequiredRunAfter = $RequiredRunAfter
    PipelineLogPath = $PipelineLogPath
    TaskName = $TaskName
    TaskState = if ($null -ne $ScheduledTask) {
        $ScheduledTask.State
    }
    else {
        "NOT_FOUND"
    }
    TaskLastRunTime = if ($null -ne $ScheduledTaskInfo) {
        $ScheduledTaskInfo.LastRunTime
    }
    else {
        $null
    }
    TaskNextRunTime = if ($null -ne $ScheduledTaskInfo) {
        $ScheduledTaskInfo.NextRunTime
    }
    else {
        $null
    }
    TaskLastResult = if ($null -ne $ScheduledTaskInfo) {
        $ScheduledTaskInfo.LastTaskResult
    }
    else {
        $null
    }
    GatewayService = if ($null -ne $GatewayService) {
        $GatewayService.Name
    }
    else {
        "NOT_FOUND"
    }
    GatewayStatus = if ($null -ne $GatewayService) {
        $GatewayService.Status
    }
    else {
        "NOT_FOUND"
    }
    AllServingFilesExist = $AllServingFilesExist
    ServingFiles = $ServingFiles
    StatusPath = $StatusPath
}

if ($AsJson) {
    $HealthReport |
        ConvertTo-Json -Depth 6
}
else {
    $HealthReport |
        Format-List `
            OverallHealth,
            CheckedAt,
            PipelineStatus,
            PipelineRunId,
            PipelineExitCode,
            RecoverySucceeded,
            PipelineCompletedAt,
            PipelineAgeHours,
            PipelineFresh,
            PipelineMeetsSchedule,
            RequiredRunAfter,
            TaskState,
            TaskLastRunTime,
            TaskNextRunTime,
            TaskLastResult,
            GatewayStatus,
            AllServingFilesExist,
            PipelineLogPath

    $ServingFiles |
        Format-Table `
            Name,
            Exists,
            Bytes,
            LastWriteTime `
            -AutoSize
}

if ($OverallHealthy) {
    exit 0
}

exit 1
