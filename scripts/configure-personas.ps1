[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [guid]$PlatformGroupObjectId,
    [Parameter(Mandatory)]
    [guid]$ApplicationGroupObjectId,
    [switch]$Remove
)

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-LabConfiguration
$outputs = Get-DeploymentOutputs -Environment standard
$clusterId = Invoke-Checked az @(
    'aks', 'show',
    '--resource-group', $config.StandardResourceGroup,
    '--name', $outputs.clusterName,
    '--query', 'id',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
$clusterId = ($clusterId | Select-Object -First 1).Trim()
$namespaceScope = "$clusterId/namespaces/orders"

$assignments = @(
    @{
        Principal = $PlatformGroupObjectId.Guid
        Role = 'Azure Kubernetes Service RBAC Admin'
        Scope = $clusterId
        Label = 'platform operator'
    },
    @{
        Principal = $ApplicationGroupObjectId.Guid
        Role = 'Azure Kubernetes Service RBAC Writer'
        Scope = $namespaceScope
        Label = 'application operator'
    }
)

foreach ($assignment in $assignments) {
    if ($Remove) {
        if ($PSCmdlet.ShouldProcess($assignment.Label, "Remove $($assignment.Role)")) {
            Invoke-Checked az @(
                'role', 'assignment', 'delete',
                '--assignee', $assignment.Principal,
                '--role', $assignment.Role,
                '--scope', $assignment.Scope,
                '--only-show-errors'
            )
        }
    } elseif ($PSCmdlet.ShouldProcess($assignment.Label, "Assign $($assignment.Role)")) {
        Invoke-Checked az @(
            'role', 'assignment', 'create',
            '--assignee-object-id', $assignment.Principal,
            '--assignee-principal-type', 'Group',
            '--role', $assignment.Role,
            '--scope', $assignment.Scope,
            '--output', 'none',
            '--only-show-errors'
        )
    }
}
