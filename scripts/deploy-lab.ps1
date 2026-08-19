[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('automatic', 'standard')]
    [string]$Environment,
    [switch]$WhatIf,
    [switch]$SkipPostDeploy,
    [ValidateRange(0, 500)]
    [int]$BudgetAmountOverride = 0,
    [ValidateRange(5, 60)]
    [int]$ProvisioningTimeoutMinutes = 60
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$root = Get-RepoRoot
$template = Join-Path $root "infra/$Environment/main.bicep"
$stateDirectory = Join-Path $root '.aks-labs'
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null

$deployerObjectId = Invoke-Checked az @(
    'ad', 'signed-in-user', 'show',
    '--query', 'id',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
if (-not $deployerObjectId) {
    throw 'Could not resolve the signed-in user object ID. Use an interactive user with Owner on the dedicated lab scope.'
}
$deployerObjectId = ($deployerObjectId | Select-Object -First 1).Trim()

$deploymentName = "aks-labs-$Environment-$($config.Prefix)-$($config.Location)"
$parameterFile = Join-Path $stateDirectory "$Environment-parameters.json"
$parameterValues = @{
    prefix = @{ value = $config.Prefix }
    location = @{ value = $config.Location }
    nodeVmSize = @{ value = $config.NodeVmSize }
    expiration = @{ value = $config.Expiration }
    deployerObjectId = @{ value = $deployerObjectId }
    budgetAmount = @{
        value = if ($Environment -eq 'automatic') {
            [Math]::Min(30, $(if ($BudgetAmountOverride -gt 0) { $BudgetAmountOverride } else { $config.Budget }))
        } else {
            $(if ($BudgetAmountOverride -gt 0) { $BudgetAmountOverride } else { $config.Budget })
        }
    }
}
if ($Environment -eq 'standard') {
    $parameterValues.apiServerAuthorizedIpRanges = @{ value = $config.AuthorizedIpRanges }
}
@{
    '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
    contentVersion = '1.0.0.0'
    parameters = $parameterValues
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $parameterFile

$commonArguments = @(
    '--name', $deploymentName,
    '--location', $config.Location,
    '--template-file', $template,
    '--parameters', "@$parameterFile",
    '--only-show-errors'
)

Write-Host 'Running mandatory subscription deployment preview...'
Invoke-Checked az (@('deployment', 'sub', 'what-if') + $commonArguments)
if ($WhatIf) {
    Write-Host 'Preview complete; no Azure resources were changed.'
    exit 0
}

Write-Host "Deploying $Environment environment..."
Invoke-Checked az (@('deployment', 'sub', 'create', '--no-wait', '--output', 'none') + $commonArguments)

$deploymentSucceeded = $false
$maxAttempts = $ProvisioningTimeoutMinutes * 4
for ($attempt = 0; $attempt -lt $maxAttempts; $attempt++) {
    $deployment = Invoke-Checked az @(
        'deployment', 'sub', 'show',
        '--name', $deploymentName,
        '--query', 'properties.{state:provisioningState,error:error.message}',
        '--output', 'json',
        '--only-show-errors'
    ) -Capture | ConvertFrom-Json
    if ($deployment.state -eq 'Succeeded') {
        $deploymentSucceeded = $true
        break
    }
    if ($deployment.state -in @('Canceled', 'Failed')) {
        throw "Azure deployment entered $($deployment.state): $($deployment.error)"
    }
    if ($attempt % 4 -eq 0) {
        Write-Host "Deployment state: $($deployment.state) ($([Math]::Round($attempt * 15 / 60, 1)) minutes)"
    }
    Start-Sleep -Seconds 15
}
if (-not $deploymentSucceeded) {
    throw "Azure deployment did not finish within $ProvisioningTimeoutMinutes minutes. Inspect it before retrying or deleting."
}

$outputs = Invoke-Checked az @(
    'deployment', 'sub', 'show',
    '--name', $deploymentName,
    '--query', 'properties.outputs',
    '--output', 'json',
    '--only-show-errors'
) -Capture | ConvertFrom-Json

$flatOutputs = [ordered]@{}
foreach ($property in $outputs.PSObject.Properties) {
    $flatOutputs[$property.Name] = $property.Value.value
}
$outputPath = Join-Path $stateDirectory "$Environment-outputs.json"
$flatOutputs | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $outputPath

if (-not $SkipPostDeploy) {
    $resourceGroup = $flatOutputs.resourceGroupName
    $cluster = $flatOutputs.clusterName

    Write-Host 'Enabling managed Gateway API CRDs...'
    Invoke-Checked az @(
        'aks', 'update',
        '--resource-group', $resourceGroup,
        '--name', $cluster,
        '--enable-gateway-api',
        '--only-show-errors',
        '--output', 'none'
    )

    Write-Host 'Enabling the managed application-routing Gateway controller...'
    Invoke-Checked az @(
        'aks', 'update',
        '--resource-group', $resourceGroup,
        '--name', $cluster,
        '--enable-app-routing-istio',
        '--only-show-errors',
        '--output', 'none'
    )

    if ($Environment -eq 'standard') {
        Write-Host 'Enabling Azure Monitor managed Prometheus...'
        Invoke-Checked az @(
            'aks', 'update',
            '--resource-group', $resourceGroup,
            '--name', $cluster,
            '--enable-azure-monitor-metrics',
            '--azure-monitor-workspace-resource-id', $flatOutputs.azureMonitorWorkspaceResourceId,
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

    $gatewayReady = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & kubectl --context $cluster get crd gateways.gateway.networking.k8s.io --output name 2>$null | Out-Null
        $crdReady = $LASTEXITCODE -eq 0
        & kubectl --context $cluster get gatewayclass approuting-istio --output name 2>$null | Out-Null
        $classReady = $LASTEXITCODE -eq 0
        if ($crdReady -and $classReady) {
            $gatewayReady = $true
            break
        }
        Start-Sleep -Seconds 5
    }
    if (-not $gatewayReady) {
        throw 'Managed Gateway API did not become ready. Inspect the AKS add-on before workload deployment.'
    }
}

Write-Host "Deployment complete. Non-secret outputs: $outputPath"
