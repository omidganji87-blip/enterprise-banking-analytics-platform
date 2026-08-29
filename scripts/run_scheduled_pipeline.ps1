#Requires -Version 7.0

[CmdletBinding()]
param(
    [Parameter()]
    [string]$PythonExecutablePath,

    [Parameter()]
    [switch]$SimulateFailureAfterBackup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# ============================================================
# Project paths and runtime
# ============================================================

$ProjectRoot = (
    Resolve-Path (
        Join-Path $PSScriptRoot ".."
    )
).Path

$AnalyticsPath = Join-Path `
    $ProjectRoot `
    "data\analytics"

$LogsPath = Join-Path `
    $ProjectRoot `
    "logs\scheduled_pipeline"

$BackupPath = Join-Path `
    $ProjectRoot `
    "data\backups\power_bi_serving"

$MonitoringPath = Join-Path `
    $ProjectRoot `
    "monitoring"

$StatusPath = Join-Path `
    $MonitoringPath `
    "scheduled_pipeline_status.json"

if (
    [string]::IsNullOrWhiteSpace(
        $PythonExecutablePath
    )
) {
    $PythonExecutable = (
        Get-Command python -ErrorAction Stop
    ).Source
}
else {
    $PythonExecutable = (
        Resolve-Path `
            -LiteralPath $PythonExecutablePath `
            -ErrorAction Stop
    ).Path

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
}

$RetentionDays = 14

# ============================================================
# Required pipeline and serving artifacts
# ============================================================

$PipelineEntryPath = Join-Path `
    $ProjectRoot `
    "pipelines\run_pipeline.py"

$ServingFileNames = @(
    "dim_date_analytics.parquet"
    "dim_merchant_analytics.parquet"
    "fact_transaction_analytics.parquet"
)

$ServingFiles = foreach (
    $FileName in $ServingFileNames
) {
    Join-Path $AnalyticsPath $FileName
}

if (
    -not (
        Test-Path `
            -LiteralPath $PipelineEntryPath `
            -PathType Leaf
    )
) {
    throw (
        "Pipeline entry file was not found: " +
        $PipelineEntryPath
    )
}

if (
    -not (
        Test-Path `
            -LiteralPath $AnalyticsPath `
            -PathType Container
    )
) {
    throw (
        "Analytics directory was not found: " +
        $AnalyticsPath
    )
}

foreach ($FilePath in $ServingFiles) {
    if (
        -not (
            Test-Path `
                -LiteralPath $FilePath `
                -PathType Leaf
        )
    ) {
        throw (
            "Required serving file was not found: " +
            $FilePath
        )
    }
}

# ============================================================
# Runtime directories and execution identity
# ============================================================

$ExecutionStartTime = Get-Date

$RunTimestamp = (
    $ExecutionStartTime.ToString(
        "yyyyMMdd_HHmmss"
    )
)

$RunLogPath = Join-Path `
    $LogsPath `
    "scheduled_pipeline_$RunTimestamp.log"

$RunBackupPath = Join-Path `
    $BackupPath `
    $RunTimestamp

foreach (
    $DirectoryPath in @(
        $LogsPath
        $BackupPath
        $RunBackupPath
        $MonitoringPath
    )
) {
    New-Item `
        -ItemType Directory `
        -Path $DirectoryPath `
        -Force |
        Out-Null
}

$PythonVersion = (
    & $PythonExecutable --version 2>&1
)

if ($LASTEXITCODE -ne 0) {
    throw (
        "Python could not be started from: " +
        $PythonExecutable
    )
}

$InitializationLines = @(
    "Scheduled pipeline initialization"
    "Timestamp: $RunTimestamp"
    "Project root: $ProjectRoot"
    "Python executable: $PythonExecutable"
    "Python version: $PythonVersion"
)

$InitializationLines |
    Set-Content `
        -LiteralPath $RunLogPath `
        -Encoding utf8

$InitializationLines |
    ForEach-Object {
        Write-Host $_
    }

# ============================================================
# Structured logging
# ============================================================

function Write-RunLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [ValidateSet(
            "INFO",
            "WARNING",
            "ERROR"
        )]
        [string]$Level = "INFO"
    )

    $LogTimestamp = Get-Date `
        -Format "yyyy-MM-dd HH:mm:ss"

    $LogLine = (
        "[$LogTimestamp] " +
        "[$Level] " +
        $Message
    )

    Write-Host $LogLine

    Add-Content `
        -LiteralPath $RunLogPath `
        -Value $LogLine `
        -Encoding utf8
}

function Write-PipelineStatus {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet(
            "RUNNING",
            "SUCCESS",
            "FAILED",
            "RECOVERY_FAILED"
        )]
        [string]$Status,

        [Parameter(Mandatory)]
        [string]$Message,

        [Parameter()]
        [AllowNull()]
        [System.Nullable[int]]$ExitCode = $null,

        [Parameter()]
        [AllowNull()]
        [System.Nullable[bool]]$RecoverySucceeded = $null
    )

    $StatusTime = Get-Date
    $CompletedAtUtc = $null
    $DurationSeconds = $null

    if ($Status -ne "RUNNING") {
        $CompletedAtUtc = $StatusTime.ToUniversalTime().ToString("o")

        $DurationSeconds = [math]::Round(
            (
                $StatusTime -
                $ExecutionStartTime
            ).TotalSeconds,
            3
        )
    }

    $PublishedFiles = @(
        foreach ($FilePath in $ServingFiles) {
            if (
                Test-Path `
                    -LiteralPath $FilePath `
                    -PathType Leaf
            ) {
                $FileInfo = Get-Item `
                    -LiteralPath $FilePath

                [ordered]@{
                    name = $FileInfo.Name
                    path = $FileInfo.FullName
                    exists = $true
                    bytes = $FileInfo.Length
                    last_write_utc = $FileInfo.LastWriteTimeUtc.ToString("o")
                    sha256 = (
                        Get-FileHash `
                            -LiteralPath $FilePath `
                            -Algorithm SHA256
                    ).Hash
                }
            }
            else {
                [ordered]@{
                    name = Split-Path `
                        -Path $FilePath `
                        -Leaf
                    path = $FilePath
                    exists = $false
                    bytes = $null
                    last_write_utc = $null
                    sha256 = $null
                }
            }
        }
    )

    $StatusPayload = [ordered]@{
        pipeline_name = (
            "Enterprise Banking Analytics Pipeline"
        )
        task_name = (
            "Enterprise Banking Analytics Pipeline"
        )
        run_id = $RunTimestamp
        status = $Status
        exit_code = $ExitCode
        message = $Message
        recovery_succeeded = $RecoverySucceeded
        started_at_utc = $ExecutionStartTime.ToUniversalTime().ToString("o")
        completed_at_utc = $CompletedAtUtc
        duration_seconds = $DurationSeconds
        project_root = $ProjectRoot
        python_executable = $PythonExecutable
        python_version = $PythonVersion.ToString()
        log_path = $RunLogPath
        backup_path = $RunBackupPath
        serving_files = $PublishedFiles
    }

    $TemporaryStatusPath = (
        $StatusPath +
        ".tmp"
    )

    $StatusPayload |
        ConvertTo-Json -Depth 6 |
        Set-Content `
            -LiteralPath $TemporaryStatusPath `
            -Encoding utf8

    Move-Item `
        -LiteralPath $TemporaryStatusPath `
        -Destination $StatusPath `
        -Force
}

function Set-PipelineStatusSafely {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet(
            "RUNNING",
            "SUCCESS",
            "FAILED",
            "RECOVERY_FAILED"
        )]
        [string]$Status,

        [Parameter(Mandatory)]
        [string]$Message,

        [Parameter()]
        [AllowNull()]
        [System.Nullable[int]]$ExitCode = $null,

        [Parameter()]
        [AllowNull()]
        [System.Nullable[bool]]$RecoverySucceeded = $null
    )

    try {
        Write-PipelineStatus `
            -Status $Status `
            -Message $Message `
            -ExitCode $ExitCode `
            -RecoverySucceeded $RecoverySucceeded
    }
    catch {
        Write-RunLog `
            -Level "WARNING" `
            -Message (
                "Pipeline status could not be written: " +
                $_.Exception.Message
            )
    }
}

Write-RunLog `
    -Message (
        "Preflight validation completed " +
        "successfully."
    )

