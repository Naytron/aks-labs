[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl,
    [string]$Branch = 'main',
    [ValidateSet('day3', 'day4')]
    [string]$Stage = 'day3'
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment standard
$cluster = $outputs.clusterName
$resourceGroup = $config.StandardResourceGroup

Assert-CourseResourceGroup $resourceGroup
if ($RepositoryUrl -match '@|[?&](token|password|key)=') {
    throw 'RepositoryUrl must be a public credential-free HTTPS GitHub URL.'
}

if (-not $PSCmdlet.ShouldProcess("$cluster/orders", "Reconcile platform/environments/azure-$Stage from $RepositoryUrl ($Branch)")) {
    return
}

Invoke-Checked az @('extension', 'add', '--name', 'k8s-configuration', '--upgrade', '--yes', '--only-show-errors')

& az k8s-configuration flux show `
    --resource-group $resourceGroup `
    --cluster-name $cluster `
    --cluster-type managedClusters `
    --name orders `
    --only-show-errors `
    --output none 2>$null
$exists = $LASTEXITCODE -eq 0

if ($exists) {
    Invoke-Checked az @(
        'k8s-configuration', 'flux', 'delete',
        '--resource-group', $resourceGroup,
        '--cluster-name', $cluster,
        '--cluster-type', 'managedClusters',
        '--name', 'orders',
        '--yes',
        '--only-show-errors',
        '--output', 'none'
    )
}

Invoke-Checked az @(
    'k8s-configuration', 'flux', 'create',
    '--resource-group', $resourceGroup,
    '--cluster-name', $cluster,
    '--cluster-type', 'managedClusters',
    '--name', 'orders',
    '--scope', 'cluster',
    '--namespace', 'flux-system',
    '--kind', 'git',
    '--url', $RepositoryUrl,
    '--branch', $Branch,
    '--sync-interval', '1m',
    '--only-show-errors',
    '--output', 'none'
)

$sourceName = $null
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $sourceName = (& kubectl --context $cluster get gitrepository -n flux-system -o jsonpath='{.items[0].metadata.name}' 2>$null)
    if ($LASTEXITCODE -eq 0 -and $sourceName) { break }
    Start-Sleep -Seconds 5
}
if (-not $sourceName) {
    throw 'Managed Flux did not create a GitRepository source within five minutes.'
}

$valuesManifest = @"
apiVersion: v1
kind: ConfigMap
metadata:
  name: course-values
  namespace: flux-system
data:
  ACR_NAME: "$($outputs.registryName)"
  WORKLOAD_IDENTITY_CLIENT_ID: "$($outputs.workloadIdentityClientId)"
  KEY_VAULT_NAME: "$($outputs.keyVaultName)"
  TENANT_ID: "$($outputs.tenantId)"
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: orders-workload
  namespace: flux-system
spec:
  interval: 1m
  path: ./platform/environments/azure-$Stage
  prune: true
  sourceRef:
    kind: GitRepository
    name: $sourceName
  postBuild:
    substituteFrom:
      - kind: ConfigMap
        name: course-values
  wait: true
  timeout: 5m
"@

$valuesManifest | & kubectl --context $cluster apply -f -
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to apply the Flux substitution values and workload Kustomization.'
}
Invoke-Checked kubectl @(
    '--context', $cluster,
    'wait',
    '--for=condition=Ready',
    'kustomization/orders-workload',
    '--namespace', 'flux-system',
    '--timeout', '10m'
)

$renderArguments = @(
    '-NoProfile',
    '-File', (Join-Path $PSScriptRoot 'deploy-workload.ps1'),
    '-Target', 'azure',
    '-Environment', 'standard',
    '-Stage', $Stage,
    '-RenderOnly'
)
Invoke-Checked pwsh $renderArguments

Write-Host "Managed Flux is reconciling platform/environments/azure-$Stage from $RepositoryUrl ($Branch) with cluster-local non-secret substitutions."
