[CmdletBinding()]
param(
    [ValidateSet('All', 'Cost', 'Identity', 'Platform', 'Workload')]
    [string]$Check = 'All',
    [ValidateSet('kind', 'automatic', 'standard')]
    [string]$Environment = 'standard',
    [ValidateSet('Prework', 'Day1', 'Day2', 'Day3', 'Day4', 'Day5')]
    [string]$Gate
)

. (Join-Path $PSScriptRoot 'common.ps1')

$results = [System.Collections.Generic.List[object]]::new()
function Test-Condition {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    $results.Add([pscustomobject]@{ Name = $Name; Passed = $Passed; Detail = $Detail })
    $mark = if ($Passed) { 'pass' } else { 'fail' }
    Write-Host "[$mark] $Name - $Detail"
}

if ($Gate) {
    switch ($Gate) {
        'Prework' { $Environment = 'kind'; $Check = 'Workload' }
        'Day1' { $Environment = 'kind'; $Check = 'Workload' }
        'Day2' { $Environment = 'standard'; $Check = 'All' }
        'Day3' { $Environment = 'standard'; $Check = 'All' }
        'Day4' { $Environment = 'standard'; $Check = 'All' }
        'Day5' { $Environment = 'standard'; $Check = 'All' }
    }
}

if ($Check -in @('All', 'Platform', 'Workload', 'Identity')) {
    $context = (& kubectl config current-context 2>$null)
    $expectedContext = if ($Environment -eq 'kind') {
        'kind-aks-labs'
    } else {
        (Get-DeploymentOutputs -Environment $Environment).clusterName
    }
    Test-Condition 'kube-context' (
        $LASTEXITCODE -eq 0 -and $context -eq $expectedContext
    ) "context is '$context'; expected '$expectedContext'"

    $namespace = (& kubectl get namespace orders -o json 2>$null)
    Test-Condition 'namespace' ($LASTEXITCODE -eq 0 -and $namespace) 'orders namespace exists'
}

if ($Check -in @('All', 'Workload')) {
    foreach ($deployment in @('orders-api', 'storefront')) {
        $available = (& kubectl get deployment $deployment -n orders -o jsonpath='{.status.availableReplicas}' 2>$null)
        $desired = (& kubectl get deployment $deployment -n orders -o jsonpath='{.spec.replicas}' 2>$null)
        Test-Condition "deployment:$deployment" (
            $LASTEXITCODE -eq 0 -and [int]$available -ge 1 -and [int]$available -eq [int]$desired
        ) "$available/$desired replicas available"
    }
    $endpointCount = (& kubectl get endpointslice -n orders -l kubernetes.io/service-name=orders-api -o jsonpath='{range .items[*].endpoints[*]}{.addresses[0]}{"`n"}{end}' 2>$null | Measure-Object -Line).Lines
    Test-Condition 'service-endpoints' ($endpointCount -ge 1) "$endpointCount orders-api endpoint(s)"

    foreach ($deployment in @('orders-api', 'storefront')) {
        $definition = (& kubectl get deployment $deployment -n orders -o json 2>$null | ConvertFrom-Json)
        $container = $definition.spec.template.spec.containers[0]
        Test-Condition "probes:$deployment" (
            $container.startupProbe -and $container.readinessProbe -and $container.livenessProbe
        ) 'startup, readiness, and liveness probes exist'
        Test-Condition "resources:$deployment" (
            $container.resources.requests.cpu -and
            $container.resources.requests.memory -and
            $container.resources.limits.cpu -and
            $container.resources.limits.memory
        ) 'CPU and memory requests/limits exist'
        Test-Condition "security:$deployment" (
            $definition.spec.template.spec.securityContext.runAsNonRoot -eq $true -and
            $container.securityContext.allowPrivilegeEscalation -eq $false -and
            $container.securityContext.readOnlyRootFilesystem -eq $true -and
            @($container.securityContext.capabilities.drop) -contains 'ALL'
        ) 'restricted non-root container settings exist'
    }

    if ($Environment -eq 'kind') {
        try {
            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8080/healthz' -TimeoutSec 5
            Test-Condition 'external-health' ($health.status -eq 'alive') 'localhost storefront is alive'
        } catch {
            Test-Condition 'external-health' $false $_.Exception.Message
        }
    } else {
        $gatewayAddress = (& kubectl get gateway orders -n orders -o jsonpath='{.status.addresses[0].value}' 2>$null)
        Test-Condition 'gateway-address' ([bool]$gatewayAddress) "Gateway address is $gatewayAddress"
        if ($gatewayAddress) {
            try {
                $health = Invoke-RestMethod -Uri "http://$gatewayAddress/healthz" -TimeoutSec 10
                Test-Condition 'external-health' ($health.status -eq 'alive') 'Gateway storefront is alive'
            } catch {
                Test-Condition 'external-health' $false $_.Exception.Message
            }
        }
    }
}

