<#
.SYNOPSIS
Validates installation, isolation, scale-to-zero, or cleanup for the ARC module.

.PARAMETER Check
Selects All, Install, Security, ScaleToZero, or Cleanup validation.

.PARAMETER RepositoryUrl
Optional private sandbox URL used to verify GitHub runner cleanup.

.PARAMETER NodeScaleDownTimeoutMinutes
Waits up to this many minutes for the runner node pool to return to zero.
#>
[CmdletBinding()]
param(
    [ValidateSet('All', 'Install', 'Security', 'ScaleToZero', 'Cleanup')]
    [string]$Check = 'All',
    [ValidatePattern('^$|^https://github\.com/[^/]+/[^/]+(?:\.git)?$')]
    [string]$RepositoryUrl = '',
    [ValidateRange(0, 30)]
    [int]$NodeScaleDownTimeoutMinutes = 0
)

. (Join-Path $PSScriptRoot 'arc-common.ps1')

Assert-Command az
Assert-Command kubectl
$context = Assert-ArcClusterContext
$helm = Get-ArcHelmCommand
$results = [System.Collections.Generic.List[object]]::new()
if (
    $Check -eq 'ScaleToZero' -and
    -not $PSBoundParameters.ContainsKey('NodeScaleDownTimeoutMinutes')
) {
    $NodeScaleDownTimeoutMinutes = 30
}

function Test-ArcCondition {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][bool]$Passed,
        [Parameter(Mandatory)][string]$Detail
    )
    $results.Add([pscustomobject]@{ Name = $Name; Passed = $Passed; Detail = $Detail })
    $mark = if ($Passed) { 'pass' } else { 'fail' }
    Write-Host "[$mark] $Name - $Detail"
}

function Get-ArcJson {
    param([string[]]$Arguments)
    $json = & kubectl @Arguments 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $json) {
        return $null
    }
    return $json | ConvertFrom-Json
}

function Get-ArcNodePool {
    $json = & az aks nodepool list `
        --resource-group $context.ResourceGroup `
        --cluster-name $context.ClusterName `
        --output json `
        --only-show-errors 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to list AKS node pools while validating ARC.'
    }
    if (-not $json) {
        return $null
    }
    return @($json | ConvertFrom-Json | Where-Object { $_.name -eq $context.RunnerNodePool }) |
        Select-Object -First 1
}

