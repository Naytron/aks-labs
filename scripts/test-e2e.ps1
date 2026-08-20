[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$LocalOnly,
    [switch]$LiveAzure,
    [switch]$AcknowledgeAzureCharges,
    [ValidateRange(20, 50)]
    [decimal]$MaxBudgetUsd = 50,
    [ValidatePattern('^$|^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl = '',
    [string]$Branch = 'main',
    [string]$PlatformGroupObjectId = '',
    [string]$ApplicationGroupObjectId = '',
    [switch]$ArcExtension,
    [ValidatePattern('^$|^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$ArcRepositoryUrl = '',
    [ValidatePattern('^$|^[0-9]+$')]
    [string]$ArcGitHubAppId = '',
    [ValidatePattern('^$|^[0-9]+$')]
    [string]$ArcGitHubAppInstallationId = '',
    [string]$ArcGitHubAppPrivateKeyPath = '',
    [ValidateRange(2, 5)]
    [int]$ArcMaxRunners = 3,
    [ValidatePattern('^[A-Za-z0-9_.-]+\.ya?ml$')]
    [string]$ArcWorkflowFile = 'arc-scale-test.yml',
    [string]$ArcBranch = 'main',
    [switch]$SkipAutomatic,
    [switch]$SkipLocal,
    [switch]$KeepResourcesOnFailure,
    [switch]$SkipDevContainerBuild,
    [Parameter(DontShow)]
    [switch]$ChildLocal,
    [Parameter(DontShow)]
    [string]$RunId,
    [Parameter(DontShow)]
    [string]$ArtifactRelative
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'e2e/common.ps1')
. (Join-Path $PSScriptRoot 'common.ps1')
. (Join-Path $PSScriptRoot 'arc-common.ps1')

if ($LocalOnly -and $LiveAzure) {
    throw '-LocalOnly and -LiveAzure cannot be combined.'
}
if ($LiveAzure -and -not $AcknowledgeAzureCharges) {
    throw '-LiveAzure requires -AcknowledgeAzureCharges.'
}
if ($LiveAzure -and -not $PSCmdlet.ShouldProcess('tagged AKS course resources', "Run live Azure E2E with a USD $MaxBudgetUsd cap")) {
    return
}

if (-not $RunId) {
    $RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
}
if (-not $ArtifactRelative) {
    $ArtifactRelative = "artifacts/e2e/$RunId"
}
$artifactDirectory = Join-Path $repoRoot $ArtifactRelative
$stateDirectory = Join-Path $repoRoot '.aks-labs'
$evidenceDirectory = Join-Path $repoRoot 'evidence'
if (-not $ChildLocal -and ((Test-Path -LiteralPath $stateDirectory) -or (Test-Path -LiteralPath $evidenceDirectory))) {
    throw 'E2E requires .aks-labs and evidence to be absent so generated-state ownership is unambiguous.'
}
Initialize-E2ERun -ArtifactDirectory $artifactDirectory
$stateExistedBefore = Test-Path -LiteralPath $stateDirectory
$evidenceExistedBefore = Test-Path -LiteralPath $evidenceDirectory

function Remove-E2EGeneratedState {
    if (-not $stateExistedBefore -and (Test-Path -LiteralPath $stateDirectory)) {
        Remove-Item -LiteralPath $stateDirectory -Recurse -Force
    }
    if (-not $evidenceExistedBefore -and (Test-Path -LiteralPath $evidenceDirectory)) {
        Remove-Item -LiteralPath $evidenceDirectory -Recurse -Force
    }
}

function Invoke-LocalE2EPhases {
    Invoke-E2EStep `
        -Phase '02' `
        -Name 'Static and content QA' `
        -Expected 'All scripts, tests, Bicep, manifests, links, and course contracts pass.' `
        -ContinueOnError `
        -Action {
            Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/test-static.ps1'))
            Invoke-Checked python @((Join-Path $repoRoot 'tests/check_external_links.py'))
        }

    Invoke-E2EStep `
        -Phase '03' `
        -Name 'Docker Compose transaction and persistence' `
        -Expected 'Both hardened images run, an order survives API restart, and Compose cleans up.' `
        -ContinueOnError `
        -Action {
            Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/e2e/test-compose.ps1'))
        }

    Invoke-E2EStep `
        -Phase '04' `
        -Name 'kind learner path and incidents' `
        -Expected 'Starter promotes to full workload; persistence, gates, three isolated incidents, and cleanup pass.' `
        -ContinueOnError `
        -Action {
            Invoke-Checked pwsh @(
                '-NoProfile',
                '-File', (Join-Path $repoRoot 'scripts/e2e/test-kind.ps1'),
                '-ArtifactDirectory', $artifactDirectory
            )
        }
}

function Remove-E2EDevContainer {
    param([string[]]$ContainerIds)

    foreach ($containerId in @($ContainerIds | Where-Object { $_ })) {
        $volumeNames = @(
            Invoke-Checked docker @('inspect', $containerId, '--format', '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}{{"\n"}}{{end}}') -Capture |
                Where-Object { $_ }
        )
        Invoke-Checked docker @('rm', '--force', $containerId) | Out-Null
        foreach ($volume in $volumeNames) {
            Invoke-Checked docker @('volume', 'rm', $volume) | Out-Null
        }
        & docker inspect $containerId 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { throw "Dev Container $containerId remains after cleanup." }
    }
}

function Invoke-AzureNoWritePhase {
    if ($LocalOnly) {
        Add-E2ENonRunResult `
            -Phase '05' `
            -Name 'Azure no-write validation' `
            -Status SKIPPED `
            -Observed 'Skipped by -LocalOnly.' `
            -Critical $false
        return $true
    }
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.env'))) {
        Add-E2ENonRunResult `
            -Phase '05' `
            -Name 'Azure no-write validation' `
            -Status BLOCKED `
            -Expected 'Azure login and concrete non-secret .env values.' `
            -Observed '.env is absent.' `
            -Remediation 'Copy .env.example to .env, select the dedicated lab subscription, and resolve region/SKU.' `
            -Critical $true
        return $false
    }
    & az account show --output none --only-show-errors 2>$null
    if ($LASTEXITCODE -ne 0) {
        Add-E2ENonRunResult `
            -Phase '05' `
            -Name 'Azure no-write validation' `
            -Status BLOCKED `
            -Expected 'Authenticated Azure CLI in the current execution environment.' `
            -Observed 'Azure CLI is not authenticated.' `
            -Remediation 'Run az login in this Dev Container or shell.' `
            -Critical $true
        return $false
    }

    $passed = Invoke-E2EStep `
        -Phase '05' `
        -Name 'Azure preflight, validate, and what-if' `
        -Expected 'Capacity and permissions pass; Automatic/Standard validate and what-if create no resources.' `
        -ErrorStatus BLOCKED `
        -PassThru `
        -Remediation 'Resolve subscription permissions, provider registration, quota, region, SKU, or policy before live testing.' `
        -ContinueOnError `
        -Action {
            Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/e2e/test-azure-nowrite.ps1'))
        }
    return [bool]$passed
}

function Invoke-ArcPrerequisitePhase {
    if (-not $ArcExtension) {
        Add-E2ENonRunResult `
            -Phase '05A' `
            -Name 'Optional ARC prerequisites' `
            -Status SKIPPED `
            -Observed 'Optional post-capstone ARC extension was not requested.' `
            -Critical $false
        return $true
    }
    if (-not $LiveAzure) {
        Add-E2ENonRunResult `
            -Phase '05A' `
            -Name 'Optional ARC prerequisites' `
            -Status BLOCKED `
            -Expected 'Explicit live Azure mode for the paid runner node-pool exercise.' `
            -Observed '-ArcExtension was supplied without -LiveAzure.' `
            -Remediation 'Use the static module by default or add the live charge acknowledgement for an instructor pilot.' `
            -Critical $true
        return $false
    }

    $requiredValues = @{
        ArcRepositoryUrl = $ArcRepositoryUrl
        ArcGitHubAppId = $ArcGitHubAppId
        ArcGitHubAppInstallationId = $ArcGitHubAppInstallationId
        ArcGitHubAppPrivateKeyPath = $ArcGitHubAppPrivateKeyPath
    }
    $missing = @($requiredValues.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object Key)
    if ($missing.Count -gt 0) {
        Add-E2ENonRunResult `
            -Phase '05A' `
            -Name 'Optional ARC prerequisites' `
            -Status BLOCKED `
            -Expected 'Private sandbox URL, GitHub App IDs, and ignored/external private-key path.' `
            -Observed "Missing parameter(s): $($missing -join ', ')." `
            -Remediation 'Complete docs/instructor-arc-setup.md before requesting the live extension.' `
            -Critical $true
        return $false
    }

    $passed = Invoke-E2EStep `
        -Phase '05A' `
        -Name 'Optional ARC private-sandbox preflight' `
        -Expected 'Private repository, authenticated GitHub CLI, workflow, key file, and pinned chart render pass without writes.' `
        -ErrorStatus BLOCKED `
        -PassThru `
        -Remediation 'Fix repository visibility/App scope, GitHub authentication, ignored key path, workflow copy, or Helm 3/chart access.' `
        -ContinueOnError `
        -Action {
            $null = Assert-ArcPrivateKeyFile -Path $ArcGitHubAppPrivateKeyPath
            $slug = Assert-PrivateArcRepository -RepositoryUrl $ArcRepositoryUrl
            & gh workflow view $ArcWorkflowFile --repo $slug 1>$null 2>$null
            if ($LASTEXITCODE -ne 0) {
                throw "Private sandbox workflow '$ArcWorkflowFile' is missing."
            }
            Invoke-Checked pwsh @(
                '-NoProfile',
                '-File', (Join-Path $repoRoot 'scripts/deploy-arc.ps1'),
                '-RepositoryUrl', $ArcRepositoryUrl,
                '-MaxRunners', "$ArcMaxRunners",
                '-DryRun'
            )
        }
    return [bool]$passed
}

function Get-ConservativeHourlyEstimate {
    $config = Get-LabConfiguration
    $filter = [Uri]::EscapeDataString(
        "armSkuName eq '$($config.NodeVmSize)' and armRegionName eq '$($config.Location)' and priceType eq 'Consumption'"
    )
    $uri = "https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview&`$filter=$filter"
    $items = @(Invoke-RestMethod -Uri $uri -TimeoutSec 30).Items |
        Where-Object {
            $_.isPrimaryMeterRegion -and
            $_.productName -notmatch 'Windows' -and
            $_.meterName -notmatch 'Spot'
        }
    $vmRate = if ($items) { [decimal]($items | Sort-Object retailPrice | Select-Object -First 1).retailPrice } else { 1 }
    $maximumNodeCount = if ($ArcExtension) { 3 + $ArcMaxRunners } else { 3 }
    return [Math]::Max(2, [decimal]($maximumNodeCount * $vmRate + 0.5))
}

function Assert-LiveBudget {
    param(
        [Parameter(Mandatory)][datetime]$LiveStart,
        [Parameter(Mandatory)][decimal]$HourlyEstimate
    )
    $projected = [decimal](([DateTime]::UtcNow - $LiveStart).TotalHours * [double]$HourlyEstimate)
    if ($projected -ge $MaxBudgetUsd) {
        throw "Projected live E2E cost $([Math]::Round($projected, 2)) reached the USD $MaxBudgetUsd cap."
    }
}

function Get-CoursePostedCost {
    $subscriptionId = Invoke-Checked az @('account', 'show', '--query', 'id', '--output', 'tsv', '--only-show-errors') -Capture
    $subscriptionId = ($subscriptionId | Select-Object -First 1).Trim()
    $config = Get-LabConfiguration -AllowExpired
    $bodyPath = Join-Path $artifactDirectory 'cost-query.json'
    @{
        type = 'ActualCost'
        timeframe = 'MonthToDate'
        dataset = @{
            granularity = 'None'
            aggregation = @{
                totalCost = @{
                    name = 'PreTaxCost'
                    function = 'Sum'
                }
            }
            grouping = @(
                @{ type = 'Dimension'; name = 'ResourceGroupName' },
                @{ type = 'Dimension'; name = 'ServiceName' }
            )
            filter = @{
                dimensions = @{
                    name = 'ResourceGroupName'
                    operator = 'In'
                    values = @($config.AutomaticResourceGroup, $config.StandardResourceGroup)
                }
            }
        }
    } | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $bodyPath

    $response = Invoke-Checked az @(
        'rest',
        '--method', 'post',
        '--url', "https://management.azure.com/subscriptions/$subscriptionId/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
        '--headers', 'Content-Type=application/json', 'ClientType=GitHubCopilotForAzure',
        '--body', "@$bodyPath",
        '--output', 'json',
        '--only-show-errors'
    ) -Capture | ConvertFrom-Json
    $rows = @($response.properties.rows)
    $total = [decimal]0
    foreach ($row in $rows) { $total += [decimal]$row[0] }
    [pscustomobject]@{
        postedCostUsd = [Math]::Round($total, 4)
        rowCount = $rows.Count
        reconciliationPending = $rows.Count -eq 0
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $artifactDirectory 'cost-status.json')
    Write-Host "Posted QA resource-group cost: USD $([Math]::Round($total, 4)); rows=$($rows.Count); delayed reconciliation may remain."
}

function Invoke-LiveAzurePhases {
    if (-not $LiveAzure) {
        Add-E2ENonRunResult `
            -Phase '06-10' `
            -Name 'Live Azure bootcamp path' `
            -Status SKIPPED `
            -Observed 'Paid deployment requires explicit -LiveAzure and -AcknowledgeAzureCharges.' `
            -Critical $false
        return
    }

    $liveStart = [DateTime]::UtcNow
    $hourlyEstimate = Get-ConservativeHourlyEstimate
    $operationTimeoutMinutes = [Math]::Max(
        5,
        [Math]::Min(60, [Math]::Floor(([double]$MaxBudgetUsd / [double]$hourlyEstimate) * 60))
    )
    $automaticReady = $false
    $standardReady = $false
    $personasConfigured = $false
    $arcAttempted = $false
    try {
        if ($SkipAutomatic) {
            Add-E2ENonRunResult -Phase '06' -Name 'AKS Automatic' -Status SKIPPED -Observed 'Skipped by -SkipAutomatic.' -Critical $false
        } else {
            $automaticReady = Invoke-E2EStep `
                -Phase '06' `
                -Name 'AKS Automatic deploy and workload' `
                -Expected 'Automatic deploys, serves an external order, passes validation, and restores isolated incidents.' `
                -ErrorStatus BLOCKED `
                -Remediation 'Use the documented no-write instructor fallback and inspect AKS provider health/capacity.' `
                -PassThru `
                -ContinueOnError `
                -Action {
                    Assert-LiveBudget -LiveStart $liveStart -HourlyEstimate $hourlyEstimate
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-lab.ps1'), '-Environment', 'automatic', '-BudgetAmountOverride', "$MaxBudgetUsd", '-ProvisioningTimeoutMinutes', "$operationTimeoutMinutes")
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/build-images.ps1'), '-Target', 'acr', '-Environment', 'automatic')
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-workload.ps1'), '-Target', 'azure', '-Environment', 'automatic', '-Stage', 'day2')
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/validate-lab.ps1'), '-Environment', 'automatic', '-Check', 'All')
                    foreach ($scenario in @('imagepull', 'readiness')) {
                        Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/inject-failure.ps1'), '-Scenario', $scenario, '-Environment', 'automatic', '-Stage', 'day2')
                        Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/collect-evidence.ps1'), '-Incident', "e2e-automatic-$scenario", '-Environment', 'automatic')
                        Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/inject-failure.ps1'), '-Scenario', $scenario, '-Environment', 'automatic', '-Stage', 'day2', '-Restore')
                    }
                }
            Invoke-E2EStep `
                -Phase '06' `
                -Name 'AKS Automatic cleanup' `
                -Expected 'Automatic parent and managed node resource groups are absent.' `
                -Action {
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/cleanup-lab.ps1'), '-Mode', 'Automatic', '-Wait')
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/cleanup-lab.ps1'), '-Mode', 'Automatic', '-Wait')
                }
        }

        $standardReady = Invoke-E2EStep `
            -Phase '07' `
            -Name 'AKS Standard Day 2' `
            -Expected 'Standard deploys and Day 2 Gateway/network/persistence/scheduling checks pass.' `
            -ErrorStatus BLOCKED `
            -Remediation 'Resolve AKS provider health, policy, networking, quota, or regional capacity.' `
            -PassThru `
            -ContinueOnError `
            -Action {
                Assert-LiveBudget -LiveStart $liveStart -HourlyEstimate $hourlyEstimate
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-lab.ps1'), '-Environment', 'standard', '-BudgetAmountOverride', "$MaxBudgetUsd", '-ProvisioningTimeoutMinutes', "$operationTimeoutMinutes")
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/build-images.ps1'), '-Target', 'acr', '-Environment', 'standard')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-workload.ps1'), '-Target', 'azure', '-Environment', 'standard', '-Stage', 'day2')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/validate-lab.ps1'), '-Gate', 'Day2')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/cleanup-lab.ps1'), '-Mode', 'Daily')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/start-lab.ps1'), '-Environment', 'standard')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/validate-lab.ps1'), '-Gate', 'Day5')
            }

        if (-not $standardReady) {
            Add-E2ENonRunResult -Phase '08-10' -Name 'Days 3-5 live phases' -Status BLOCKED -Observed 'Standard cluster did not become ready.' -Remediation 'Repeat in a working dedicated AKS subscription.' -Critical $true
            if ($ArcExtension) {
                Add-E2ENonRunResult -Phase '10A' -Name 'Optional ARC live extension' -Status BLOCKED -Observed 'Standard cluster did not become ready.' -Remediation 'Run the extension only after the Standard and Day 5 gates pass.' -Critical $true
            }
            return
        }

        Invoke-E2EStep `
            -Phase '08' `
            -Name 'Day 3 identity and security' `
            -Expected 'Key Vault CSI, policy boundaries, and direct Day 3 workload pass.' `
            -ErrorStatus BLOCKED `
            -ContinueOnError `
            -Action {
                Assert-LiveBudget -LiveStart $liveStart -HourlyEstimate $hourlyEstimate
                $outputs = Get-DeploymentOutputs -Environment standard
                $secretPath = Join-Path $repoRoot '.aks-labs/e2e-course-api-key.txt'
                [guid]::NewGuid().ToString() | Set-Content -LiteralPath $secretPath -NoNewline
                try {
                    Invoke-Checked az @('keyvault', 'secret', 'set', '--vault-name', $outputs.keyVaultName, '--name', 'course-api-key', '--file', $secretPath, '--output', 'none', '--only-show-errors')
                } finally {
                    Remove-Item -LiteralPath $secretPath -Force -ErrorAction SilentlyContinue
                }
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-workload.ps1'), '-Target', 'azure', '-Environment', 'standard', '-Stage', 'day3')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/validate-lab.ps1'), '-Environment', 'standard', '-Check', 'Identity')
            }

        if ($RepositoryUrl) {
            Invoke-E2EStep `
                -Phase '08' `
                -Name 'Managed Flux reconciliation' `
                -Expected 'Public source and orders-workload become Ready with cluster-local substitutions.' `
                -ErrorStatus BLOCKED `
                -ContinueOnError `
                -Action {
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/bootstrap-gitops.ps1'), '-RepositoryUrl', $RepositoryUrl, '-Branch', $Branch, '-Stage', 'day3', '-Confirm:$false')
                }
        } else {
            Add-E2ENonRunResult -Phase '08' -Name 'Managed Flux reconciliation' -Status BLOCKED -Observed 'RepositoryUrl was not supplied.' -Remediation 'Publish/provide the public course repository.' -Critical $true
        }

        if ($PlatformGroupObjectId -and $ApplicationGroupObjectId) {
            $personasConfigured = Invoke-E2EStep `
                -Phase '08' `
                -Name 'Prepared Entra persona assignments' `
                -Expected 'Platform and application groups receive scoped course roles.' `
                -ErrorStatus BLOCKED `
                -PassThru `
                -ContinueOnError `
                -Action {
                    Invoke-Checked pwsh @(
                        '-NoProfile',
                        '-File', (Join-Path $repoRoot 'scripts/configure-personas.ps1'),
                        '-PlatformGroupObjectId', $PlatformGroupObjectId,
                        '-ApplicationGroupObjectId', $ApplicationGroupObjectId,
                        '-Confirm:$false'
                    )
                }
        } else {
            Add-E2ENonRunResult -Phase '08' -Name 'Real Entra persona test' -Status BLOCKED -Observed 'Prepared group object IDs were not supplied.' -Remediation 'Supply instructor-prepared disposable groups; impersonation is authorization-only.' -Critical $true
        }

        Invoke-E2EStep `
            -Phase '09' `
            -Name 'Day 4 operational core' `
            -Expected 'Day 4 stage, Prometheus query, bounded HPA, backup, and restore pass.' `
            -ErrorStatus BLOCKED `
            -ContinueOnError `
            -Action {
                Assert-LiveBudget -LiveStart $liveStart -HourlyEstimate $hourlyEstimate
                if ($RepositoryUrl) {
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/bootstrap-gitops.ps1'), '-RepositoryUrl', $RepositoryUrl, '-Branch', $Branch, '-Stage', 'day4', '-Confirm:$false')
                } else {
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/deploy-workload.ps1'), '-Target', 'azure', '-Environment', 'standard', '-Stage', 'day4')
                }
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/query-prometheus.ps1'))
                Invoke-Checked kubectl @('set', 'env', 'deployment/storefront', '-n', 'orders', 'CPU_BURN_MS=25')
                Invoke-Checked kubectl @('apply', '-f', (Join-Path $repoRoot 'platform/components/scaling/hpa.yaml'))
                $gateway = Invoke-Checked kubectl @('get', 'gateway', 'orders', '-n', 'orders', '-o', 'jsonpath={.status.addresses[0].value}') -Capture
                Invoke-Checked python @((Join-Path $repoRoot 'app/loadgen/load.py'), "http://$(($gateway | Select-Object -First 1).Trim())", '--requests', '500', '--concurrency', '25')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/backup-orders.ps1'), '-Mode', 'Backup')
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/backup-orders.ps1'), '-Mode', 'RestoreTest')
                Invoke-Checked kubectl @('set', 'env', 'deployment/storefront', '-n', 'orders', 'CPU_BURN_MS-')
            }

        Invoke-E2EStep `
            -Phase '10' `
            -Name 'Day 5 deterministic incidents' `
            -Expected 'Three isolated incidents collect evidence, restore, and return workload health.' `
            -ErrorStatus BLOCKED `
            -ContinueOnError `
            -Action {
                foreach ($scenario in @('dns', 'oom', 'rollout')) {
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/inject-failure.ps1'), '-Scenario', $scenario, '-Environment', 'standard', '-Stage', 'day4')
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/collect-evidence.ps1'), '-Incident', "e2e-day5-$scenario", '-Environment', 'standard')
                    Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/inject-failure.ps1'), '-Scenario', $scenario, '-Environment', 'standard', '-Stage', 'day4', '-Restore')
                }
                Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/validate-lab.ps1'), '-Environment', 'standard', '-Check', 'Workload')
            }

        if ($ArcExtension) {
            $arcAttempted = $true
            Invoke-E2EStep `
                -Phase '10A' `
                -Name 'Optional ARC runner and node autoscaling' `
                -Expected 'Pinned ARC installs, the private matrix workflow succeeds, runners are ephemeral, security gates pass, and runner nodes return to zero.' `
                -ErrorStatus BLOCKED `
                -ContinueOnError `
                -Remediation 'Inspect GitHub queue, controller/listener logs, runner custom resources, scheduler events, node-pool state, quota, and egress.' `
                -Action {
                    Assert-LiveBudget -LiveStart $liveStart -HourlyEstimate $hourlyEstimate
                    Invoke-Checked pwsh @(
                        '-NoProfile',
                        '-File', (Join-Path $repoRoot 'scripts/deploy-arc.ps1'),
                        '-RepositoryUrl', $ArcRepositoryUrl,
                        '-GitHubAppId', $ArcGitHubAppId,
                        '-GitHubAppInstallationId', $ArcGitHubAppInstallationId,
                        '-GitHubAppPrivateKeyPath', $ArcGitHubAppPrivateKeyPath,
                        '-MaxRunners', "$ArcMaxRunners",
                        '-Confirm:$false'
                    )
                    Invoke-Checked pwsh @(
                        '-NoProfile',
                        '-File', (Join-Path $repoRoot 'scripts/test-arc-scale.ps1'),
                        '-RepositoryUrl', $ArcRepositoryUrl,
                        '-WorkflowFile', $ArcWorkflowFile,
                        '-Ref', $ArcBranch,
                        '-NodeScaleDownTimeoutMinutes', '30'
                    )
                    Invoke-Checked pwsh @(
                        '-NoProfile',
                        '-File', (Join-Path $repoRoot 'scripts/validate-arc.ps1'),
                        '-Check', 'Security'
                    )
                }
        }
    } finally {
        if (-not $KeepResourcesOnFailure) {
            Invoke-E2EStep `
                -Phase '11' `
                -Name 'Final Azure cleanup' `
                -Expected 'Course resource groups and tagged resources are absent; repeat cleanup succeeds.' `
                -ErrorStatus FAIL `
                -ContinueOnError `
                -Action {
                    $cleanupErrors = [System.Collections.Generic.List[string]]::new()
                    if ($arcAttempted) {
                        try {
                            Invoke-Checked pwsh @(
                                '-NoProfile',
                                '-File', (Join-Path $repoRoot 'scripts/cleanup-arc.ps1'),
                                '-RepositoryUrl', $ArcRepositoryUrl,
                                '-Confirm:$false'
                            )
                        } catch {
                            $cleanupErrors.Add("ARC cleanup: $($_.Exception.Message)")
                        }
                    }
                    if ($personasConfigured) {
                        try {
                            Invoke-Checked pwsh @(
                                '-NoProfile',
                                '-File', (Join-Path $repoRoot 'scripts/configure-personas.ps1'),
                                '-PlatformGroupObjectId', $PlatformGroupObjectId,
                                '-ApplicationGroupObjectId', $ApplicationGroupObjectId,
                                '-Remove',
                                '-Confirm:$false'
                            )
                        } catch {
                            $cleanupErrors.Add("persona cleanup: $($_.Exception.Message)")
                        }
                    }
                    foreach ($mode in @('Automatic', 'Final')) {
                        try {
                            Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/cleanup-lab.ps1'), '-Mode', $mode, '-Wait', '-Confirm:$false')
                            Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $repoRoot 'scripts/cleanup-lab.ps1'), '-Mode', $mode, '-Wait', '-Confirm:$false')
                        } catch {
                            $cleanupErrors.Add("$mode cleanup: $($_.Exception.Message)")
                        }
                    }
                    try {
                        $remaining = @(Invoke-Checked az @('resource', 'list', '--tag', 'aks-course=level400', '--output', 'json', '--only-show-errors') -Capture | ConvertFrom-Json)
                        if ($remaining.Count -ne 0) { throw "$($remaining.Count) tagged Azure resources remain." }
                    } catch {
                        $cleanupErrors.Add("inventory verification: $($_.Exception.Message)")
                    }
                    try { Get-CoursePostedCost } catch { $cleanupErrors.Add("cost query: $($_.Exception.Message)") }
                    if ($cleanupErrors.Count -gt 0) {
                        throw ($cleanupErrors -join '; ')
                    }
                }
        } else {
            Add-E2ENonRunResult -Phase '11' -Name 'Final Azure cleanup' -Status BLOCKED -Observed 'Skipped by -KeepResourcesOnFailure.' -Remediation 'Delete all tagged course resources before release.' -Critical $true
        }
    }
}

if ($ChildLocal) {
    Invoke-LocalE2EPhases
    Remove-E2EGeneratedState
    $childResults = Join-Path $artifactDirectory 'results-child.json'
    $childSummary = Join-Path $artifactDirectory 'summary-child.md'
    $childOutcome = Complete-E2ERun -ResultsPath $childResults -SummaryPath $childSummary
    exit $(if ($childOutcome.Failures -gt 0) { 1 } elseif ($childOutcome.Blocks -gt 0) { 2 } else { 0 })
}

Invoke-E2EStep `
    -Phase '00' `
    -Name 'Repository safety contract' `
    -Expected 'Course contract tests and repository whitespace checks pass.' `
    -Action {
        Invoke-Checked python @('-m', 'unittest', 'discover', '-s', (Join-Path $repoRoot 'tests'), '-p', 'test_*.py')
        & git -C $repoRoot diff --check
        if ($LASTEXITCODE -ne 0) { throw 'git diff --check failed.' }
    }

$insideContainer = $IsLinux -and (Test-Path -LiteralPath '/.dockerenv')
if ($SkipLocal) {
    Add-E2ENonRunResult -Phase '01-04' -Name 'Local E2E phases' -Status SKIPPED -Observed 'Skipped by -SkipLocal.' -Critical $false
} elseif (-not $insideContainer -and -not $SkipDevContainerBuild -and (Get-Command devcontainer -ErrorAction SilentlyContinue)) {
    $existingBefore = @(docker ps -a --filter "label=devcontainer.local_folder=$($repoRoot.ToLowerInvariant())" --format '{{.ID}}')
    Invoke-E2EStep `
        -Phase '01' `
        -Name 'Full Dev Container and child local E2E' `
        -Expected 'Full image builds, post-create preflight passes, and child local E2E succeeds.' `
        -Action {
            Invoke-Checked devcontainer @('up', '--workspace-folder', $repoRoot, '--remove-existing-container')
            Invoke-Checked devcontainer @(
                'exec', '--workspace-folder', $repoRoot,
                'pwsh', '-NoLogo', '-NoProfile',
                '-File', './scripts/test-e2e.ps1',
                '-ChildLocal',
                '-LocalOnly',
                '-RunId', $RunId,
                '-ArtifactRelative', "$ArtifactRelative/child"
            )
        } `
        -ContinueOnError
    Import-E2EResults -Path (Join-Path $artifactDirectory 'child/results-child.json')
    $existingAfter = @(docker ps -a --filter "label=devcontainer.local_folder=$($repoRoot.ToLowerInvariant())" --format '{{.ID}}')
    Invoke-E2EStep `
        -Phase '01' `
        -Name 'Dev Container cleanup' `
        -Expected 'Every container and named volume created by this run is absent.' `
        -ContinueOnError `
        -Action {
            Remove-E2EDevContainer -ContainerIds @($existingAfter | Where-Object { $_ -notin $existingBefore })
        }
} else {
    if (-not $insideContainer) {
        Add-E2ENonRunResult -Phase '01' -Name 'Full Dev Container build' -Status SKIPPED -Observed 'Dev Container build skipped or CLI unavailable.' -Critical $false
    }
    Invoke-LocalE2EPhases
}

$azureNoWritePassed = Invoke-AzureNoWritePhase
$arcPrerequisitesPassed = Invoke-ArcPrerequisitePhase
if ($LiveAzure -and (-not $azureNoWritePassed -or ($ArcExtension -and -not $arcPrerequisitesPassed))) {
    Add-E2ENonRunResult `
        -Phase '06-10' `
        -Name 'Live Azure bootcamp path' `
        -Status BLOCKED `
        -Observed 'A critical Azure no-write or optional ARC prerequisite phase did not pass.' `
        -Remediation 'Resolve all requested no-write and private-sandbox gates before paid deployment.' `
        -Critical $true
} else {
    Invoke-LiveAzurePhases
}
Remove-E2EGeneratedState

$resultsPath = Join-Path $artifactDirectory 'results.json'
$summaryPath = Join-Path $artifactDirectory 'summary.md'
$outcome = Complete-E2ERun -ResultsPath $resultsPath -SummaryPath $summaryPath
Write-Host "E2E decision: $($outcome.Decision)"
Write-Host "Summary: $summaryPath"

if ($outcome.Failures -gt 0) { exit 1 }
if ($outcome.Blocks -gt 0) { exit 2 }
exit 0
