Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:RepoRoot = Split-Path -Parent $PSScriptRoot

function Get-RepoRoot {
    return $script:RepoRoot
}

function Import-LabEnvironment {
    param(
        [switch]$Optional
    )

    $path = Join-Path $script:RepoRoot '.env'
    if (-not (Test-Path -LiteralPath $path)) {
        if ($Optional) {
            return
        }
        throw "Missing .env. Copy .env.example to .env and set the lab values."
    }

    foreach ($line in Get-Content -LiteralPath $path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        if ($trimmed -notmatch '^([A-Z][A-Z0-9_]*)=(.*)$') {
            throw "Invalid .env entry: $trimmed"
        }
        $name = $Matches[1]
        $value = $Matches[2].Trim().Trim('"').Trim("'")
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Get-LabConfiguration {
    param(
        [switch]$AllowExpired
    )

    Import-LabEnvironment

    $prefix = $env:LAB_PREFIX
    if ($prefix -notmatch '^[a-z0-9]{3,8}$' -or $prefix -in @('replace', 'example', 'default')) {
        throw 'LAB_PREFIX must contain 3-8 lowercase letters or digits.'
    }

    $location = $env:AZURE_LOCATION
    if ($location -notmatch '^[a-z0-9]+$' -or $location -in @('replace', 'default')) {
        throw 'AZURE_LOCATION must be a concrete Azure region name such as westus2.'
    }

    $nodeVmSize = $env:AKS_NODE_VM_SIZE
    if ($nodeVmSize -notmatch '^Standard_D[0-9]+[A-Za-z0-9_]*$' -or $nodeVmSize -in @('replace', 'default')) {
        throw 'AKS_NODE_VM_SIZE must be a concrete four-vCPU-or-larger D-series SKU.'
    }

    $expiration = $env:LAB_EXPIRATION
    $expirationDate = [DateTime]::MinValue
    if (-not [DateTime]::TryParseExact(
        $expiration,
        'yyyy-MM-dd',
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::None,
        [ref]$expirationDate
    )) {
        throw 'LAB_EXPIRATION must use yyyy-MM-dd.'
    }
    if (-not $AllowExpired -and $expirationDate.Date -lt [DateTime]::UtcNow.Date) {
        throw 'LAB_EXPIRATION cannot be in the past.'
    }

    $budget = 0
    if (-not [int]::TryParse($env:LAB_BUDGET_USD, [ref]$budget) -or $budget -lt 20 -or $budget -gt 500) {
        throw 'LAB_BUDGET_USD must be an integer from 20 through 500.'
    }

    $authorizedRanges = @()
    if ($env:API_SERVER_AUTHORIZED_IP_RANGES) {
        $authorizedRanges = @(
            $env:API_SERVER_AUTHORIZED_IP_RANGES.Split(
                ',',
                [StringSplitOptions]::RemoveEmptyEntries
            ) | ForEach-Object { $_.Trim() }
        )
    }

    return [pscustomobject]@{
        Prefix = $prefix
        Location = $location
        NodeVmSize = $nodeVmSize
        Expiration = $expiration
        Budget = $budget
        AuthorizedIpRanges = $authorizedRanges
        StandardResourceGroup = "rg-$prefix-aks-labs"
        AutomaticResourceGroup = "rg-$prefix-automatic"
        StandardCluster = "aks-$prefix-standard"
        AutomaticCluster = "aks-$prefix-automatic"
    }
}

function Assert-Command {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not on PATH."
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)]
        [string]$Command,
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [switch]$Capture
    )

    if ($Capture) {
        $output = & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$Command failed with exit code $LASTEXITCODE."
        }
        return $output
    }

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

function Get-DeploymentOutputs {
    param(
        [ValidateSet('automatic', 'standard')]
        [string]$Environment
    )

    $path = Join-Path $script:RepoRoot ".aks-labs/$Environment-outputs.json"
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Deployment outputs not found at $path. Deploy $Environment first."
    }
    return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

function Assert-CourseResourceGroup {
    param(
        [Parameter(Mandatory)]
        [string]$Name
    )

    $tags = Invoke-Checked az @(
        'group', 'show',
        '--name', $Name,
        '--query', 'tags',
        '--output', 'json',
        '--only-show-errors'
    ) -Capture | ConvertFrom-Json

    if ($tags.'aks-course' -ne 'level400' -or $tags.environment -ne 'lab') {
        throw "Refusing to modify '$Name' because required course tags are absent."
    }
}

function New-EvidenceDirectory {
    $path = Join-Path $script:RepoRoot 'evidence'
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    return $path
}
