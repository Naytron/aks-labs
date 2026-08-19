[CmdletBinding()]
param(
    [string[]]$CandidateRegions = @('eastus2', 'centralus', 'westus2', 'westus3'),
    [string[]]$CandidateSkus = @('Standard_D4ds_v6', 'Standard_D4ds_v7', 'Standard_D4ads_v7', 'Standard_D4s_v6'),
    [switch]$FixProvider
)

. (Join-Path $PSScriptRoot 'common.ps1')

Assert-Command az
$account = & az account show --query name --output tsv --only-show-errors 2>$null
if ($LASTEXITCODE -ne 0 -or -not $account) {
    throw 'Run az login and select the intended lab subscription first.'
}

$computeState = (& az provider show --namespace Microsoft.Compute --query registrationState --output tsv --only-show-errors 2>$null)
if ($computeState -ne 'Registered' -and $FixProvider) {
    Invoke-Checked az @('provider', 'register', '--namespace', 'Microsoft.Compute', '--wait', '--only-show-errors')
    $computeState = 'Registered'
}
if ($computeState -ne 'Registered') {
    throw 'Microsoft.Compute is not registered. Rerun with -FixProvider.'
}

$results = foreach ($region in $CandidateRegions) {
    Write-Host "Checking $region..." -ForegroundColor DarkGray
    $skuQuery = '[?' + (($CandidateSkus | ForEach-Object { "name=='$_'" }) -join ' || ') + ']'
    $skuJson = & az vm list-skus `
        --location $region `
        --resource-type virtualMachines `
        --all `
        --query $skuQuery `
        --output json `
        --only-show-errors 2>$null
    $availableSkus = if ($LASTEXITCODE -eq 0 -and $skuJson) { @($skuJson | ConvertFrom-Json) } else { @() }
    $sku = $null
    foreach ($candidateSku in $CandidateSkus) {
        $candidate = @($availableSkus | Where-Object name -eq $candidateSku) | Select-Object -First 1
        if (-not $candidate) { continue }
        $candidateVcpus = @($candidate.capabilities | Where-Object name -eq 'vCPUs') | Select-Object -First 1
        $candidateEphemeral = @($candidate.capabilities | Where-Object name -eq 'EphemeralOSDiskSupported') | Select-Object -First 1
        if (
            $candidate -and
            @($candidate.restrictions).Count -eq 0 -and
            [int]$candidateVcpus.value -ge 4 -and
            $candidateEphemeral.value -eq 'True'
        ) {
            $sku = $candidate
            break
        }
    }
    $unrestricted = [bool]$sku
    $zones = if ($sku) {
        @($sku.locationInfo | ForEach-Object { $_.zones } | Sort-Object -Unique) -join ','
    } else {
        ''
    }
    $familyHeadroom = -1
    $regionalHeadroom = -1
    if ($unrestricted) {
        $usageJson = & az vm list-usage --location $region --output json --only-show-errors 2>$null
        $usage = if ($LASTEXITCODE -eq 0 -and $usageJson) { @($usageJson | ConvertFrom-Json) } else { @() }
        $familyEntry = @($usage | Where-Object { $_.name.value -eq $sku.family }) | Select-Object -First 1
        $regionalEntry = @($usage | Where-Object { $_.name.value -eq 'cores' }) | Select-Object -First 1
        if ($familyEntry) { $familyHeadroom = [int]$familyEntry.limit - [int]$familyEntry.currentValue }
        if ($regionalEntry) { $regionalHeadroom = [int]$regionalEntry.limit - [int]$regionalEntry.currentValue }
    }
    [pscustomobject]@{
        Region = $region
        VmSize = if ($sku) { $sku.name } else { '' }
        Zones = $zones
        SkuUnrestricted = [bool]$unrestricted
        FamilyVcpuHeadroom = $familyHeadroom
        RegionalVcpuHeadroom = $regionalHeadroom
        Ready = [bool]($unrestricted -and $zones -and $familyHeadroom -ge 12 -and $regionalHeadroom -ge 12)
    }
}

$results | Format-Table -AutoSize
$ready = @($results | Where-Object Ready)
if ($ready.Count -eq 0) {
    throw 'No candidate region met the course SKU, zone, and 12-vCPU headroom requirements. Check quota or pass other candidate regions.'
}
Write-Host "Recommended available region: $($ready[0].Region)"
Write-Host "Recommended available VM size: $($ready[0].VmSize)"
