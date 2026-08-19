[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Deploy', 'Delete')]
    [string]$Action
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment standard
$cluster = $outputs.clusterName
$resourceGroup = $config.StandardResourceGroup
$template = Join-Path (Get-RepoRoot) 'infra/standard/spot-pool.bicep'

Assert-CourseResourceGroup $resourceGroup
if ($Action -eq 'Delete') {
    & az aks nodepool show --resource-group $resourceGroup --cluster-name $cluster --name spot --output none --only-show-errors 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Spot pool is already absent.'
        exit 0
    }
    if ($PSCmdlet.ShouldProcess("$cluster/spot", 'Delete Spot node pool')) {
        Invoke-Checked az @(
            'aks', 'nodepool', 'delete',
            '--resource-group', $resourceGroup,
            '--cluster-name', $cluster,
            '--name', 'spot',
            '--output', 'none',
            '--only-show-errors'
        )
    }
    exit 0
}

Write-Host 'Previewing the short-lived Spot pool...'
Invoke-Checked az @(
    'deployment', 'group', 'what-if',
    '--resource-group', $resourceGroup,
    '--name', 'aks-labs-spot',
    '--template-file', $template,
    '--parameters', "clusterName=$cluster", "vmSize=$($config.NodeVmSize)",
    '--only-show-errors'
)
if ($PSCmdlet.ShouldProcess("$cluster/spot", 'Deploy short-lived Spot node pool')) {
    Invoke-Checked az @(
        'deployment', 'group', 'create',
        '--resource-group', $resourceGroup,
        '--name', 'aks-labs-spot',
        '--template-file', $template,
        '--parameters', "clusterName=$cluster", "vmSize=$($config.NodeVmSize)",
        '--output', 'none',
        '--only-show-errors'
    )
}
