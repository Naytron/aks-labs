[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('kind', 'acr')]
    [string]$Target,
    [ValidateSet('automatic', 'standard')]
    [string]$Environment = 'standard',
    [string]$Version = '0.1.0'
)

. (Join-Path $PSScriptRoot 'common.ps1')

$root = Get-RepoRoot
if ($Target -eq 'kind') {
    Invoke-Checked docker @('build', '--tag', "aks-labs/orders-api:dev", (Join-Path $root 'app/orders-api'))
    Invoke-Checked docker @('build', '--tag', "aks-labs/storefront:dev", (Join-Path $root 'app/storefront'))
    Invoke-Checked kind @('load', 'docker-image', 'aks-labs/orders-api:dev', 'aks-labs/storefront:dev', '--name', 'aks-labs')
    Write-Host 'Loaded course images into kind cluster aks-labs.'
    exit 0
}

$outputs = Get-DeploymentOutputs -Environment $Environment
Invoke-Checked az @(
    'acr', 'build',
    '--registry', $outputs.registryName,
    '--image', "orders-api:$Version",
    (Join-Path $root 'app/orders-api'),
    '--only-show-errors',
    '--output', 'none'
)
Invoke-Checked az @(
    'acr', 'build',
    '--registry', $outputs.registryName,
    '--image', "storefront:$Version",
    (Join-Path $root 'app/storefront'),
    '--only-show-errors',
    '--output', 'none'
)
Write-Host "Built images in $($outputs.registryName).azurecr.io for $Environment."
