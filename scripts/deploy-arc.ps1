<#
.SYNOPSIS
Installs the pinned ARC controller and an ephemeral runner scale set.

.DESCRIPTION
Refuses public targets, verifies private repository visibility with GitHub CLI,
creates the GitHub App Secret without printing key data, deploys the isolated
runner node pool, and installs ARC with Helm 3.

.PARAMETER RepositoryUrl
HTTPS URL of the instructor-approved private sandbox repository.

.PARAMETER GitHubAppId
Numeric GitHub App ID. Required for a live installation.

.PARAMETER GitHubAppInstallationId
Numeric installation ID for the App on the private sandbox.

.PARAMETER GitHubAppPrivateKeyPath
Path to an ignored or external PEM key file. Key contents never enter Helm values.

.PARAMETER MaxRunners
Bounded ARC runner and node-pool maximum, from two through five.

.PARAMETER DryRun
Renders both pinned charts without contacting GitHub, Azure, or Kubernetes.

.PARAMETER DeletePrivateKeyAfterInstall
Deletes the temporary local PEM file only after ARC installation validates.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl,
    [ValidatePattern('^$|^[0-9]+$')]
    [string]$GitHubAppId = '',
    [ValidatePattern('^$|^[0-9]+$')]
    [string]$GitHubAppInstallationId = '',
    [string]$GitHubAppPrivateKeyPath = '',
    [ValidateRange(2, 5)]
    [int]$MaxRunners = 3,
    [switch]$DryRun,
    [switch]$DeletePrivateKeyAfterInstall
)

. (Join-Path $PSScriptRoot 'arc-common.ps1')

Assert-Command kubectl
$repoRoot = Get-RepoRoot
$helm = Get-ArcHelmCommand
$configuration = Get-ArcConfiguration
$controllerValues = Join-Path $repoRoot 'platform/arc/controller-values.yaml'
$runnerValues = Join-Path $repoRoot 'platform/arc/runner-scale-set-values.yaml'
$platformPath = Join-Path $repoRoot 'platform/arc'
$controllerChart = Get-ArcChartArguments -Chart Controller
$runnerChart = Get-ArcChartArguments -Chart RunnerScaleSet
$null = Get-ArcRepositorySlug -RepositoryUrl $RepositoryUrl

if ($DryRun) {
    Write-Host "Rendering pinned ARC $($configuration.controllerChartVersion) charts with Helm $($configuration.helmMajorVersion)..."
    Invoke-Checked $helm @(
        'template', $script:ArcControllerRelease,
        $controllerChart[0],
        '--version', $controllerChart[2],
        '--namespace', $script:ArcSystemNamespace,
        '--include-crds',
        '--values', $controllerValues
    ) | Out-Null
    Invoke-Checked $helm @(
        'template', $script:ArcRunnerRelease,
        $runnerChart[0],
        '--version', $runnerChart[2],
        '--namespace', $script:ArcRunnerNamespace,
        '--values', $runnerValues,
        '--set-string', "githubConfigUrl=$RepositoryUrl",
        '--set-string', "githubConfigSecret=$($script:ArcRunnerSecret)",
        '--set', 'minRunners=0',
        '--set', "maxRunners=$MaxRunners"
    ) | Out-Null
    Write-Host 'ARC Helm rendering passed. No cluster, GitHub, or Azure state changed.'
    exit 0
}

foreach ($required in @{
    GitHubAppId = $GitHubAppId
    GitHubAppInstallationId = $GitHubAppInstallationId
    GitHubAppPrivateKeyPath = $GitHubAppPrivateKeyPath
}.GetEnumerator()) {
    if (-not $required.Value) {
        throw "-$($required.Key) is required unless -DryRun is used."
    }
}

$privateKeyPath = Assert-ArcPrivateKeyFile -Path $GitHubAppPrivateKeyPath
$null = Assert-PrivateArcRepository -RepositoryUrl $RepositoryUrl
$context = Assert-ArcClusterContext

if (-not $PSCmdlet.ShouldProcess(
    "$($context.ClusterName) and the verified private sandbox repository",
    "Install ARC $($configuration.controllerChartVersion) with at most $MaxRunners ephemeral runners"
)) {
    return
}

Invoke-Checked pwsh @(
    '-NoProfile',
    '-File', (Join-Path $PSScriptRoot 'manage-arc-runner-pool.ps1'),
    '-Action', 'Deploy',
    '-MaxCount', "$MaxRunners",
    '-Confirm:$false'
)

Invoke-Checked kubectl @('apply', '-k', $platformPath)

$secretJson = & kubectl create secret generic $script:ArcRunnerSecret `
    --namespace $script:ArcRunnerNamespace `
    --from-literal "github_app_id=$GitHubAppId" `
    --from-literal "github_app_installation_id=$GitHubAppInstallationId" `
    --from-file "github_app_private_key=$privateKeyPath" `
    --dry-run client `
    --output json
if ($LASTEXITCODE -ne 0 -or -not $secretJson) {
    throw 'Failed to render the GitHub App Kubernetes Secret.'
}
$secretJson | & kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to apply the GitHub App Kubernetes Secret.'
}
$secretJson = $null

Invoke-Checked $helm @(
    'upgrade', '--install', $script:ArcControllerRelease,
    $controllerChart[0],
    '--version', $controllerChart[2],
    '--namespace', $script:ArcSystemNamespace,
    '--values', $controllerValues,
    '--atomic',
    '--wait',
    '--timeout', '10m'
)

Invoke-Checked $helm @(
    'upgrade', '--install', $script:ArcRunnerRelease,
    $runnerChart[0],
    '--version', $runnerChart[2],
    '--namespace', $script:ArcRunnerNamespace,
    '--values', $runnerValues,
    '--set-string', "githubConfigUrl=$RepositoryUrl",
    '--set-string', "githubConfigSecret=$($script:ArcRunnerSecret)",
    '--set', 'minRunners=0',
    '--set', "maxRunners=$MaxRunners",
    '--atomic',
    '--wait',
    '--timeout', '10m'
)

Invoke-Checked pwsh @(
    '-NoProfile',
    '-File', (Join-Path $PSScriptRoot 'validate-arc.ps1'),
    '-Check', 'Install'
)

if (
    $DeletePrivateKeyAfterInstall -and
    $PSCmdlet.ShouldProcess($privateKeyPath, 'Delete the temporary ignored GitHub App private-key file')
) {
    Remove-Item -LiteralPath $privateKeyPath -Force
}

Write-Host "ARC is ready for the private sandbox with minRunners=0 and maxRunners=$MaxRunners."
