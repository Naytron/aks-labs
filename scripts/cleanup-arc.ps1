<#
.SYNOPSIS
Removes the optional ARC module in a GitHub-safe order.

.DESCRIPTION
Uninstalls runner scale sets before the controller, waits for ARC custom resources
to disappear, removes the authentication Secret and namespaces, deletes the runner
node pool, and optionally verifies the dedicated sandbox has no runner registrations.

.PARAMETER RepositoryUrl
Private sandbox URL used for GitHub-side cleanup verification.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidatePattern('^$|^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl = ''
)

. (Join-Path $PSScriptRoot 'arc-common.ps1')

Assert-Command kubectl
$context = Assert-ArcClusterContext
$helm = Get-ArcHelmCommand
$platformPath = Join-Path (Get-RepoRoot) 'platform/arc'

if (-not $PSCmdlet.ShouldProcess(
    "$($context.ClusterName) ARC extension",
    'Remove runner scale set, GitHub App Secret, controller, namespaces, and runner node pool'
)) {
    return
}

& $helm status $script:ArcRunnerRelease --namespace $script:ArcRunnerNamespace 1>$null 2>$null
$runnerReleaseExists = $LASTEXITCODE -eq 0
& $helm status $script:ArcControllerRelease --namespace $script:ArcSystemNamespace 1>$null 2>$null
$controllerReleaseExists = $LASTEXITCODE -eq 0

if ($runnerReleaseExists -and -not $controllerReleaseExists) {
    throw 'Runner scale set exists without its controller. Reinstall the pinned controller before cleanup so GitHub-side state can be removed safely.'
}

if ($runnerReleaseExists) {
    Invoke-Checked $helm @(
        'uninstall', $script:ArcRunnerRelease,
        '--namespace', $script:ArcRunnerNamespace,
        '--wait',
        '--timeout', '10m'
    )
}

$cleanupDeadline = [DateTime]::UtcNow.AddMinutes(10)
do {
    $remaining = 0
    foreach ($target in @(
        @{ Resource = 'autoscalingrunnersets.actions.github.com'; Namespace = $script:ArcRunnerNamespace },
        @{ Resource = 'ephemeralrunnersets.actions.github.com'; Namespace = $script:ArcRunnerNamespace },
        @{ Resource = 'ephemeralrunners.actions.github.com'; Namespace = $script:ArcRunnerNamespace },
        @{ Resource = 'autoscalinglisteners.actions.github.com'; Namespace = $script:ArcSystemNamespace }
    )) {
        $items = @(
            & kubectl get $($target.Resource) --namespace $($target.Namespace) --output name 2>$null
        )
        if ($LASTEXITCODE -eq 0) {
            $remaining += @($items | Where-Object { $_ }).Count
        }
    }
    if ($remaining -eq 0) {
        break
    }
    Start-Sleep -Seconds 10
} while ([DateTime]::UtcNow -lt $cleanupDeadline)
if ($remaining -ne 0) {
    throw "$remaining ARC runner custom resource(s) remain; preserving the controller and Secret for safe reconciliation."
}

Invoke-Checked kubectl @(
    'delete', 'secret', $script:ArcRunnerSecret,
    '--namespace', $script:ArcRunnerNamespace,
    '--ignore-not-found'
)

if ($controllerReleaseExists) {
    Invoke-Checked $helm @(
        'uninstall', $script:ArcControllerRelease,
        '--namespace', $script:ArcSystemNamespace,
        '--wait',
        '--timeout', '10m'
    )
}

Invoke-Checked kubectl @('delete', '-k', $platformPath, '--ignore-not-found')
Invoke-Checked kubectl @(
    'delete', 'namespace',
    $script:ArcRunnerNamespace,
    $script:ArcSystemNamespace,
    '--ignore-not-found',
    '--wait=true',
    '--timeout=5m'
)

Invoke-Checked pwsh @(
    '-NoProfile',
    '-File', (Join-Path $PSScriptRoot 'manage-arc-runner-pool.ps1'),
    '-Action', 'Delete',
    '-Confirm:$false'
)

if ($RepositoryUrl) {
    $slug = Assert-PrivateArcRepository -RepositoryUrl $RepositoryUrl
    $runnerCount = Invoke-Checked gh @(
        'api', "repos/$slug/actions/runners",
        '--jq', '.total_count'
    ) -Capture
    if ([int](($runnerCount | Select-Object -First 1).Trim()) -ne 0) {
        throw 'GitHub still reports self-hosted runner registrations in the dedicated sandbox.'
    }
} else {
    Write-Warning 'RepositoryUrl was not supplied, so GitHub-side runner registration could not be independently verified.'
}

$validationArguments = @(
    '-NoProfile',
    '-File', (Join-Path $PSScriptRoot 'validate-arc.ps1'),
    '-Check', 'Cleanup'
)
if ($RepositoryUrl) {
    $validationArguments += @('-RepositoryUrl', $RepositoryUrl)
}
Invoke-Checked pwsh $validationArguments

Write-Host 'ARC cleanup completed. CRDs are retained because they may be shared by other controller installations.'
