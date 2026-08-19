[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('kind', 'automatic', 'standard')]
    [string]$Environment
)

. (Join-Path $PSScriptRoot 'common.ps1')

$context = (& kubectl config current-context 2>$null)
if ($Environment -eq 'kind') {
    Write-Host "Environment: kind"
    Write-Host "Expected context: kind-aks-labs"
    Write-Host "Current context: $context"
    & kubectl --context kind-aks-labs get nodes
    & kubectl --context kind-aks-labs get deployment,service,pvc -n orders
    Write-Host 'Endpoint: http://localhost:8080'
    exit 0
}

$config = Get-LabConfiguration -AllowExpired
$outputs = Get-DeploymentOutputs -Environment $Environment
$resourceGroup = if ($Environment -eq 'automatic') { $config.AutomaticResourceGroup } else { $config.StandardResourceGroup }
$cluster = $outputs.clusterName
$clusterSummary = Invoke-Checked az @(
    'aks', 'show',
    '--resource-group', $resourceGroup,
    '--name', $cluster,
    '--query', '{power:powerState.code,provisioning:provisioningState,version:kubernetesVersion}',
    '--output', 'json',
    '--only-show-errors'
) -Capture | ConvertFrom-Json
$subscriptionName = Invoke-Checked az @(
    'account', 'show',
    '--query', 'name',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
$resourceCount = Invoke-Checked az @(
    'resource', 'list',
    '--resource-group', $resourceGroup,
    '--query', 'length(@)',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture

Write-Host "Environment: $Environment"
Write-Host "Subscription: $(($subscriptionName | Select-Object -First 1).Trim())"
Write-Host "Resource group: $resourceGroup"
Write-Host "Cluster: $cluster"
Write-Host "Power/provisioning: $($clusterSummary.power) / $($clusterSummary.provisioning)"
Write-Host "Kubernetes: $($clusterSummary.version)"
Write-Host "Current/expected context: $context / $cluster"
Write-Host "Top-level resources: $resourceCount"
Write-Host "Expiration: $($config.Expiration)"

if ($clusterSummary.power -eq 'Running' -and $context -eq $cluster) {
    & kubectl --context $cluster get deployment,service,pvc -n orders 2>$null
    $gateway = (& kubectl --context $cluster get gateway orders -n orders -o jsonpath='{.status.addresses[0].value}' 2>$null)
    if ($gateway) {
        Write-Host "Gateway address: $gateway"
    } else {
        Write-Host 'Gateway address: not assigned'
    }
}
