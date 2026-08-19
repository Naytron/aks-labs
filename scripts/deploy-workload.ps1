[CmdletBinding()]
param(
    [ValidateSet('kind', 'azure')]
    [string]$Target = 'kind',
    [ValidateSet('automatic', 'standard')]
    [string]$Environment = 'standard',
    [ValidateSet('day2', 'day3', 'day4')]
    [string]$Stage = 'day2',
    [string]$Version = '0.1.0',
    [switch]$IncludeIdentity,
    [switch]$RenderOnly
)

. (Join-Path $PSScriptRoot 'common.ps1')

$root = Get-RepoRoot
$effectiveStage = if ($IncludeIdentity -and $Stage -eq 'day2') { 'day3' } else { $Stage }
if ($Target -eq 'azure' -and $Environment -eq 'automatic' -and $effectiveStage -ne 'day2') {
    throw 'AKS Automatic is used only for the Day 1/Day 2 workload stage in this course.'
}
$overlayName = if ($Target -eq 'azure') { "azure-$effectiveStage" } else { $Target }
$overlay = Join-Path $root "platform/environments/$overlayName"
$rendered = Invoke-Checked kubectl @('kustomize', $overlay) -Capture
$renderedText = $rendered -join [Environment]::NewLine

if ($Target -eq 'azure') {
    if ($effectiveStage -in @('day3', 'day4') -and $Environment -ne 'standard') {
        throw 'The identity component is available only in the Standard environment.'
    }
    $outputs = Get-DeploymentOutputs -Environment $Environment
    $renderedText = $renderedText.Replace(
        '${ACR_NAME}.azurecr.io',
        "$($outputs.registryName).azurecr.io"
    ).Replace(
        "$($outputs.registryName).azurecr.io/orders-api:0.1.0",
        "$($outputs.registryName).azurecr.io/orders-api:$Version"
    ).Replace(
        "$($outputs.registryName).azurecr.io/storefront:0.1.0",
        "$($outputs.registryName).azurecr.io/storefront:$Version"
    )

    if ($effectiveStage -in @('day3', 'day4')) {
        $renderedText = $renderedText.Replace(
            '${WORKLOAD_IDENTITY_CLIENT_ID}',
            $outputs.workloadIdentityClientId
        ).Replace(
            '${KEY_VAULT_NAME}',
            $outputs.keyVaultName
        ).Replace(
            '${TENANT_ID}',
            $outputs.tenantId
        )
    }
}

if ($renderedText -match '\$\{(ACR_NAME|WORKLOAD_IDENTITY_CLIENT_ID|KEY_VAULT_NAME|TENANT_ID)\}|REPLACE_WITH_|replacewithacr|replace-with-') {
    throw "Rendered $overlayName contains unresolved placeholders. Resolve the deployment outputs before applying it."
}

$expectedContext = if ($Target -eq 'kind') {
    'kind-aks-labs'
} else {
    $outputs.clusterName
}
Invoke-Checked kubectl @('config', 'use-context', $expectedContext)

$stateDirectory = Join-Path $root '.aks-labs'
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
$manifestName = if ($Target -eq 'kind') { 'rendered-kind.yaml' } else { "rendered-$Environment-$effectiveStage.yaml" }
$manifestPath = Join-Path $stateDirectory $manifestName
$renderedText | Set-Content -LiteralPath $manifestPath
if ($RenderOnly) {
    Write-Host "Rendered $manifestPath without applying it."
    exit 0
}

if ($Target -eq 'kind') {
    $ordersServiceType = (& kubectl --context $expectedContext get service orders-api -n orders -o jsonpath='{.spec.type}' 2>$null)
    if ($LASTEXITCODE -eq 0 -and $ordersServiceType -eq 'NodePort') {
        Write-Host 'Removing the intentionally incomplete Day 1 starter before full workload promotion...'
        Invoke-Checked kubectl @(
            '--context', $expectedContext,
            'delete',
            'deployment/orders-api',
            'service/orders-api',
            'configmap/orders-config',
            '--namespace', 'orders',
            '--ignore-not-found',
            '--wait=true'
        )
    }
}

Invoke-Checked kubectl @('--context', $expectedContext, 'apply', '--server-side', '--field-manager', 'aks-labs', '--filename', $manifestPath)
Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'status', 'deployment/storefront', '--namespace', 'orders', '--timeout', '5m')
Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'status', 'deployment/orders-api', '--namespace', 'orders', '--timeout', '5m')
Write-Host "Applied $manifestPath."
