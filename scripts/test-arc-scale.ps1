<#
.SYNOPSIS
Dispatches the private ARC workflow and records runner and node scaling evidence.

.PARAMETER RepositoryUrl
HTTPS URL of the instructor-approved private sandbox repository.

.PARAMETER WorkflowFile
Workflow filename copied to the private repository.

.PARAMETER Ref
Private repository branch containing the workflow.

.PARAMETER RunTimeoutMinutes
Maximum wait for the GitHub workflow to complete.

.PARAMETER NodeScaleDownTimeoutMinutes
Maximum wait for the AKS runner pool to return to zero. Use zero to skip node wait.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl,
    [string]$WorkflowFile = 'arc-scale-test.yml',
    [string]$Ref = 'main',
    [ValidateRange(5, 45)]
    [int]$RunTimeoutMinutes = 30,
    [ValidateRange(0, 30)]
    [int]$NodeScaleDownTimeoutMinutes = 30
)

. (Join-Path $PSScriptRoot 'arc-common.ps1')

Assert-Command gh
Assert-Command kubectl
$context = Assert-ArcClusterContext
$slug = Assert-PrivateArcRepository -RepositoryUrl $RepositoryUrl
$evidenceDirectory = New-EvidenceDirectory
$evidencePath = Join-Path $evidenceDirectory 'arc-scale-timeline.json'
$timeline = [System.Collections.Generic.List[object]]::new()
$runId = $null
$conclusion = $null
$maximumRunnerPods = 0
$maximumRunnerNodes = 0

function Get-ArcScaleSample {
    $podsJson = & kubectl get pods -n $script:ArcRunnerNamespace -o json 2>$null
    $pods = if ($LASTEXITCODE -eq 0 -and $podsJson) {
        @(($podsJson | ConvertFrom-Json).items)
    } else {
        @()
    }
    $runnerPods = @($pods | Where-Object { $_.metadata.name -notmatch 'listener' }).Count

    $ephemeralJson = & kubectl get ephemeralrunners.actions.github.com `
        -n $script:ArcRunnerNamespace `
        -o json 2>$null
    $ephemeralRunners = if ($LASTEXITCODE -eq 0 -and $ephemeralJson) {
        @((($ephemeralJson | ConvertFrom-Json).items)).Count
    } else {
        0
    }

    $nodeCountText = & az aks nodepool show `
        --resource-group $context.ResourceGroup `
        --cluster-name $context.ClusterName `
        --name $context.RunnerNodePool `
        --query count `
        --output tsv `
        --only-show-errors 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to read the ARC runner node-pool count.'
    }
    $nodeCount = [int](($nodeCountText | Select-Object -First 1).Trim())

    return [pscustomobject]@{
        timestamp = [DateTime]::UtcNow.ToString('o')
        runnerPods = $runnerPods
        ephemeralRunners = $ephemeralRunners
        runnerNodes = $nodeCount
    }
}

try {
    & gh workflow view $WorkflowFile --repo $slug 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow '$WorkflowFile' is not available on the private sandbox default branch."
    }

    $started = [DateTime]::UtcNow.AddSeconds(-5)
    Invoke-Checked gh @(
        'workflow', 'run', $WorkflowFile,
        '--repo', $slug,
        '--ref', $Ref
    )

    $discoveryDeadline = [DateTime]::UtcNow.AddMinutes(2)
    do {
        $runs = Invoke-Checked gh @(
            'run', 'list',
            '--repo', $slug,
            '--workflow', $WorkflowFile,
            '--event', 'workflow_dispatch',
            '--limit', '10',
            '--json', 'databaseId,createdAt,status,conclusion'
        ) -Capture | ConvertFrom-Json
        $run = @(
            $runs |
                Where-Object { [DateTime]::Parse($_.createdAt).ToUniversalTime() -ge $started } |
                Sort-Object { [DateTime]::Parse($_.createdAt) } -Descending
        ) | Select-Object -First 1
        if ($run) {
            $runId = [long]$run.databaseId
            break
        }
        Start-Sleep -Seconds 5
    } while ([DateTime]::UtcNow -lt $discoveryDeadline)

    if (-not $runId) {
        throw 'The dispatched ARC workflow run was not discovered within two minutes.'
    }

    $runDeadline = [DateTime]::UtcNow.AddMinutes($RunTimeoutMinutes)
    do {
        $run = Invoke-Checked gh @(
            'run', 'view', "$runId",
            '--repo', $slug,
            '--json', 'status,conclusion'
        ) -Capture | ConvertFrom-Json
        $sample = Get-ArcScaleSample
        $timeline.Add($sample)
        $maximumRunnerPods = [Math]::Max($maximumRunnerPods, [int]$sample.runnerPods)
        $maximumRunnerNodes = [Math]::Max($maximumRunnerNodes, [int]$sample.runnerNodes)
        if ($run.status -eq 'completed') {
            $conclusion = $run.conclusion
            break
        }
        Start-Sleep -Seconds 10
    } while ([DateTime]::UtcNow -lt $runDeadline)

    if (-not $conclusion) {
        throw "The ARC workflow did not complete within $RunTimeoutMinutes minutes."
    }
    if ($conclusion -ne 'success') {
        throw "The ARC workflow concluded with '$conclusion'."
    }
    if ($maximumRunnerPods -lt 2) {
        throw "Only $maximumRunnerPods concurrent runner pod(s) were observed; expected at least two."
    }
    if ($maximumRunnerNodes -lt 1) {
        throw 'No dedicated runner node was observed during the workflow.'
    }

    $cleanupWaitMinutes = if ($NodeScaleDownTimeoutMinutes -eq 0) {
        5
    } else {
        $NodeScaleDownTimeoutMinutes
    }
    $scaleDownDeadline = [DateTime]::UtcNow.AddMinutes($cleanupWaitMinutes)
    do {
        $sample = Get-ArcScaleSample
        $timeline.Add($sample)
        if (
            $sample.runnerPods -eq 0 -and
            $sample.ephemeralRunners -eq 0 -and
            ($NodeScaleDownTimeoutMinutes -eq 0 -or $sample.runnerNodes -eq 0)
        ) {
            break
        }
        Start-Sleep -Seconds 15
    } while ([DateTime]::UtcNow -lt $scaleDownDeadline)

    $finalSample = $timeline[$timeline.Count - 1]
    if ($finalSample.runnerPods -ne 0 -or $finalSample.ephemeralRunners -ne 0) {
        throw 'Ephemeral runner pods or custom resources remain after the workflow completed.'
    }
    if ($NodeScaleDownTimeoutMinutes -gt 0 -and $finalSample.runnerNodes -ne 0) {
        throw "Runner node pool did not scale to zero within $NodeScaleDownTimeoutMinutes minutes."
    }
} finally {
    [pscustomobject]@{
        workflowRunRecorded = [bool]$runId
        conclusion = $conclusion
        maximumRunnerPods = $maximumRunnerPods
        maximumRunnerNodes = $maximumRunnerNodes
        samples = $timeline
    } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $evidencePath
}

Write-Host "ARC workflow passed and scaled back to zero. Evidence: $evidencePath"
