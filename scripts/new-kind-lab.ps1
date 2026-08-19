[CmdletBinding()]
param(
    [switch]$Recreate,
    [switch]$Starter
)

. (Join-Path $PSScriptRoot 'common.ps1')

$root = Get-RepoRoot
$exists = (& kind get clusters 2>$null) -contains 'aks-labs'
if ($exists -and $Recreate) {
    Invoke-Checked kind @('delete', 'cluster', '--name', 'aks-labs')
    $exists = $false
}
if (-not $exists) {
    Invoke-Checked kind @(
        'create', 'cluster',
        '--config', (Join-Path $root 'platform/environments/kind/kind-cluster.yaml'),
        '--wait', '120s'
    )
}
Invoke-Checked kubectl @('config', 'use-context', 'kind-aks-labs')
Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $root 'scripts/build-images.ps1'), '-Target', 'kind')
if ($Starter) {
    Invoke-Checked kubectl @('--context', 'kind-aks-labs', 'apply', '--server-side', '--field-manager', 'aks-labs-starter', '--kustomize', (Join-Path $root 'labs/01-foundations/starter'))
    Invoke-Checked kubectl @('--context', 'kind-aks-labs', 'rollout', 'status', 'deployment/orders-api', '--namespace', 'orders', '--timeout', '3m')
    Write-Host 'Day 1 starter API is available at http://localhost:8080.'
} else {
    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $root 'scripts/deploy-workload.ps1'), '-Target', 'kind')
    Write-Host 'Full local lab is available at http://localhost:8080.'
}
