[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('dns', 'imagepull', 'network', 'oom', 'readiness', 'rollout', 'scheduling')]
    [string]$Scenario,
    [Parameter(Mandatory)]
    [ValidateSet('kind', 'automatic', 'standard')]
    [string]$Environment,
    [ValidateSet('day2', 'day3', 'day4')]
    [string]$Stage = 'day2',
    [switch]$Restore
)

. (Join-Path $PSScriptRoot 'common.ps1')

$expectedContext = if ($Environment -eq 'kind') {
    'kind-aks-labs'
} else {
    (Get-DeploymentOutputs -Environment $Environment).clusterName
}
$currentContext = (& kubectl config current-context 2>$null)
if ($LASTEXITCODE -ne 0 -or $currentContext -ne $expectedContext) {
    throw "Refusing failure injection: context '$currentContext' is not '$expectedContext'."
}

$namespaceLabel = (& kubectl --context $expectedContext get namespace orders -o jsonpath='{.metadata.labels.aks-course}' 2>$null)
if ($LASTEXITCODE -ne 0 -or $namespaceLabel -ne 'level400') {
    throw 'Refusing failure injection: orders namespace is not labeled aks-course=level400.'
}

if ($Restore) {
    $root = Get-RepoRoot
    $manifestName = if ($Environment -eq 'kind') { 'rendered-kind.yaml' } else { "rendered-$Environment-$Stage.yaml" }
    $rendered = Join-Path $root ".aks-labs/$manifestName"
    if (-not (Test-Path -LiteralPath $rendered)) {
        throw "Baseline manifest not found at $rendered. Run deploy-workload.ps1 first."
    }
    & kubectl --context $expectedContext set env deployment/orders-api FAIL_READINESS- --namespace orders *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to remove injected readiness environment variable.'
    }
    & kubectl --context $expectedContext patch deployment storefront `
        --namespace orders `
        --type merge `
        --patch '{"spec":{"template":{"spec":{"nodeSelector":null}}}}' *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Failed to remove injected scheduling constraint.'
    }
    Invoke-Checked kubectl @(
        '--context', $expectedContext,
        'apply',
        '--server-side',
        '--force-conflicts',
        '--field-manager', 'aks-labs',
        '--filename', $rendered
    )
    Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'restart', 'deployment/storefront', 'deployment/orders-api', '--namespace', 'orders')
    Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'status', 'deployment/storefront', '--namespace', 'orders', '--timeout', '5m')
    Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'status', 'deployment/orders-api', '--namespace', 'orders', '--timeout', '5m')
    Write-Host 'Baseline restored and rollouts are available.'
    exit 0
}

switch ($Scenario) {
    'imagepull' {
        Invoke-Checked kubectl @('--context', $expectedContext, 'set', 'image', 'deployment/storefront', 'storefront=invalid.example/aks-labs/storefront:missing', '--namespace', 'orders')
    }
    'readiness' {
        Invoke-Checked kubectl @('--context', $expectedContext, 'set', 'env', 'deployment/orders-api', 'FAIL_READINESS=true', '--namespace', 'orders')
    }
    'oom' {
        Invoke-Checked kubectl @('--context', $expectedContext, 'set', 'resources', 'deployment/orders-api', '--limits=cpu=500m,memory=16Mi', '--requests=cpu=100m,memory=16Mi', '--namespace', 'orders')
    }
    'scheduling' {
        $patch = '{"spec":{"template":{"spec":{"nodeSelector":{"aks-course/impossible":"true"}}}}}'
        Invoke-Checked kubectl @('--context', $expectedContext, 'patch', 'deployment', 'storefront', '--namespace', 'orders', '--type', 'merge', '--patch', $patch)
    }
    'dns' {
        Invoke-Checked kubectl @('--context', $expectedContext, 'patch', 'configmap', 'orders-config', '--namespace', 'orders', '--type', 'merge', '--patch', '{"data":{"ORDERS_API_URL":"http://orders-api-wrong:8080"}}')
        Invoke-Checked kubectl @('--context', $expectedContext, 'rollout', 'restart', 'deployment/storefront', '--namespace', 'orders')
    }
    'network' {
        Invoke-Checked kubectl @('--context', $expectedContext, 'delete', 'networkpolicy', 'allow-storefront-to-api', '--namespace', 'orders', '--ignore-not-found')
    }
    'rollout' {
        $patch = '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/wrong"}]'
        Invoke-Checked kubectl @('--context', $expectedContext, 'patch', 'deployment', 'storefront', '--namespace', 'orders', '--type', 'json', '--patch', $patch)
    }
}

Write-Host "Injected '$Scenario'. Do not restore until evidence has been collected."
