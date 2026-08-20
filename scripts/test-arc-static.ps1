<#
.SYNOPSIS
Runs credential-free static validation for the optional ARC module.
#>
[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'arc-common.ps1')

$repoRoot = Get-RepoRoot
$helm = Get-ArcHelmCommand
$configuration = Get-ArcConfiguration
$controllerValues = Join-Path $repoRoot 'platform/arc/controller-values.yaml'
$runnerValues = Join-Path $repoRoot 'platform/arc/runner-scale-set-values.yaml'
$controllerChart = Get-ArcChartArguments -Chart Controller
$runnerChart = Get-ArcChartArguments -Chart RunnerScaleSet
$tempDirectory = Join-Path ([IO.Path]::GetTempPath()) "aks-labs-arc-$([guid]::NewGuid())"
New-Item -ItemType Directory -Path $tempDirectory | Out-Null

function Assert-ArcChartDigest {
    param(
        [Parameter(Mandatory)][string]$Chart,
        [Parameter(Mandatory)][string]$Version,
        [Parameter(Mandatory)][string]$ExpectedDigest
    )

    $output = & $helm show chart $Chart --version $Version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to inspect pinned ARC chart ${Chart}:$Version."
    }
    $digestLine = @($output | Where-Object { "$_" -match '^Digest:\s+(sha256:[a-f0-9]{64})$' }) |
        Select-Object -First 1
    if (-not $digestLine -or "$digestLine" -notmatch '^Digest:\s+(sha256:[a-f0-9]{64})$') {
        throw "ARC chart ${Chart}:$Version did not report an OCI digest."
    }
    if ($Matches[1] -ne $ExpectedDigest) {
        throw "ARC chart digest changed for ${Chart}:$Version."
    }
}

try {
    Assert-ArcChartDigest `
        -Chart $controllerChart[0] `
        -Version $controllerChart[2] `
        -ExpectedDigest $configuration.controllerChartDigest
    Assert-ArcChartDigest `
        -Chart $runnerChart[0] `
        -Version $runnerChart[2] `
        -ExpectedDigest $configuration.runnerScaleSetChartDigest

    $controllerManifest = Join-Path $tempDirectory 'controller.yaml'
    Invoke-Checked $helm @(
        'template', $script:ArcControllerRelease,
        $controllerChart[0],
        '--version', $controllerChart[2],
        '--namespace', $script:ArcSystemNamespace,
        '--include-crds',
        '--values', $controllerValues
    ) -Capture | Set-Content -LiteralPath $controllerManifest

    $runnerManifest = Join-Path $tempDirectory 'runner.yaml'
    Invoke-Checked $helm @(
        'template', $script:ArcRunnerRelease,
        $runnerChart[0],
        '--version', $runnerChart[2],
        '--namespace', $script:ArcRunnerNamespace,
        '--values', $runnerValues,
        '--set-string', 'githubConfigUrl=https://github.com/example/private-sandbox',
        '--set-string', "githubConfigSecret=$($script:ArcRunnerSecret)",
        '--set', 'minRunners=0',
        '--set', 'maxRunners=3'
    ) -Capture | Set-Content -LiteralPath $runnerManifest

    foreach ($manifest in @($controllerManifest, $runnerManifest)) {
        Invoke-Checked kubeconform @(
            '-strict',
            '-summary',
            '-ignore-missing-schemas',
            '-kubernetes-version', '1.36.0',
            $manifest
        )
    }

    $platformManifest = Join-Path $tempDirectory 'platform.yaml'
    Invoke-Checked kubectl @('kustomize', (Join-Path $repoRoot 'platform/arc')) -Capture |
        Set-Content -LiteralPath $platformManifest
    Invoke-Checked kubeconform @(
        '-strict',
        '-summary',
        '-ignore-missing-schemas',
        '-kubernetes-version', '1.36.0',
        $platformManifest,
        (Join-Path $repoRoot 'platform/arc/failures/deny-egress.yaml')
    )

    $runnerContent = Get-Content -LiteralPath $runnerManifest -Raw
    if ($runnerContent -notmatch 'automountServiceAccountToken:\s+false') {
        throw 'Rendered runner template does not disable service-account token mounting.'
    }
    if ($runnerContent -match '(?m)^\s*privileged:\s*true\s*$') {
        throw 'Rendered ARC runner unexpectedly enables privileged mode.'
    }
    if ($runnerContent -match '(?m)^\s*hostPath:\s*$') {
        throw 'Rendered ARC runner unexpectedly mounts a hostPath.'
    }
    if ($runnerContent -notmatch [regex]::Escape($configuration.runnerImage)) {
        throw 'Rendered runner image does not match the immutable version lock.'
    }

    $rejectedPublicTarget = $false
    try {
        $null = Get-ArcRepositorySlug -RepositoryUrl 'https://github.com/naytron/aks-labs'
    } catch {
        $rejectedPublicTarget = $_.Exception.Message -match 'public course repository'
    }
    if (-not $rejectedPublicTarget) {
        throw 'ARC repository guard did not reject the public course repository.'
    }

    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $PSScriptRoot 'deploy-arc.ps1'),
        '-RepositoryUrl', 'https://github.com/example/private-sandbox',
        '-MaxRunners', '3',
        '-DryRun'
    )
} finally {
    Remove-Item -LiteralPath $tempDirectory -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host 'ARC static validation passed.'