# ============================================================
# Protect the current Power BI serving files
# ============================================================

Write-RunLog `
    -Message (
        "Creating a recovery copy of the " +
        "current Power BI serving files."
    )

foreach ($SourceFilePath in $ServingFiles) {
    $FileName = Split-Path `
        -Path $SourceFilePath `
        -Leaf

    $BackupFilePath = Join-Path `
        $RunBackupPath `
        $FileName

    Copy-Item `
        -LiteralPath $SourceFilePath `
        -Destination $BackupFilePath `
        -Force

    $SourceHash = (
        Get-FileHash `
            -LiteralPath $SourceFilePath `
            -Algorithm SHA256
    ).Hash

    $BackupHash = (
        Get-FileHash `
            -LiteralPath $BackupFilePath `
            -Algorithm SHA256
    ).Hash

    if ($SourceHash -ne $BackupHash) {
        throw (
            "Backup verification failed for: " +
            $FileName
        )
    }

    Write-RunLog `
        -Message (
            "Verified backup: " +
            $FileName
        )
}

Write-RunLog `
    -Message (
        "All current serving files were " +
        "backed up successfully."
    )

# ============================================================
# Controlled Python command execution
# ============================================================

function Invoke-LoggedPythonCommand {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Description,

        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    Write-RunLog `
        -Message (
            "Starting: " +
            $Description
        )

    $CommandExitCode = $null

    Push-Location $ProjectRoot

    try {
        & $PythonExecutable @Arguments 2>&1 |
            Tee-Object `
                -FilePath $RunLogPath `
                -Append

        $CommandExitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }

    if ($CommandExitCode -ne 0) {
        throw (
            $Description +
            " failed with exit code " +
            $CommandExitCode +
            "."
        )
    }

    Write-RunLog `
        -Message (
            "Completed successfully: " +
            $Description
        )
}

