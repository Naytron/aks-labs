<#
.SYNOPSIS
Previews, deploys, or deletes the optional AKS node pool used by ARC runners.

.DESCRIPTION
Uses the tagged Standard lab cluster and a separate Bicep template. The pool is
tainted for GitHub runner workloads and permits autoscaler scale-to-zero.

.PARAMETER Action
Preview runs Azure what-if, Deploy previews then applies, and Delete removes the pool.

.PARAMETER MaxCount
Maximum ARC runner nodes. The concurrency exercise permits two through five.

.PARAMETER VmSize
Optional D-series override. The validated lab VM size is used by default.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Preview', 'Deploy', 'Delete')]
    [string]$Action,
    [ValidateRange(2, 5)]
    [int]$MaxCount = 3,
    [ValidatePattern('^$|^Standard_D[0-9]+[A-Za-z0-9_]*$')]
    [string]$VmSize = ''
)

. (Join-Path $PSScriptRoot 'common.ps1')

Assert-Command az
$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment standard
$cluster = $outputs.clusterName
$resourceGroup = $config.StandardResourceGroup
$template = Join-Path (Get-RepoRoot) 'infra/standard/arc-runner-pool.bicep'
$nodePoolName = 'arcrunner'
$deploymentName = 'aks-labs-arc-runner-pool'
$effectiveVmSize = if ($VmSize) { $VmSize } else { $config.NodeVmSize }

Assert-CourseResourceGroup $resourceGroup

& az aks nodepool show `
    --resource-group $resourceGroup `
    --cluster-name $cluster `
    --name $nodePoolName `
    --output none `
    --only-show-errors 2>$null
$poolExists = $LASTEXITCODE -eq 0

if ($Action -eq 'Delete') {
    if (-not $poolExists) {
        Write-Host 'ARC runner pool is already absent.'
        exit 0
    }
    if ($PSCmdlet.ShouldProcess("$cluster/$nodePoolName", 'Delete ARC runner node pool')) {
        Invoke-Checked az @(
            'aks', 'nodepool', 'delete',
            '--resource-group', $resourceGroup,
            '--cluster-name', $cluster,
            '--name', $nodePoolName,
            '--output', 'none',
            '--only-show-errors'
        )
    }
    exit 0
}

Write-Host 'Previewing the optional ARC runner node pool...'
Invoke-Checked az @(
    'deployment', 'group', 'what-if',
    '--resource-group', $resourceGroup,
    '--name', $deploymentName,
    '--template-file', $template,
    '--parameters',
    "clusterName=$cluster",
    "vmSize=$effectiveVmSize",
    "maxCount=$MaxCount",
    '--only-show-errors'
)

if ($Action -eq 'Preview') {
    Write-Host 'Preview complete. No Azure resources were changed.'
    exit 0
}

if ($PSCmdlet.ShouldProcess("$cluster/$nodePoolName", 'Deploy optional ARC runner node pool')) {
    Invoke-Checked az @(
        'deployment', 'group', 'create',
        '--resource-group', $resourceGroup,
        '--name', $deploymentName,
        '--template-file', $template,
        '--parameters',
        "clusterName=$cluster",
        "vmSize=$effectiveVmSize",
        "maxCount=$MaxCount",
        '--output', 'none',
        '--only-show-errors'
    )

    $pool = Invoke-Checked az @(
        'aks', 'nodepool', 'show',
        '--resource-group', $resourceGroup,
        '--cluster-name', $cluster,
        '--name', $nodePoolName,
        '--output', 'json',
        '--only-show-errors'
    ) -Capture | ConvertFrom-Json

    if (
        -not $pool.enableAutoScaling -or
        [int]$pool.minCount -ne 0 -or
        [int]$pool.maxCount -ne $MaxCount -or
        $pool.nodeLabels.workload -ne 'github-runner' -or
        @($pool.nodeTaints) -notcontains 'workload=github-runner:NoSchedule'
    ) {
        throw 'ARC runner pool was created without the required autoscaling or isolation settings.'
    }

    Write-Host "ARC runner pool is ready: min=0 max=$MaxCount, taint=workload=github-runner:NoSchedule."
}
