[CmdletBinding()]
param(
    [string]$Query = 'sum(rate(storefront_requests_total[5m]))'
)

. (Join-Path $PSScriptRoot 'common.ps1')

$outputs = Get-DeploymentOutputs -Environment standard
$endpoint = Invoke-Checked az @(
    'resource', 'show',
    '--ids', $outputs.azureMonitorWorkspaceResourceId,
    '--api-version', '2025-10-03',
    '--query', 'properties.metrics.prometheusQueryEndpoint',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
$endpoint = ($endpoint | Select-Object -First 1).Trim().TrimEnd('/')
if (-not $endpoint) {
    throw 'Azure Monitor workspace did not return a Prometheus query endpoint.'
}

$token = Invoke-Checked az @(
    'account', 'get-access-token',
    '--resource', 'https://prometheus.monitor.azure.com',
    '--query', 'accessToken',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
$token = ($token | Select-Object -First 1).Trim()
$encodedQuery = [Uri]::EscapeDataString($Query)
$response = Invoke-RestMethod `
    -Uri "$endpoint/api/v1/query?query=$encodedQuery" `
    -Headers @{ Authorization = "Bearer $token" } `
    -TimeoutSec 30

if ($response.status -ne 'success') {
    throw "Prometheus query failed with status '$($response.status)'."
}

$response.data.result | ConvertTo-Json -Depth 10
