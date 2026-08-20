<#
.SYNOPSIS
Injects or restores one deterministic ARC failure.

.DESCRIPTION
Changes one bounded ARC condition at a time. Scheduling removes the runner
toleration, Auth references a missing Secret, and Egress applies a
namespace-scoped deny policy.

.PARAMETER Scenario
Auth, Egress, or Scheduling.

.PARAMETER Restore
Restores the known-good setting for the selected scenario.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Auth', 'Egress', 'Scheduling')]
    [string]$Scenario,
    [switch]$Restore
)

. (Join-Path $PSScriptRoot 'arc-common.ps1')

Assert-Command kubectl
$null = Assert-ArcClusterContext
$helm = Get-ArcHelmCommand
$runnerChart = Get-ArcChartArguments -Chart RunnerScaleSet
$egressFailure = Join-Path (Get-RepoRoot) 'platform/arc/failures/deny-egress.yaml'
$verb = if ($Restore) { 'Restore' } else { 'Inject' }

if (-not $PSCmdlet.ShouldProcess("$($script:ArcRunnerRelease)/$Scenario", "$verb deterministic ARC failure")) {
    return
}

if ($Scenario -eq 'Egress') {
    if ($Restore) {
        Invoke-Checked kubectl @('delete', '-f', $egressFailure, '--ignore-not-found')
    } else {
        Invoke-Checked kubectl @('apply', '-f', $egressFailure)
    }
    Write-Host "$verb complete for ARC $Scenario scenario."
    exit 0
}

$overrideArguments = switch ($Scenario) {
    'Auth' {
        if ($Restore) {
            @('--set-string', "githubConfigSecret=$($script:ArcRunnerSecret)")
        } else {
            @('--set-string', 'githubConfigSecret=arc-github-app-missing')
        }
    }
    'Scheduling' {
        if ($Restore) {
            @(
                '--set-json',
                'template.spec.tolerations=[{"key":"workload","operator":"Equal","value":"github-runner","effect":"NoSchedule"}]'
            )
        } else {
            @('--set-json', 'template.spec.tolerations=[]')
        }
    }
}

$arguments = @(
    'upgrade', $script:ArcRunnerRelease,
    $runnerChart[0],
    '--version', $runnerChart[2],
    '--namespace', $script:ArcRunnerNamespace,
    '--reuse-values'
) + $overrideArguments
if ($Restore) {
    $arguments += @('--wait', '--timeout', '10m')
}
Invoke-Checked $helm $arguments
Write-Host "$verb complete for ARC $Scenario scenario."
