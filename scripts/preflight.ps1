[CmdletBinding()]
param(
    [switch]$LocalOnly,
    [switch]$CloudOnly,
    [switch]$FixProviders
)

. (Join-Path $PSScriptRoot 'common.ps1')

$checks = [System.Collections.Generic.List[object]]::new()
function Add-Check {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $checks.Add([pscustomobject]@{ Name = $Name; Passed = $Passed; Detail = $Detail })
    if (-not $Passed) {
        Write-Warning "$Name - $Detail"
    } else {
        Write-Host "[pass] $Name - $Detail"
    }
}

$requiredCommands = if ($CloudOnly) {
    @('az', 'kubectl', 'kubelogin', 'pwsh')
} else {
    @('az', 'docker', 'flux', 'helm', 'kind', 'kubeconform', 'kubectl', 'kubelogin', 'kustomize', 'python', 'pwsh')
}
foreach ($command in $requiredCommands) {
    Add-Check "tool:$command" ([bool](Get-Command $command -ErrorAction SilentlyContinue)) 'available on PATH'
}

if (-not $CloudOnly -and (Get-Command docker -ErrorAction SilentlyContinue)) {
    & docker info --format '{{.ServerVersion}}' *> $null
    Add-Check 'docker-engine' ($LASTEXITCODE -eq 0) 'Docker daemon is reachable'
}

if ($LocalOnly) {
    if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
        throw 'Local preflight failed. Rebuild the Dev Container or install missing tools.'
    }
    Write-Host 'Local preflight passed.'
    exit 0
}

$config = Get-LabConfiguration

$accountJson = & az account show --output json --only-show-errors 2>$null
Add-Check 'azure-login' ($LASTEXITCODE -eq 0 -and $accountJson) 'Azure CLI has an active account'
if (-not $accountJson) {
    throw 'Run az login, select the intended lab subscription, and rerun preflight.'
}

$account = $accountJson | ConvertFrom-Json
Add-Check 'subscription-state' ($account.state -eq 'Enabled') "active subscription '$($account.name)' is enabled"

$permissionJson = & az rest `
    --method get `
    --url "https://management.azure.com/subscriptions/$($account.id)/providers/Microsoft.Authorization/permissions?api-version=2022-04-01" `
    --output json `
    --only-show-errors 2>$null
$canAssignRoles = $false
if ($LASTEXITCODE -eq 0 -and $permissionJson) {
    $permissionSets = @(($permissionJson | ConvertFrom-Json).value)
    $canAssignRoles = @(
        $permissionSets | Where-Object {
            (@($_.actions) -contains '*' -or @($_.actions) -contains 'Microsoft.Authorization/*') -and
            @($_.notActions) -notcontains 'Microsoft.Authorization/roleAssignments/write'
        }
    ).Count -gt 0
}
Add-Check 'subscription-owner-capability' $canAssignRoles 'can create scoped role assignments required by the labs'

$requiredProviders = @(
    'Microsoft.Authorization',
    'Microsoft.ContainerRegistry',
    'Microsoft.ContainerService',
    'Microsoft.Compute',
    'Microsoft.Consumption',
    'Microsoft.Insights',
    'Microsoft.KeyVault',
    'Microsoft.KubernetesConfiguration',
    'Microsoft.ManagedIdentity',
    'Microsoft.Monitor',
    'Microsoft.Network',
    'Microsoft.OperationalInsights'
)

foreach ($provider in $requiredProviders) {
    $state = (& az provider show --namespace $provider --query registrationState --output tsv --only-show-errors 2>$null)
    if ($state -ne 'Registered' -and $FixProviders) {
        Invoke-Checked az @('provider', 'register', '--namespace', $provider, '--wait', '--only-show-errors')
        $state = 'Registered'
    }
    Add-Check "provider:$provider" ($state -eq 'Registered') $state
}

$skuJson = & az vm list-skus `
    --location $config.Location `
    --resource-type virtualMachines `
    --size $config.NodeVmSize `
    --all `
    --output json `
    --only-show-errors 2>$null
$skuAvailable = $false
$sku = @()
$skuVcpus = 0
$ephemeralOsSupported = $false
if ($LASTEXITCODE -eq 0 -and $skuJson) {
    $sku = @($skuJson | ConvertFrom-Json)
    if ($sku.Count -gt 0) {
        $vcpuCapability = @($sku[0].capabilities | Where-Object name -eq 'vCPUs') | Select-Object -First 1
        if ($vcpuCapability) { $skuVcpus = [int]$vcpuCapability.value }
        $ephemeralCapability = @($sku[0].capabilities | Where-Object name -eq 'EphemeralOSDiskSupported') | Select-Object -First 1
        $ephemeralOsSupported = $ephemeralCapability -and $ephemeralCapability.value -eq 'True'
    }
    $skuAvailable = (
        $sku.Count -gt 0 -and
        @($sku[0].restrictions).Count -eq 0 -and
        $skuVcpus -ge 4 -and
        $ephemeralOsSupported
    )
}
Add-Check 'vm-sku' $skuAvailable "$($config.NodeVmSize) is available with $skuVcpus vCPUs and ephemeral OS support in $($config.Location)"

& az aks get-versions --location $config.Location --output none --only-show-errors 2>$null
Add-Check 'aks-region' ($LASTEXITCODE -eq 0) "AKS versions are available in $($config.Location)"

if ($skuAvailable) {
    $family = $sku[0].family
    $usageJson = & az vm list-usage `
        --location $config.Location `
        --query "[?name.value=='$family' || name.value=='cores']" `
        --output json `
        --only-show-errors 2>$null
    $usage = @()
    if ($LASTEXITCODE -eq 0 -and $usageJson) {
        $usage = @($usageJson | ConvertFrom-Json)
    }
    foreach ($quota in @($family, 'cores')) {
        $entry = @($usage | Where-Object { $_.name.value -eq $quota }) | Select-Object -First 1
        $headroom = if ($entry) { [int]$entry.limit - [int]$entry.currentValue } else { -1 }
        Add-Check "quota:$quota" ($headroom -ge 12) "$headroom vCPUs available; 12 required for scaling labs"
    }
}

$resultsPath = Join-Path (New-EvidenceDirectory) 'preflight.json'
$checks | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $resultsPath

if ($checks.Where({ -not $_.Passed }).Count -gt 0) {
    throw "Preflight failed. See $resultsPath."
}

Write-Host "Preflight passed. Results: $resultsPath"
