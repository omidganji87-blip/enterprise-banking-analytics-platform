#Requires -Version 7.0

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [switch]$RemoveAutoDateTables,

    [Parameter()]
    [switch]$RefreshModel
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PowerBIBinPath = Join-Path `
    $env:ProgramFiles `
    "Microsoft Power BI Desktop\bin"

$AnalysisServicesRoot = Join-Path `
    $env:LOCALAPPDATA `
    "Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"

$CoreAssemblyPath = Join-Path `
    $PowerBIBinPath `
    "Microsoft.AnalysisServices.Server.Core.dll"

$TabularAssemblyPath = Join-Path `
    $PowerBIBinPath `
    "Microsoft.AnalysisServices.Server.Tabular.dll"

foreach (
    $RequiredPath in @(
        $CoreAssemblyPath
        $TabularAssemblyPath
        $AnalysisServicesRoot
    )
) {
    if (-not (Test-Path -LiteralPath $RequiredPath)) {
        throw "Required Power BI path was not found: $RequiredPath"
    }
}

Add-Type -Path $CoreAssemblyPath
Add-Type -Path $TabularAssemblyPath

$Workspace = Get-ChildItem `
    -LiteralPath $AnalysisServicesRoot `
    -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $Workspace) {
    throw "No open Power BI Desktop model workspace was found."
}

$PortPath = Join-Path `
    $Workspace.FullName `
    "Data\msmdsrv.port.txt"

if (-not (Test-Path -LiteralPath $PortPath -PathType Leaf)) {
    throw "Power BI Desktop port file was not found: $PortPath"
}

$Port = (
    (Get-Content -LiteralPath $PortPath -Raw) `
        -replace "`0", ""
).Trim()

if ($Port -notmatch '^\d+$') {
    throw "Power BI Desktop returned an invalid local model port."
}

$Server = [Microsoft.AnalysisServices.Tabular.Server]::new()

try {
    $Server.Connect("localhost:$Port")

    if ($Server.Databases.Count -ne 1) {
        throw (
            "Expected one open Power BI model; found " +
            $Server.Databases.Count +
            "."
        )
    }

    $Database = $Server.Databases[0]
    $Model = $Database.Model

    $MerchantTable = $Model.Tables.Find(
        "dim_merchant_analytics"
    )

    if ($null -eq $MerchantTable) {
        throw "dim_merchant_analytics was not found in the open model."
    }

    $DateTable = $Model.Tables.Find(
        "dim_date_analytics"
    )

    if (
        $null -eq $DateTable -or
        $DateTable.DataCategory -ne "Time"
    ) {
        throw (
            "dim_date_analytics must exist and be marked as the " +
            "model's date table before auto-date objects are removed."
        )
    }

    $AddedColumns = [System.Collections.Generic.List[string]]::new()

    foreach (
        $ColumnContract in @(
            [ordered]@{
                Name = "merchant_id_text"
                SourceColumn = "merchant_id_text"
                IsHidden = $false
            }
            [ordered]@{
                Name = "merchant_display_label"
                SourceColumn = "merchant_display_label"
                IsHidden = $false
            }
        )
    ) {
        $ExistingColumn = $MerchantTable.Columns.Find(
            $ColumnContract.Name
        )

        if ($null -eq $ExistingColumn) {
            $NewColumn = (
                [Microsoft.AnalysisServices.Tabular.DataColumn]::new()
            )
            $NewColumn.Name = $ColumnContract.Name
            $NewColumn.SourceColumn = $ColumnContract.SourceColumn
            $NewColumn.DataType = (
                [Microsoft.AnalysisServices.Tabular.DataType]::String
            )
            $NewColumn.IsHidden = $ColumnContract.IsHidden
            $null = $MerchantTable.Columns.Add($NewColumn)
            $null = $AddedColumns.Add($ColumnContract.Name)
        }
        else {
            $ExistingColumn.SourceColumn = $ColumnContract.SourceColumn
            $ExistingColumn.DataType = (
                [Microsoft.AnalysisServices.Tabular.DataType]::String
            )
            $ExistingColumn.IsHidden = $ColumnContract.IsHidden
        }
    }

    $NumericMerchantId = $MerchantTable.Columns.Find(
        "merchant_id"
    )

    if ($null -eq $NumericMerchantId) {
        throw (
            "merchant_id was not found in dim_merchant_analytics; " +
            "the Power BI serving contract is incomplete."
        )
    }

    $NumericMerchantId.IsHidden = $true

    $MeasuresTable = $Model.Tables.Find("_Measures")
    $ProfileMeasure = if ($null -ne $MeasuresTable) {
        $MeasuresTable.Measures.Find(
            "Selected Merchant Profile"
        )
    }
    else {
        $null
    }

    if ($null -eq $ProfileMeasure) {
        throw "Selected Merchant Profile measure was not found."
    }

    $ProfileMeasure.Expression = @'
VAR MerchantLabel =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_display_label] )
VAR MerchantSourceID =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_id_text] )
VAR MerchantCity =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_city] )
VAR MerchantState =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_state] )
VAR MerchantZip =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_zip_code] )
VAR MerchantCategory =
    SELECTEDVALUE ( dim_merchant_analytics[merchant_category_code] )
