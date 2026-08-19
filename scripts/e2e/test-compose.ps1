[CmdletBinding()]
param()

. (Join-Path (Split-Path -Parent $PSScriptRoot) 'common.ps1')

$root = Get-RepoRoot
$composeFile = Join-Path $root 'app/compose.yaml'
try {
    Invoke-Checked docker @('compose', '-f', $composeFile, 'up', '--build', '--detach', '--wait')
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/healthz' -TimeoutSec 5
    if ($health.status -ne 'alive') { throw 'Storefront health endpoint did not report alive.' }
    $order = Invoke-RestMethod `
        -Uri 'http://127.0.0.1:8080/api/orders' `
        -Method Post `
        -ContentType 'application/json' `
        -Body '{"item":"e2e-compose","quantity":2}' `
        -TimeoutSec 10
    Invoke-Checked docker @('compose', '-f', $composeFile, 'restart', 'orders-api')
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
        throw 'Order did not persist across orders-api restart.'
    }
    foreach ($image in @('app-orders-api:latest', 'app-storefront:latest')) {
        $metadata = Invoke-Checked docker @('image', 'inspect', $image, '--format', '{{.Config.User}}|{{json .Config.Healthcheck}}') -Capture
        if (($metadata -join '') -notmatch '^10001:10001\|\{"Test"') {
            throw "$image does not expose the expected non-root user and health check."
        }
    }
} finally {
    & docker compose -f $composeFile down --volumes --remove-orphans 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose cleanup failed.' }
    $remainingContainers = @(& docker compose -f $composeFile ps --all --quiet 2>$null | Where-Object { $_ })
    if ($remainingContainers.Count -ne 0) {
        throw "$($remainingContainers.Count) Compose container(s) remain after cleanup."
    }
    & docker volume inspect app_orders-data 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { throw 'Compose orders-data volume remains after cleanup.' }
}
