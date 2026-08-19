[CmdletBinding()]
param(
    [string]$Incident = 'manual',
    [Parameter(Mandatory)]
    [ValidateSet('kind', 'automatic', 'standard')]
    [string]$Environment
)

. (Join-Path $PSScriptRoot 'common.ps1')

$evidenceDirectory = New-EvidenceDirectory
$timestamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$path = Join-Path $evidenceDirectory "incident-$Incident-$timestamp.txt"
$context = if ($Environment -eq 'kind') {
    'kind-aks-labs'
} else {
    (Get-DeploymentOutputs -Environment $Environment).clusterName
}
$currentContext = (& kubectl config current-context 2>$null)
if ($LASTEXITCODE -ne 0 -or $currentContext -ne $context) {
    throw "Refusing evidence collection: context '$currentContext' is not '$context'."
}

$sections = [ordered]@{
    'context' = { kubectl config current-context }
    'nodes' = { kubectl --context $context get nodes -o wide }
    'workloads' = { kubectl --context $context get all,pvc,pdb,networkpolicy -n orders -o wide }
    'events' = { kubectl --context $context get events -n orders --sort-by=.lastTimestamp }
    'deployments' = { kubectl --context $context describe deployment storefront orders-api -n orders }
    'pods' = { kubectl --context $context describe pods -n orders }
    'logs-storefront' = { kubectl --context $context logs -n orders deployment/storefront --all-containers --tail=200 }
    'logs-orders-api' = { kubectl --context $context logs -n orders deployment/orders-api --all-containers --tail=200 }
}

foreach ($section in $sections.GetEnumerator()) {
    "===== $($section.Key) =====" | Add-Content -LiteralPath $path
    try {
        & $section.Value 2>&1 | Add-Content -LiteralPath $path
    } catch {
        "collection failed: $($_.Exception.Message)" | Add-Content -LiteralPath $path
    }
}

$content = Get-Content -LiteralPath $path -Raw
$content = $content `
    -replace '(?i)(subscription|tenant)[- ]?id[=: ]+[0-9a-f-]{36}', '$1-id=<redacted>' `
    -replace '(?i)(token|password|secret)[=: ]+\S+', '$1=<redacted>'
$content | Set-Content -LiteralPath $path
Write-Host "Evidence collected at $path. Review it before sharing."
