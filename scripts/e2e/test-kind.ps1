[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ArtifactDirectory
)

. (Join-Path (Split-Path -Parent $PSScriptRoot) 'common.ps1')

$root = Get-RepoRoot
$kindName = 'aks-labs'
$evidenceRoot = Join-Path $root 'evidence'
$evidenceBefore = @(
    Get-ChildItem -Path $evidenceRoot -Filter 'incident-e2e-*' -File -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName
)
try {
    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/new-kind-lab.ps1'),
        '-Recreate',
        '-Starter'
    )
    $starter = Invoke-Checked kubectl @(
        '--context', 'kind-aks-labs',
        'get', 'deployment/orders-api',
        '--namespace', 'orders',
        '--output', 'json'
    ) -Capture | ConvertFrom-Json
    $starterContainer = $starter.spec.template.spec.containers[0]
    $starterProperties = @($starterContainer.PSObject.Properties | ForEach-Object Name)
    $hasReadiness = $starterProperties -contains 'readinessProbe'
    $hasRequests = (
        $starterProperties -contains 'resources' -and
        $starterContainer.resources -and
        @($starterContainer.resources.PSObject.Properties | ForEach-Object Name) -contains 'requests'
    )
    if ($hasReadiness -or $hasRequests) {
        throw 'Day 1 starter unexpectedly contains completed probe/resource configuration.'
    }

    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/deploy-workload.ps1'),
        '-Target', 'kind'
    )
    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/validate-lab.ps1'),
        '-Gate', 'Prework'
    )

    $order = Invoke-RestMethod `
        -Uri 'http://127.0.0.1:8080/api/orders' `
        -Method Post `
        -ContentType 'application/json' `
        -Body '{"item":"e2e-kind","quantity":3}' `
        -TimeoutSec 10
    $pod = Invoke-Checked kubectl @(
        '--context', 'kind-aks-labs',
        'get', 'pod',
        '--namespace', 'orders',
        '--selector', 'app.kubernetes.io/name=orders-api',
        '--output', 'jsonpath={.items[0].metadata.name}'
    ) -Capture
    Invoke-Checked kubectl @('--context', 'kind-aks-labs', 'delete', 'pod', ($pod | Select-Object -First 1), '--namespace', 'orders', '--wait=true')
    Invoke-Checked kubectl @('--context', 'kind-aks-labs', 'rollout', 'status', 'deployment/orders-api', '--namespace', 'orders', '--timeout=3m')
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $orders = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/api/orders' -TimeoutSec 3
            if (@($orders.id) -contains $order.id) { break }
        } catch {
            if ($attempt -eq 29) { throw }
        }
        Start-Sleep -Seconds 1
    }
    if (@($orders.id) -notcontains $order.id) {
        throw 'Order did not persist across API pod replacement.'
    }

    foreach ($scenario in @('imagepull', 'readiness', 'scheduling')) {
        Invoke-Checked pwsh @(
            '-NoProfile',
            '-File', (Join-Path $root 'scripts/inject-failure.ps1'),
            '-Scenario', $scenario,
            '-Environment', 'kind'
        )
        Invoke-Checked pwsh @(
            '-NoProfile',
            '-File', (Join-Path $root 'scripts/collect-evidence.ps1'),
            '-Incident', "e2e-$scenario",
            '-Environment', 'kind'
        )
        Invoke-Checked pwsh @(
            '-NoProfile',
            '-File', (Join-Path $root 'scripts/inject-failure.ps1'),
            '-Scenario', $scenario,
            '-Environment', 'kind',
            '-Restore'
        )
    }
    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/validate-lab.ps1'),
        '-Environment', 'kind',
        '-Check', 'Workload'
    )

    New-Item -ItemType Directory -Path $ArtifactDirectory -Force | Out-Null
    Get-ChildItem -Path $evidenceRoot -Filter 'incident-e2e-*' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notin $evidenceBefore } |
        Copy-Item -Destination $ArtifactDirectory -Force
} finally {
    & kind delete cluster --name $kindName 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'kind cleanup command failed.' }
    if ((& kind get clusters 2>$null) -contains $kindName) {
        throw 'kind cluster remained after cleanup.'
    }
}
