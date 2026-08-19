[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('automatic', 'standard')]
    [string]$Environment
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment $Environment
$resourceGroup = if ($Environment -eq 'automatic') { $config.AutomaticResourceGroup } else { $config.StandardResourceGroup }
$cluster = $outputs.clusterName

Assert-CourseResourceGroup $resourceGroup
$powerState = Invoke-Checked az @(
    'aks', 'show',
    '--resource-group', $resourceGroup,
    '--name', $cluster,
    '--query', 'powerState.code',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture

if (($powerState | Select-Object -First 1).Trim() -eq 'Stopped') {
    Write-Host "Starting $cluster..."
    Invoke-Checked az @(
        'aks', 'start',
        '--resource-group', $resourceGroup,
        '--name', $cluster,
        '--only-show-errors',
        '--output', 'none'
    )
}

Invoke-Checked az @(
    'aks', 'get-credentials',
    '--resource-group', $resourceGroup,
    '--name', $cluster,
    '--format', 'exec',
    '--overwrite-existing',
    '--only-show-errors'
)
Invoke-Checked kubelogin @('convert-kubeconfig', '-l', 'azurecli')
Invoke-Checked kubectl @('config', 'use-context', $cluster)
Invoke-Checked kubectl @('--context', $cluster, 'wait', '--for=condition=Ready', 'nodes', '--all', '--timeout=10m')

Write-Host "$cluster is running and selected. Run ./scripts/show-lab.ps1 -Environment $Environment."
