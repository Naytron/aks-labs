[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateRange(1, 2)]
    [int]$Minimum
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment standard
$cluster = $outputs.clusterName

Assert-CourseResourceGroup $config.StandardResourceGroup
Invoke-Checked az @(
    'aks', 'nodepool', 'update',
    '--resource-group', $config.StandardResourceGroup,
    '--cluster-name', $cluster,
    '--name', 'user',
    '--update-cluster-autoscaler',
    '--min-count', "$Minimum",
    '--max-count', '3',
    '--output', 'none',
    '--only-show-errors'
)

for ($attempt = 0; $attempt -lt 60; $attempt++) {
    $count = (& kubectl --context $cluster get nodes -l agentpool=user --no-headers 2>$null | Measure-Object -Line).Lines
    if ($count -ge $Minimum) {
        Write-Host "User pool minimum is $Minimum; $count user node(s) are visible."
        exit 0
    }
    Start-Sleep -Seconds 5
}

throw "User pool did not reach $Minimum visible node(s) within five minutes."