if ($Check -in @('All', 'Install')) {
    $pool = Get-ArcNodePool
    Test-ArcCondition 'runner-node-pool' (
        $null -ne $pool -and
        $pool.enableAutoScaling -eq $true -and
        [int]$pool.minCount -eq 0 -and
        [int]$pool.maxCount -ge 1 -and
        $pool.nodeLabels.workload -eq 'github-runner' -and
        @($pool.nodeTaints) -contains 'workload=github-runner:NoSchedule'
    ) $(if ($pool) {
        "autoscaling=$($pool.enableAutoScaling) min=$($pool.minCount) max=$($pool.maxCount)"
    } else {
        'runner node pool is missing'
    })

    & $helm status $script:ArcControllerRelease --namespace $script:ArcSystemNamespace 1>$null 2>$null
    Test-ArcCondition 'controller-release' ($LASTEXITCODE -eq 0) 'controller Helm release is installed'
    & $helm status $script:ArcRunnerRelease --namespace $script:ArcRunnerNamespace 1>$null 2>$null
    Test-ArcCondition 'runner-release' ($LASTEXITCODE -eq 0) 'runner scale-set Helm release is installed'

    $controllerDeployments = Get-ArcJson @('get', 'deployment', '-n', $script:ArcSystemNamespace, '-o', 'json')
    $readyControllers = if ($controllerDeployments) {
        @($controllerDeployments.items | Where-Object {
            [int]$_.status.availableReplicas -ge 1 -and
            [int]$_.status.availableReplicas -eq [int]$_.spec.replicas
        }).Count
    } else {
        0
    }
    Test-ArcCondition 'controller-ready' ($readyControllers -ge 1) "$readyControllers controller deployment(s) ready"

    $runnerSets = Get-ArcJson @('get', 'autoscalingrunnersets.actions.github.com', '-n', $script:ArcRunnerNamespace, '-o', 'json')
    $runnerSet = if ($runnerSets -and @($runnerSets.items).Count -eq 1) {
        @($runnerSets.items)[0]
    } else {
        $null
    }
    Test-ArcCondition 'runner-scale-set' ($null -ne $runnerSet) 'exactly one AutoScalingRunnerSet exists'
    if ($runnerSet) {
        $template = $runnerSet.spec.template.spec
        $requiredToleration = @($template.tolerations | Where-Object {
            $_.key -eq 'workload' -and
            $_.operator -eq 'Equal' -and
            $_.value -eq 'github-runner' -and
            $_.effect -eq 'NoSchedule'
        }).Count -eq 1
        Test-ArcCondition 'runner-template-scheduling' (
            $template.nodeSelector.workload -eq 'github-runner' -and $requiredToleration
        ) 'runner template selects and tolerates only the dedicated runner pool'
        Test-ArcCondition 'runner-scale-bounds' (
            [int]$runnerSet.spec.minRunners -eq 0 -and
            [int]$runnerSet.spec.maxRunners -ge 2 -and
            [int]$runnerSet.spec.maxRunners -le 5
        ) "min=$($runnerSet.spec.minRunners) max=$($runnerSet.spec.maxRunners)"
        Test-ArcCondition 'runner-service-account-token' (
            $template.serviceAccountName -eq 'arc-runner' -and
            $template.automountServiceAccountToken -eq $false
        ) 'runner uses an unprivileged service account without an API token'
        $privileged = @($template.containers | Where-Object { $_.securityContext.privileged -eq $true }).Count
        $hostPaths = @($template.volumes | Where-Object { $null -ne $_.hostPath }).Count
        Test-ArcCondition 'runner-no-privileged-host-access' (
            $privileged -eq 0 -and $hostPaths -eq 0
        ) 'runner template has no privileged container or hostPath volume'
    }

    $listenerPods = Get-ArcJson @('get', 'pods', '-n', $script:ArcSystemNamespace, '-o', 'json')
    $readyListeners = if ($listenerPods) {
        @($listenerPods.items | Where-Object {
            $_.metadata.name -match 'listener' -and
            @($_.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count -ge 1
        }).Count
    } else {
        0
    }
    Test-ArcCondition 'listener-ready' ($readyListeners -ge 1) "$readyListeners listener pod(s) ready"

    $podMonitors = Get-ArcJson @('get', 'podmonitor', '-n', $script:ArcSystemNamespace, '-o', 'json')
    $arcPodMonitorCount = if ($podMonitors) {
        @($podMonitors.items | Where-Object { $_.metadata.name -in @('arc-controller', 'arc-listener') }).Count
    } else {
        0
    }
    Test-ArcCondition 'arc-pod-monitors' (
        $arcPodMonitorCount -eq 2
    ) "$arcPodMonitorCount/2 ARC PodMonitor objects exist"
}

if ($Check -in @('All', 'Security')) {
    $systemNamespace = Get-ArcJson @('get', 'namespace', $script:ArcSystemNamespace, '-o', 'json')
    $runnerNamespace = Get-ArcJson @('get', 'namespace', $script:ArcRunnerNamespace, '-o', 'json')
    Test-ArcCondition 'namespace-boundary' (
        $systemNamespace -and
        $runnerNamespace -and
        $systemNamespace.metadata.labels.'pod-security.kubernetes.io/enforce' -eq 'baseline' -and
        $runnerNamespace.metadata.labels.'pod-security.kubernetes.io/enforce' -eq 'baseline' -and
        $runnerNamespace.metadata.labels.'pod-security.kubernetes.io/warn' -eq 'restricted'
    ) 'controller and runner namespaces enforce baseline and warn on restricted violations'

    $serviceAccount = Get-ArcJson @('get', 'serviceaccount', 'arc-runner', '-n', $script:ArcRunnerNamespace, '-o', 'json')
    Test-ArcCondition 'runner-service-account' (
        $serviceAccount -and $serviceAccount.automountServiceAccountToken -eq $false
    ) 'runner service account disables automatic token mounting'

    $canReadSecrets = & kubectl auth can-i get secrets `
        --namespace orders `
        --as "system:serviceaccount:$($script:ArcRunnerNamespace):arc-runner" 2>$null
    Test-ArcCondition 'runner-cannot-read-application-secrets' (
        $LASTEXITCODE -eq 0 -and ($canReadSecrets | Select-Object -First 1).Trim() -eq 'no'
    ) 'runner service account cannot get secrets in orders'

    $canCreateClusterRoles = & kubectl auth can-i create clusterroles.rbac.authorization.k8s.io `
        --as "system:serviceaccount:$($script:ArcRunnerNamespace):arc-runner" 2>$null
    Test-ArcCondition 'runner-cannot-administer-cluster' (
        $LASTEXITCODE -eq 0 -and ($canCreateClusterRoles | Select-Object -First 1).Trim() -eq 'no'
    ) 'runner service account cannot create ClusterRoles'

    $networkPolicies = Get-ArcJson @('get', 'networkpolicy', '-n', $script:ArcRunnerNamespace, '-o', 'json')
    Test-ArcCondition 'runner-ingress-policy' (
        $networkPolicies -and
        @($networkPolicies.items | Where-Object { $_.metadata.name -eq 'deny-unsolicited-ingress' }).Count -eq 1
    ) 'runner namespace denies unsolicited ingress'
}

if ($Check -in @('All', 'ScaleToZero')) {
    $ephemeralRunners = Get-ArcJson @('get', 'ephemeralrunners.actions.github.com', '-n', $script:ArcRunnerNamespace, '-o', 'json')
    $ephemeralRunnerCount = if ($ephemeralRunners) { @($ephemeralRunners.items).Count } else { 0 }
    $pods = Get-ArcJson @('get', 'pods', '-n', $script:ArcRunnerNamespace, '-o', 'json')
    $runnerPodCount = if ($pods) {
        @($pods.items | Where-Object { $_.metadata.name -notmatch 'listener' }).Count
    } else {
        0
    }
    Test-ArcCondition 'ephemeral-runners-clean' (
        $ephemeralRunnerCount -eq 0 -and $runnerPodCount -eq 0
    ) "$ephemeralRunnerCount EphemeralRunner object(s), $runnerPodCount runner pod(s)"

    if ($NodeScaleDownTimeoutMinutes -gt 0) {
        $deadline = [DateTime]::UtcNow.AddMinutes($NodeScaleDownTimeoutMinutes)
        do {
            $pool = Get-ArcNodePool
            $nodeCount = if ($pool) { [int]$pool.count } else { -1 }
            if ($nodeCount -eq 0) {
                break
            }
            Start-Sleep -Seconds 15
        } while ([DateTime]::UtcNow -lt $deadline)
        Test-ArcCondition 'runner-nodes-scaled-to-zero' (
            $nodeCount -eq 0
        ) "runner node count is $nodeCount"
    }
}

if ($Check -eq 'Cleanup') {
    & $helm status $script:ArcRunnerRelease --namespace $script:ArcRunnerNamespace 1>$null 2>$null
    $runnerReleaseAbsent = $LASTEXITCODE -ne 0
    & $helm status $script:ArcControllerRelease --namespace $script:ArcSystemNamespace 1>$null 2>$null
    $controllerReleaseAbsent = $LASTEXITCODE -ne 0
    Test-ArcCondition 'arc-releases-removed' (
        $runnerReleaseAbsent -and $controllerReleaseAbsent
    ) 'runner and controller Helm releases are absent'

    & kubectl get namespace $script:ArcRunnerNamespace 1>$null 2>$null
    $runnerNamespaceAbsent = $LASTEXITCODE -ne 0
    & kubectl get namespace $script:ArcSystemNamespace 1>$null 2>$null
    $systemNamespaceAbsent = $LASTEXITCODE -ne 0
    Test-ArcCondition 'arc-namespaces-removed' (
        $runnerNamespaceAbsent -and $systemNamespaceAbsent
    ) 'arc-runners and arc-systems are absent'

    $pool = Get-ArcNodePool
    Test-ArcCondition 'runner-node-pool-removed' ($null -eq $pool) 'arcrunner node pool is absent'

    if ($RepositoryUrl) {
        $slug = Assert-PrivateArcRepository -RepositoryUrl $RepositoryUrl
        $runnerCount = Invoke-Checked gh @(
            'api', "repos/$slug/actions/runners",
            '--jq', '.total_count'
        ) -Capture
        $runnerCount = [int](($runnerCount | Select-Object -First 1).Trim())
        Test-ArcCondition 'github-runner-registration-cleanup' (
            $runnerCount -eq 0
        ) "$runnerCount self-hosted runner registration(s) remain in the dedicated sandbox"
    }
}

$evidenceDirectory = New-EvidenceDirectory
$evidencePath = Join-Path $evidenceDirectory "arc-$($Check.ToLowerInvariant()).json"
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $evidencePath

if ($results.Where({ -not $_.Passed }).Count -gt 0) {
    throw "ARC validation failed. See $evidencePath."
}
Write-Host "ARC validation passed. Evidence: $evidencePath"