# ============================================================
# Recovery of the last validated Power BI publication
# ============================================================

function Restore-PowerBIServingFiles {
    [CmdletBinding()]
    param()

    Write-RunLog `
        -Level "WARNING" `
        -Message (
            "Starting recovery of the previous " +
            "Power BI serving files."
        )

    foreach ($TargetFilePath in $ServingFiles) {
        $FileName = Split-Path `
            -Path $TargetFilePath `
            -Leaf

        $BackupFilePath = Join-Path `
            $RunBackupPath `
            $FileName

        if (
            -not (
                Test-Path `
                    -LiteralPath $BackupFilePath `
                    -PathType Leaf
            )
        ) {
            throw (
                "Recovery file was not found: " +
                $BackupFilePath
            )
        }

        Copy-Item `
            -LiteralPath $BackupFilePath `
            -Destination $TargetFilePath `
            -Force

        $BackupHash = (
            Get-FileHash `
                -LiteralPath $BackupFilePath `
                -Algorithm SHA256
        ).Hash

        $RestoredHash = (
            Get-FileHash `
                -LiteralPath $TargetFilePath `
                -Algorithm SHA256
        ).Hash

        if ($BackupHash -ne $RestoredHash) {
            throw (
                "Recovery verification failed for: " +
                $FileName
            )
        }

        Write-RunLog `
            -Level "WARNING" `
            -Message (
                "Verified restored file: " +
                $FileName
            )
    }

    Write-RunLog `
        -Level "WARNING" `
        -Message (
            "Recovery completed successfully."
        )
}

# ============================================================
# Retention of operational logs and recovery copies
# ============================================================

function Remove-ExpiredRuntimeArtifacts {
    [CmdletBinding()]
    param()

    $RetentionCutoff = (
        Get-Date
    ).AddDays(-$RetentionDays)

    $ResolvedBackupRoot = (
        Resolve-Path `
            -LiteralPath $BackupPath
    ).Path.TrimEnd([char[]]"\/")

    $ResolvedLogsRoot = (
        Resolve-Path `
            -LiteralPath $LogsPath
    ).Path.TrimEnd([char[]]"\/")

    $BackupPrefix = (
        $ResolvedBackupRoot +
        [System.IO.Path]::DirectorySeparatorChar
    )

    $LogsPrefix = (
        $ResolvedLogsRoot +
        [System.IO.Path]::DirectorySeparatorChar
    )

    $RemovedBackupCount = 0
    $RemovedLogCount = 0

    $ExpiredBackupDirectories = (
        Get-ChildItem `
            -LiteralPath $BackupPath `
            -Directory |
        Where-Object {
            $_.Name -match '^\d{8}_\d{6}$' -and
            $_.LastWriteTime -lt $RetentionCutoff
        }
    )

    foreach (
        $ExpiredBackup in $ExpiredBackupDirectories
    ) {
        $ResolvedCandidate = (
            Resolve-Path `
                -LiteralPath $ExpiredBackup.FullName
        ).Path

        if (
            -not $ResolvedCandidate.StartsWith(
                $BackupPrefix,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw (
                "Unsafe backup-retention target: " +
                $ResolvedCandidate
            )
        }

        Remove-Item `
            -LiteralPath $ResolvedCandidate `
            -Recurse `
            -Force

        $RemovedBackupCount += 1
    }

    $ExpiredLogFiles = (
        Get-ChildItem `
            -LiteralPath $LogsPath `
            -Filter "scheduled_pipeline_*.log" `
            -File |
        Where-Object {
            $_.Name -match (
                '^scheduled_pipeline_' +
                '\d{8}_\d{6}\.log$'
            ) -and
            $_.LastWriteTime -lt $RetentionCutoff
        }
    )

    foreach ($ExpiredLog in $ExpiredLogFiles) {
        $ResolvedCandidate = (
            Resolve-Path `
                -LiteralPath $ExpiredLog.FullName
        ).Path

        if (
            -not $ResolvedCandidate.StartsWith(
                $LogsPrefix,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw (
                "Unsafe log-retention target: " +
                $ResolvedCandidate
            )
        }

        Remove-Item `
            -LiteralPath $ResolvedCandidate `
            -Force

        $RemovedLogCount += 1
    }

    Write-RunLog `
        -Message (
            "Retention cleanup completed; days=" +
            $RetentionDays +
            "; backups_removed=" +
            $RemovedBackupCount +
            "; logs_removed=" +
            $RemovedLogCount
        )
}

# ============================================================
# Guarded production execution
# ============================================================

Set-PipelineStatusSafely `
    -Status "RUNNING" `
    -Message "Scheduled pipeline execution is in progress."

try {
    if ($SimulateFailureAfterBackup) {
        throw (
            "Controlled recovery-test failure requested " +
            "after the verified backup."
        )
    }

    Invoke-LoggedPythonCommand `
        -Description "Automated Python test suite" `
        -Arguments @(
            "-m"
            "pytest"
            "-q"
        )

    Invoke-LoggedPythonCommand `
        -Description (
            "Enterprise banking analytics pipeline"
        ) `
        -Arguments @(
            "-m"
            "pipelines.run_pipeline"
        )

    Write-RunLog `
        -Message (
            "Verifying the published Power BI " +
            "serving files."
        )

    foreach ($PublishedFilePath in $ServingFiles) {
        if (
            -not (
                Test-Path `
                    -LiteralPath $PublishedFilePath `
                    -PathType Leaf
            )
        ) {
            throw (
                "Published serving file is missing: " +
                $PublishedFilePath
            )
        }

        $PublishedFile = Get-Item `
            -LiteralPath $PublishedFilePath

        if ($PublishedFile.Length -le 0) {
            throw (
                "Published serving file is empty: " +
                $PublishedFile.Name
            )
        }

        $PublishedHash = (
            Get-FileHash `
                -LiteralPath $PublishedFilePath `
                -Algorithm SHA256
        ).Hash

        Write-RunLog `
            -Message (
                "Verified publication: " +
                $PublishedFile.Name +
                "; bytes=" +
                $PublishedFile.Length +
                "; sha256=" +
                $PublishedHash
            )
    }

    try {
        Remove-ExpiredRuntimeArtifacts
    }
    catch {
        Write-RunLog `
            -Level "WARNING" `
            -Message (
                "Retention cleanup was skipped " +
                "after an error: " +
                $_.Exception.Message
            )
    }

    $ExecutionDuration = (
        Get-Date
    ) - $ExecutionStartTime

    Write-RunLog `
        -Message (
            "Scheduled pipeline completed " +
            "successfully; duration=" +
            $ExecutionDuration.ToString()
        )

    Set-PipelineStatusSafely `
        -Status "SUCCESS" `
        -Message "Scheduled pipeline completed successfully." `
        -ExitCode 0 `
        -RecoverySucceeded $null

    exit 0
}
catch {
    $FailureMessage = $_.Exception.Message

    Write-RunLog `
        -Level "ERROR" `
        -Message (
            "Scheduled pipeline failed: " +
            $FailureMessage
        )

    try {
        Restore-PowerBIServingFiles
    }
    catch {
        $RecoveryFailureMessage = (
            $_.Exception.Message
        )

        Write-RunLog `
            -Level "ERROR" `
            -Message (
                "Recovery also failed: " +
                $RecoveryFailureMessage
            )

        Set-PipelineStatusSafely `
            -Status "RECOVERY_FAILED" `
            -Message (
                "Pipeline failed and recovery also failed: " +
                $RecoveryFailureMessage
            ) `
            -ExitCode 2 `
            -RecoverySucceeded $false

        exit 2
    }

    $ExecutionDuration = (
        Get-Date
    ) - $ExecutionStartTime

    Write-RunLog `
        -Level "ERROR" `
        -Message (
            "The previous validated publication " +
            "was restored; duration=" +
            $ExecutionDuration.ToString()
        )

    Set-PipelineStatusSafely `
        -Status "FAILED" `
        -Message (
            "Pipeline failed, and the previous validated " +
            "publication was restored: " +
            $FailureMessage
        ) `
        -ExitCode 1 `
        -RecoverySucceeded $true

    exit 1
}