RETURN
    IF (
        ISBLANK ( MerchantLabel ),
        "Drill through from Merchant Risk to select one merchant",
        MerchantLabel
            & "  |  Source ID " & MerchantSourceID
            & "  |  " & COALESCE ( MerchantCity, "ONLINE" )
            & IF (
                NOT ISBLANK ( MerchantState ),
                ", " & MerchantState,
                ""
            )
            & IF (
                NOT ISBLANK ( MerchantZip ),
                " " & MerchantZip,
                ""
            )
            & "  |  Category " & MerchantCategory
    )
'@

    $RemovedTables = [System.Collections.Generic.List[string]]::new()
    $RemovedVariations = [System.Collections.Generic.List[string]]::new()
    $RemovedRelationships = [System.Collections.Generic.List[string]]::new()

    if ($RemoveAutoDateTables) {
        $AutoDateTables = @(
            $Model.Tables |
            Where-Object {
                $_.Name -like "LocalDateTable_*" -or
                $_.Name -like "DateTableTemplate_*"
            }
        )

        $AutoDateTableNames = [System.Collections.Generic.HashSet[string]]::new(
            [System.StringComparer]::OrdinalIgnoreCase
        )

        foreach ($AutoDateTable in $AutoDateTables) {
            $null = $AutoDateTableNames.Add($AutoDateTable.Name)
        }

        # Power BI creates a Variation on the source timestamp column for
        # every automatic date hierarchy. The Variation must be removed
        # before its hidden table; otherwise SaveChanges fails because the
        # column still points to a hierarchy that no longer exists.
        foreach ($Table in @($Model.Tables)) {
            foreach ($Column in @($Table.Columns)) {
                foreach ($Variation in @($Column.Variations)) {
                    $VariationTableName = if (
                        $null -ne $Variation.DefaultHierarchy
                    ) {
                        $Variation.DefaultHierarchy.Table.Name
                    }
                    elseif ($null -ne $Variation.DefaultColumn) {
                        $Variation.DefaultColumn.Table.Name
                    }
                    else {
                        $null
                    }

                    if (
                        $null -ne $VariationTableName -and
                        $AutoDateTableNames.Contains($VariationTableName)
                    ) {
                        $RemovedVariationName = (
                            $Table.Name +
                            "[" +
                            $Column.Name +
                            "]." +
                            $Variation.Name
                        )
                        $null = $Column.Variations.Remove($Variation)
                        $null = $RemovedVariations.Add(
                            $RemovedVariationName
                        )
                    }
                }
            }
        }

        foreach ($Relationship in @($Model.Relationships)) {
            $ReferencesAutoDateTable = (
                $AutoDateTableNames.Contains(
                    $Relationship.FromTable.Name
                ) -or
                $AutoDateTableNames.Contains(
                    $Relationship.ToTable.Name
                )
            )

            if ($ReferencesAutoDateTable) {
                $null = $RemovedRelationships.Add(
                    $Relationship.Name
                )
                $null = $Model.Relationships.Remove($Relationship)
            }
        }

        foreach ($AutoDateTable in $AutoDateTables) {
            $null = $RemovedTables.Add($AutoDateTable.Name)
            $null = $Model.Tables.Remove($AutoDateTable)
        }
    }

    $ModelRefreshSeconds = $null

    if (
        $PSCmdlet.ShouldProcess(
            $Database.Name,
            "Save Power BI model hardening changes"
        )
    ) {
        $null = $Model.SaveChanges()

        if ($RefreshModel) {
            $RefreshTimer = [System.Diagnostics.Stopwatch]::StartNew()
            $Model.RequestRefresh(
                [Microsoft.AnalysisServices.Tabular.RefreshType]::Full
            )
            $null = $Model.SaveChanges()
            $RefreshTimer.Stop()
            $ModelRefreshSeconds = [math]::Round(
                $RefreshTimer.Elapsed.TotalSeconds,
                2
            )
        }
    }

    [pscustomobject]@{
        Database = $Database.Name
        Port = [int]$Port
        AddedColumns = @($AddedColumns)
        NumericMerchantIdHidden = (
            $NumericMerchantId.IsHidden
        )
        UpdatedMeasure = $ProfileMeasure.Name
        RemovedVariations = @($RemovedVariations)
        RemovedRelationships = @($RemovedRelationships)
        RemovedAutoDateTables = @($RemovedTables)
        ModelRefreshSeconds = $ModelRefreshSeconds
    } | Format-List
}
finally {
    if ($Server.Connected) {
        $Server.Disconnect()
    }
}
