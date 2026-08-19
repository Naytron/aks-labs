Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:E2EResults = [System.Collections.Generic.List[object]]::new()
$script:E2EArtifactDirectory = $null

function Initialize-E2ERun {
    param(
        [Parameter(Mandatory)]
        [string]$ArtifactDirectory
    )

    $script:E2EArtifactDirectory = $ArtifactDirectory
    New-Item -ItemType Directory -Path $script:E2EArtifactDirectory -Force | Out-Null
}

function Add-E2EResult {
    param(
        [Parameter(Mandatory)]
        [string]$Phase,
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [ValidateSet('PASS', 'FAIL', 'BLOCKED', 'SKIPPED')]
        [string]$Status,
        [Parameter(Mandatory)]
        [datetime]$StartedUtc,
        [Parameter(Mandatory)]
        [datetime]$EndedUtc,
        [string]$Expected = '',
        [string]$Observed = '',
        [string]$Evidence = '',
        [string]$Remediation = '',
        [bool]$Critical = $true
    )

    $script:E2EResults.Add([pscustomobject]@{
        phase = $Phase
        name = $Name
        status = $Status
        critical = $Critical
        startedUtc = $StartedUtc.ToString('o')
        endedUtc = $EndedUtc.ToString('o')
        durationSeconds = [Math]::Round(($EndedUtc - $StartedUtc).TotalSeconds, 3)
        expected = $Expected
        observed = $Observed
        evidence = $Evidence
        remediation = $Remediation
    })
}

function Redact-E2EFile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $content = Get-Content -LiteralPath $Path -Raw
    $content = $content `
        -replace '(?i)(subscription|tenant)([- ]?id)?[=: /]+[0-9a-f-]{36}', '$1$2=<redacted>' `
        -replace '(?i)(client|object|principal)([- ]?id)?[=: ]+[0-9a-f-]{36}', '$1$2=<redacted>' `
        -replace '(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '<guid-redacted>' `
        -replace '(?i)(access[_ -]?token|client[_ -]?secret|password|secret)[=: ]+\S+', '$1=<redacted>' `
        -replace '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (RSA |EC |OPENSSH )?PRIVATE KEY-----', '<private-key-redacted>'
    Set-Content -LiteralPath $Path -Value $content
}

function Invoke-E2EStep {
    param(
        [Parameter(Mandatory)]
        [string]$Phase,
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [scriptblock]$Action,
        [string]$Expected = '',
        [ValidateSet('FAIL', 'BLOCKED')]
        [string]$ErrorStatus = 'FAIL',
        [string]$Remediation = '',
        [bool]$Critical = $true,
        [switch]$PassThru,
        [switch]$ContinueOnError
    )

    $started = [DateTime]::UtcNow
    $safeName = ($Name.ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
    $logPath = Join-Path $script:E2EArtifactDirectory "$Phase-$safeName.log"
    try {
        & $Action *>&1 | Tee-Object -FilePath $logPath | ForEach-Object { Write-Host $_ }
        $ended = [DateTime]::UtcNow
        Redact-E2EFile -Path $logPath
        Add-E2EResult `
            -Phase $Phase `
            -Name $Name `
            -Status PASS `
            -StartedUtc $started `
            -EndedUtc $ended `
            -Expected $Expected `
            -Observed 'Completed without error.' `
            -Evidence $logPath `
            -Critical $Critical
        if ($PassThru) { return $true }
        return
    } catch {
        $ended = [DateTime]::UtcNow
        $_ | Out-String | Add-Content -LiteralPath $logPath
        Redact-E2EFile -Path $logPath
        Add-E2EResult `
            -Phase $Phase `
            -Name $Name `
            -Status $ErrorStatus `
            -StartedUtc $started `
            -EndedUtc $ended `
            -Expected $Expected `
            -Observed $_.Exception.Message `
            -Evidence $logPath `
            -Remediation $Remediation `
            -Critical $Critical
        if (-not $ContinueOnError) { throw }
        if ($PassThru) { return $false }
        return
    }
}

function Add-E2ENonRunResult {
    param(
        [Parameter(Mandatory)]
        [string]$Phase,
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [ValidateSet('BLOCKED', 'SKIPPED')]
        [string]$Status,
        [string]$Expected = '',
        [string]$Observed = '',
        [string]$Remediation = '',
        [bool]$Critical = $true
    )

    $now = [DateTime]::UtcNow
    Add-E2EResult `
        -Phase $Phase `
        -Name $Name `
        -Status $Status `
        -StartedUtc $now `
        -EndedUtc $now `
        -Expected $Expected `
        -Observed $Observed `
        -Remediation $Remediation `
        -Critical $Critical
}

function Import-E2EResults {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    foreach ($result in @(Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)) {
        $script:E2EResults.Add($result)
    }

    function Test-E2ECriticalPhasePassed {
        param([Parameter(Mandatory)][string]$Phase)

        $matching = @($script:E2EResults | Where-Object { $_.phase -eq $Phase -and $_.critical })
        return $matching.Count -gt 0 -and @($matching | Where-Object status -ne 'PASS').Count -eq 0
    }
}

function Complete-E2ERun {
    param(
        [Parameter(Mandatory)]
        [string]$ResultsPath,
        [Parameter(Mandatory)]
        [string]$SummaryPath
    )

    $script:E2EResults | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ResultsPath
    Redact-E2EFile -Path $ResultsPath

    $criticalFailures = @($script:E2EResults | Where-Object { $_.critical -and $_.status -eq 'FAIL' })
    $criticalBlocks = @($script:E2EResults | Where-Object { $_.critical -and $_.status -eq 'BLOCKED' })
    $decision = if ($criticalFailures.Count -gt 0) {
        'NOT READY'
    } elseif ($criticalBlocks.Count -gt 0) {
        'BLOCKED'
    } else {
        'READY'
    }

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('# AKS bootcamp E2E summary')
    $lines.Add('')
    $lines.Add("**Decision:** $decision")
    $lines.Add('')
    $lines.Add('| Phase | Test | Status | Seconds |')
    $lines.Add('| --- | --- | --- | ---: |')
    foreach ($result in $script:E2EResults) {
        $lines.Add("| $($result.phase) | $($result.name) | $($result.status) | $($result.durationSeconds) |")
    }
    $lines.Add('')
    $lines.Add('## Blocked or failed')
    $lines.Add('')
    foreach ($result in @($script:E2EResults | Where-Object { $_.status -in @('FAIL', 'BLOCKED') })) {
        $lines.Add("- **$($result.phase) / $($result.name):** $($result.observed) $($result.remediation)")
    }
    Set-Content -LiteralPath $SummaryPath -Value $lines
    Redact-E2EFile -Path $SummaryPath
    Get-ChildItem -Path $script:E2EArtifactDirectory -Recurse -File |
        ForEach-Object { Redact-E2EFile -Path $_.FullName }

    return [pscustomobject]@{
        Decision = $decision
        Failures = $criticalFailures.Count
        Blocks = $criticalBlocks.Count
        ResultsPath = $ResultsPath
        SummaryPath = $SummaryPath
    }
}
