[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Automatic', 'Daily', 'Final')]
    [string]$Mode,
    [switch]$Wait
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration -AllowExpired
$targetResourceGroup = if ($Mode -eq 'Automatic') {
    $config.AutomaticResourceGroup
} else {
    $config.StandardResourceGroup
}
$groupExists = (& az group exists --name $targetResourceGroup --output tsv --only-show-errors)
if ($groupExists -eq 'false') {
    Write-Host "$targetResourceGroup is already absent."
    exit 0
}

if ($Mode -eq 'Daily') {
    Assert-CourseResourceGroup $config.StandardResourceGroup
    $powerState = Invoke-Checked az @(
        'aks', 'show',
        '--resource-group', $config.StandardResourceGroup,
        '--name', $config.StandardCluster,
        '--query', 'powerState.code',
        '--output', 'tsv',
        '--only-show-errors'
    ) -Capture
    $powerState = ($powerState | Select-Object -First 1).Trim()
    $currentContext = (& kubectl config current-context 2>$null)
    if ($LASTEXITCODE -ne 0 -or $currentContext -ne $config.StandardCluster) {
        throw "Refusing daily cleanup: current context '$currentContext' is not '$($config.StandardCluster)'."
    }
    if ($powerState -eq 'Running' -and $PSCmdlet.ShouldProcess('orders namespace course jobs', 'Delete')) {
        Invoke-Checked kubectl @('delete', 'job', '-n', 'orders', '-l', 'aks-course=level400', '--ignore-not-found')
    }
    if ($powerState -eq 'Running' -and $PSCmdlet.ShouldProcess('orders namespace debug pods', 'Delete')) {
        Invoke-Checked kubectl @('delete', 'pod', '-n', 'orders', '-l', 'purpose=debug', '--ignore-not-found')
    }
    & az aks nodepool show `
        --resource-group $config.StandardResourceGroup `
        --cluster-name $config.StandardCluster `
        --name spot `
        --only-show-errors `
        --output none 2>$null
    $spotExists = $LASTEXITCODE -eq 0
    if ($spotExists -and $PSCmdlet.ShouldProcess('spot node pool', 'Delete')) {
        Invoke-Checked az @(
            'aks', 'nodepool', 'delete',
            '--resource-group', $config.StandardResourceGroup,
            '--cluster-name', $config.StandardCluster,
            '--name', 'spot',
            '--only-show-errors',
            '--output', 'none'
        )
    }
    if ($powerState -eq 'Running' -and $PSCmdlet.ShouldProcess($config.StandardCluster, 'Stop AKS cluster')) {
        Invoke-Checked az @(
            'aks', 'stop',
            '--resource-group', $config.StandardResourceGroup,
            '--name', $config.StandardCluster,
            '--only-show-errors',
            '--output', 'none'
        )
    } elseif ($powerState -eq 'Stopped') {
        Write-Host "$($config.StandardCluster) is already stopped."
    }
    $remaining = Invoke-Checked az @(
        'resource', 'list',
        '--resource-group', $config.StandardResourceGroup,
        '--query', '[].{Name:name,Type:type}',
        '--output', 'table',
        '--only-show-errors'
    ) -Capture
    Write-Host 'Daily cleanup complete. These supporting resources can still accrue charges:'
    $remaining | ForEach-Object { Write-Host $_ }
    exit 0
}

$resourceGroup = $targetResourceGroup

Assert-CourseResourceGroup $resourceGroup
if ($PSCmdlet.ShouldProcess($resourceGroup, 'Delete tagged course resource group')) {
    $arguments = @('group', 'delete', '--name', $resourceGroup, '--yes', '--only-show-errors')
    if (-not $Wait) {
        $arguments += '--no-wait'
    }
    Invoke-Checked az $arguments
}

if ($Wait) {
    $exists = (& az group exists --name $resourceGroup --output tsv --only-show-errors)
    if ($exists -ne 'false') {
        throw "Resource group $resourceGroup still exists."
    }
    Write-Host "Verified deletion of $resourceGroup."
} else {
    Write-Host "Deletion started for $resourceGroup. Rerun with -Wait to block and verify."
}
