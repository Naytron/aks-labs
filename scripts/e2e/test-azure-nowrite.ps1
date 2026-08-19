[CmdletBinding()]
param()

. (Join-Path (Split-Path -Parent $PSScriptRoot) 'common.ps1')

$root = Get-RepoRoot
$config = Get-LabConfiguration
$deployerObjectId = Invoke-Checked az @(
    'ad', 'signed-in-user', 'show',
    '--query', 'id',
    '--output', 'tsv',
    '--only-show-errors'
) -Capture
$deployerObjectId = ($deployerObjectId | Select-Object -First 1).Trim()

foreach ($resourceGroup in @($config.AutomaticResourceGroup, $config.StandardResourceGroup)) {
    $exists = Invoke-Checked az @('group', 'exists', '--name', $resourceGroup, '--output', 'tsv', '--only-show-errors') -Capture
    if (($exists | Select-Object -First 1).Trim() -ne 'false') {
        throw "No-write E2E requires $resourceGroup to be absent."
    }
}

Invoke-Checked pwsh @('-NoProfile', '-File', (Join-Path $root 'scripts/preflight.ps1'), '-CloudOnly')
foreach ($environment in @('automatic', 'standard')) {
    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/deploy-lab.ps1'),
        '-Environment', $environment,
        '-WhatIf'
    )
    $parameterFile = Join-Path $root ".aks-labs/$environment-parameters.json"
    Invoke-Checked az @(
        'deployment', 'sub', 'validate',
        '--name', "aks-labs-e2e-validate-$environment-$($config.Prefix)-$($config.Location)",
        '--location', $config.Location,
        '--template-file', (Join-Path $root "infra/$environment/main.bicep"),
        '--parameters', "@$parameterFile",
        '--output', 'none',
        '--only-show-errors'
    )
}

Invoke-Checked az @('bicep', 'build', '--file', (Join-Path $root 'infra/standard/spot-pool.bicep'), '--stdout') | Out-Null

foreach ($resourceGroup in @($config.AutomaticResourceGroup, $config.StandardResourceGroup)) {
    $exists = Invoke-Checked az @('group', 'exists', '--name', $resourceGroup, '--output', 'tsv', '--only-show-errors') -Capture
    if (($exists | Select-Object -First 1).Trim() -ne 'false') {
        throw "No-write E2E unexpectedly created $resourceGroup."
    }
}