if ($Check -in @('All', 'Platform') -and $Environment -ne 'kind') {
    $config = Get-LabConfiguration
    $outputs = Get-DeploymentOutputs -Environment $Environment
    $resourceGroup = if ($Environment -eq 'automatic') { $config.AutomaticResourceGroup } else { $config.StandardResourceGroup }
    $cluster = (& az aks show --resource-group $resourceGroup --name $outputs.clusterName --output json --only-show-errors | ConvertFrom-Json)
    Test-Condition 'local-accounts' ($cluster.disableLocalAccounts -eq $true) 'local AKS accounts are disabled'
    Test-Condition 'entra-azure-rbac' (
        $cluster.aadProfile.managed -eq $true -and $cluster.aadProfile.enableAzureRbac -eq $true
    ) 'managed Entra authentication and Azure RBAC are enabled'
    if ($Environment -eq 'standard') {
        Test-Condition 'network-profile' (
            $cluster.networkProfile.networkPlugin -eq 'azure' -and
            $cluster.networkProfile.networkPluginMode -eq 'overlay' -and
            $cluster.networkProfile.networkDataplane -eq 'cilium' -and
            $cluster.networkProfile.networkPolicy -eq 'cilium'
        ) 'Azure CNI Overlay with Cilium data plane/policy is enabled'
        $systemPool = @($cluster.agentPoolProfiles | Where-Object mode -eq 'System') | Select-Object -First 1
        Test-Condition 'system-pool-taint' (
            @($systemPool.nodeTaints) -contains 'CriticalAddonsOnly=true:NoSchedule'
        ) 'system pool is tainted for critical add-ons'
    }

    $gateway = (& kubectl get gateway orders -n orders -o json 2>$null | ConvertFrom-Json)
    $accepted = @($gateway.status.conditions | Where-Object { $_.type -eq 'Accepted' -and $_.status -eq 'True' }).Count -gt 0
    $programmed = @($gateway.status.conditions | Where-Object { $_.type -eq 'Programmed' -and $_.status -eq 'True' }).Count -gt 0
    Test-Condition 'gateway-conditions' ($accepted -and $programmed) 'Gateway is Accepted and Programmed'
}

if (
    $Check -in @('All', 'Identity') -and
    $Environment -eq 'standard' -and
    (-not $Gate -or $Gate -in @('Day3', 'Day4', 'Day5'))
) {
    $serviceAccountClient = (& kubectl get serviceaccount orders-api -n orders -o jsonpath='{.metadata.annotations.azure\.workload\.identity/client-id}' 2>$null)
    Test-Condition 'workload-identity-serviceaccount' (
        $LASTEXITCODE -eq 0 -and $serviceAccountClient -and $serviceAccountClient -notmatch 'REPLACE_WITH'
    ) 'service account has a concrete client ID'
    $secretProvider = (& kubectl get secretproviderclass orders-key-vault -n orders -o name 2>$null)
    Test-Condition 'secret-provider-class' ($LASTEXITCODE -eq 0 -and $secretProvider) 'Key Vault CSI object exists'
    $podSecurity = (& kubectl get namespace orders -o json 2>$null | ConvertFrom-Json).metadata.labels.'pod-security.kubernetes.io/enforce'
    Test-Condition 'pod-security' ($podSecurity -eq 'restricted') 'namespace enforces restricted Pod Security'
    $networkPolicyNames = (& kubectl get networkpolicy -n orders -o jsonpath='{.items[*].metadata.name}' 2>$null)
    $networkPolicyCount = @($networkPolicyNames -split '\s+' | Where-Object { $_ }).Count
    Test-Condition 'network-policies' ($networkPolicyCount -ge 6) "$networkPolicyCount NetworkPolicies exist"

    try {
        $configJson = & kubectl exec -n orders deployment/storefront -- python -c "import urllib.request; print(urllib.request.urlopen('http://orders-api:8080/api/config', timeout=5).read().decode())" 2>$null
        $appConfig = $configJson | ConvertFrom-Json
        Test-Condition 'secret-mounted' ($appConfig.secret.mounted -eq $true) 'application reports a mounted secret without returning its value'
    } catch {
        Test-Condition 'secret-mounted' $false $_.Exception.Message
    }
}

