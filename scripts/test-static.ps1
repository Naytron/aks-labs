[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'common.ps1')

$root = Get-RepoRoot
Push-Location $root
try {
    $parseErrors = [System.Collections.Generic.List[object]]::new()
    Get-ChildItem -Path (Join-Path $root 'scripts') -Filter '*.ps1' -File | ForEach-Object {
        $tokens = $null
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            $_.FullName,
            [ref]$tokens,
            [ref]$errors
        ) | Out-Null
        foreach ($error in @($errors)) { $parseErrors.Add($error) }
    }
    if ($parseErrors.Count -gt 0) {
        throw "PowerShell parsing failed:`n$($parseErrors | Out-String)"
    }

    Invoke-Checked python @('-m', 'unittest', 'discover', '-s', 'app/orders-api', '-p', 'test_*.py')
    Invoke-Checked python @('-m', 'unittest', 'discover', '-s', 'app/storefront', '-p', 'test_*.py')
    Invoke-Checked python @('-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py')

    foreach ($template in @(
        'infra/automatic/main.bicep',
        'infra/automatic/platform.bicep',
        'infra/standard/main.bicep',
        'infra/standard/platform.bicep',
        'infra/standard/spot-pool.bicep',
        'infra/standard/arc-runner-pool.bicep'
    )) {
        Invoke-Checked az @('bicep', 'build', '--file', $template, '--stdout') | Out-Null
    }

    foreach ($overlay in @(
        'platform/environments/kind',
        'labs/01-foundations/starter',
        'platform/environments/azure-day2',
        'platform/environments/azure-day3',
        'platform/environments/azure-day4',
        'platform/gitops/clusters/lab'
    )) {
        $rendered = Invoke-Checked kubectl @('kustomize', $overlay) -Capture
        $tempManifest = Join-Path ([IO.Path]::GetTempPath()) "aks-labs-$([guid]::NewGuid()).yaml"
        try {
            $rendered | Set-Content -LiteralPath $tempManifest
            Invoke-Checked kubeconform @(
                '-strict',
                '-summary',
                '-ignore-missing-schemas',
                '-kubernetes-version', '1.36.0',
                $tempManifest
            )
        } finally {
            Remove-Item -LiteralPath $tempManifest -Force -ErrorAction SilentlyContinue
        }
    }

    foreach ($manifest in @(
        'labs/03-security-delivery/manifests/connectivity-probe.yaml',
        'labs/04-operations/manifests/scale-pressure.yaml',
        'labs/04-operations/manifests/spot-workload.yaml',
        'platform/arc/failures/deny-egress.yaml'
    )) {
        Invoke-Checked kubeconform @(
            '-strict',
            '-summary',
            '-kubernetes-version', '1.36.0',
            $manifest
        )
    }

    Invoke-Checked pwsh @(
        '-NoProfile',
        '-File', (Join-Path $root 'scripts/test-arc-static.ps1')
    )
} finally {
    Pop-Location
}

Write-Host 'Static validation passed.'