if ($Check -in @('All', 'Cost') -and $Environment -ne 'kind') {
    $config = Get-LabConfiguration
    $resourceGroup = if ($Environment -eq 'automatic') { $config.AutomaticResourceGroup } else { $config.StandardResourceGroup }
    $group = (& az group show --name $resourceGroup --output json --only-show-errors 2>$null)
    Test-Condition 'resource-group' ($LASTEXITCODE -eq 0 -and $group) "$resourceGroup exists"
    if ($group) {
        $tags = ($group | ConvertFrom-Json).tags
        Test-Condition 'expiration-tag' (
            $tags.expiration -eq $config.Expiration
        ) "expiration is '$($tags.expiration)'; expected '$($config.Expiration)'"

        $budgets = @(& az consumption budget list --resource-group $resourceGroup --output json --only-show-errors | ConvertFrom-Json)
        Test-Condition 'budget' (
            $LASTEXITCODE -eq 0 -and $budgets.Count -ge 1 -and ($budgets | Where-Object { $_.amount -le $config.Budget })
        ) "$($budgets.Count) budget(s) found with configured guardrail $($config.Budget) USD"

        $resources = @(& az resource list --resource-group $resourceGroup --output json --only-show-errors | ConvertFrom-Json)
        $allowedTypes = if ($Environment -eq 'automatic') {
            @(
                'Microsoft.Consumption/budgets',
                'Microsoft.ContainerRegistry/registries',
                'Microsoft.ContainerService/managedClusters'
            )
        } else {
            @(
                'Microsoft.Consumption/budgets',
                'Microsoft.ContainerRegistry/registries',
                'Microsoft.ContainerService/managedClusters',
                'Microsoft.Insights/dataCollectionEndpoints',
                'Microsoft.Insights/dataCollectionRuleAssociations',
                'Microsoft.Insights/dataCollectionRules',
                'Microsoft.KeyVault/vaults',
                'Microsoft.KubernetesConfiguration/extensions',
                'Microsoft.KubernetesConfiguration/fluxConfigurations',
                'Microsoft.ManagedIdentity/userAssignedIdentities',
                'Microsoft.Monitor/accounts',
                'Microsoft.Network/publicIPAddresses',
                'Microsoft.Network/virtualNetworks',
                'Microsoft.OperationalInsights/workspaces',
                'Microsoft.OperationsManagement/solutions'
            )
        }
        $unexpected = @($resources | Where-Object { $_.type -notin $allowedTypes })
        Test-Condition 'resource-inventory' (
            $LASTEXITCODE -eq 0 -and $unexpected.Count -eq 0
        ) "$($resources.Count) resource(s); unexpected types: $(@($unexpected.type) -join ', ')"
    }
}

if ($Gate -in @('Day3', 'Day4', 'Day5')) {
    $config = Get-LabConfiguration
    $outputs = Get-DeploymentOutputs -Environment standard
    $fluxJson = & az k8s-configuration flux show `
        --resource-group $config.StandardResourceGroup `
        --cluster-name $outputs.clusterName `
        --cluster-type managedClusters `
        --name orders `
        --output json `
        --only-show-errors 2>$null
    $flux = if ($LASTEXITCODE -eq 0 -and $fluxJson) { $fluxJson | ConvertFrom-Json } else { $null }
    Test-Condition 'flux-provisioning' (
        $flux -and $flux.provisioningState -eq 'Succeeded'
    ) "Flux provisioning state is $(if ($flux) { $flux.provisioningState } else { 'missing' })"
    $workloadJson = & kubectl get kustomization orders-workload -n flux-system -o json 2>$null
    $workloadKustomization = if ($LASTEXITCODE -eq 0 -and $workloadJson) {
        $workloadJson | ConvertFrom-Json
    } else {
        $null
    }
    $fluxReady = if ($workloadKustomization) {
        @(
            @($workloadKustomization.status.conditions) |
                Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }
        ).Count -gt 0
    } else {
        $false
    }
    $expectedFluxPath = if ($Gate -eq 'Day3') {
        './platform/environments/azure-day3'
    } else {
        './platform/environments/azure-day4'
    }
    Test-Condition 'flux-workload' (
        $workloadKustomization -and
        $fluxReady -and
        $workloadKustomization.spec.path -eq $expectedFluxPath
    ) "orders-workload Ready=$fluxReady path=$(if ($workloadKustomization) { $workloadKustomization.spec.path } else { 'missing' }), expected $expectedFluxPath"
}

if ($Gate -in @('Day4', 'Day5')) {
    $podMonitorCount = @(& kubectl get podmonitor -n orders -o name 2>$null).Count
    Test-Condition 'pod-monitors' ($podMonitorCount -ge 2) "$podMonitorCount PodMonitor objects exist"
    $amaMetricsCount = @(& kubectl get pods -n kube-system -l rsName=ama-metrics -o name 2>$null).Count
    Test-Condition 'managed-prometheus' ($amaMetricsCount -ge 1) "$amaMetricsCount managed Prometheus collector pod(s) exist"
    & az aks nodepool show --resource-group (Get-LabConfiguration).StandardResourceGroup --cluster-name (Get-DeploymentOutputs -Environment standard).clusterName --name spot --output none --only-show-errors 2>$null
    Test-Condition 'spot-cleanup' ($LASTEXITCODE -ne 0) 'Spot node pool is absent at the gate'
}

if ($Gate -eq 'Day1') {
    $config = Get-LabConfiguration
    $automaticExists = (& az group exists --name $config.AutomaticResourceGroup --output tsv --only-show-errors)
    Test-Condition 'automatic-cleanup' ($automaticExists -eq 'false') 'Automatic resource group is deleted'
}

$evidenceDirectory = New-EvidenceDirectory
$evidenceName = if ($Gate) { "gate-$($Gate.ToLowerInvariant()).json" } else { "validation-$($Environment.ToLowerInvariant())-$($Check.ToLowerInvariant()).json" }
$path = Join-Path $evidenceDirectory $evidenceName
$results | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path

if ($results.Where({ -not $_.Passed }).Count -gt 0) {
    throw "Validation failed. See $path."
}
Write-Host "Validation passed. Evidence: $path"
