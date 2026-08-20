Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot 'common.ps1')

$script:ArcSystemNamespace = 'arc-systems'
$script:ArcRunnerNamespace = 'arc-runners'
$script:ArcControllerRelease = 'arc'
$script:ArcRunnerRelease = 'arc-aks-lab'
$script:ArcRunnerSecret = 'arc-github-app'
$script:ArcRunnerNodePool = 'arcrunner'

function Get-ArcConfiguration {
    $path = Join-Path (Get-RepoRoot) 'platform/arc/versions.json'
    if (-not (Test-Path -LiteralPath $path)) {
        throw "ARC version lock is missing at $path."
    }

    $configuration = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    foreach ($property in @(
        'helmMajorVersion',
        'controllerChart',
        'controllerChartVersion',
        'runnerScaleSetChart',
        'runnerScaleSetChartVersion'
    )) {
        if (-not $configuration.PSObject.Properties[$property] -or -not $configuration.$property) {
            throw "ARC version lock is missing '$property'."
        }
    }

    if ([int]$configuration.helmMajorVersion -ne 3) {
        throw 'ARC requires Helm 3 because current GitHub guidance does not document Helm 4 support.'
    }
    foreach ($versionProperty in @('controllerChartVersion', 'runnerScaleSetChartVersion')) {
        if ($configuration.$versionProperty -notmatch '^[0-9]+\.[0-9]+\.[0-9]+$') {
            throw "ARC $versionProperty must be a pinned semantic version."
        }
    }
    if ($configuration.controllerChartVersion -ne $configuration.runnerScaleSetChartVersion) {
        throw 'ARC controller and runner scale-set chart versions must be pinned together.'
    }
    return $configuration
}

function Get-ArcHelmCommand {
    $configuration = Get-ArcConfiguration
    $expectedMajor = [int]$configuration.helmMajorVersion
    $candidateNames = @('helm3', 'helm')

    foreach ($candidate in $candidateNames) {
        if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) {
            continue
        }
        $version = (& $candidate version --short 2>$null | Select-Object -First 1)
        if ($version -match "^v?$expectedMajor\.") {
            return $candidate
        }
    }

    throw "ARC requires Helm major version $expectedMajor. Install the pinned course tool before continuing."
}

function Get-ArcRepositorySlug {
    param(
        [Parameter(Mandatory)]
        [string]$RepositoryUrl
    )

    $uri = $null
    if (
        -not [Uri]::TryCreate($RepositoryUrl, [UriKind]::Absolute, [ref]$uri) -or
        $uri.Scheme -ne 'https' -or
        $uri.Host -ne 'github.com' -or
        $uri.UserInfo -or
        -not $uri.IsDefaultPort -or
        $uri.Query -or
        $uri.Fragment
    ) {
        throw 'ARC repository URL must be https://github.com/<owner>/<private-repository>.'
    }

    $segments = @($uri.AbsolutePath.Trim('/').Split('/', [StringSplitOptions]::RemoveEmptyEntries))
    if ($segments.Count -ne 2) {
        throw 'ARC repository URL must identify exactly one GitHub repository.'
    }
    $owner = $segments[0]
    $repository = $segments[1] -replace '\.git$', ''
    if (
        $owner -notmatch '^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$' -or
        $repository -notmatch '^[A-Za-z0-9_.-]+$'
    ) {
        throw 'ARC repository owner or name contains unsupported characters.'
    }

    $slug = "$owner/$repository"
    if ($slug -ieq 'naytron/aks-labs') {
        throw 'Refusing to register self-hosted runners to the public course repository.'
    }
    return $slug
}

function Assert-PrivateArcRepository {
    param(
        [Parameter(Mandatory)]
        [string]$RepositoryUrl
    )

    Assert-Command gh
    $slug = Get-ArcRepositorySlug -RepositoryUrl $RepositoryUrl
    & gh auth status --hostname github.com 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'GitHub CLI is not authenticated. Run gh auth login for an administrator of the private sandbox repository.'
    }

    $visibility = Invoke-Checked gh @(
        'repo', 'view', $slug,
        '--json', 'visibility',
        '--jq', '.visibility'
    ) -Capture
    $visibility = ($visibility | Select-Object -First 1).Trim()
    if ($visibility -ne 'PRIVATE') {
        throw "Refusing ARC deployment because the sandbox repository visibility is '$visibility', not PRIVATE."
    }
    return $slug
}

function Assert-ArcPrivateKeyFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    $repoRoot = [IO.Path]::GetFullPath((Get-RepoRoot)).TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    )
    $repoPrefix = "$repoRoot$([IO.Path]::DirectorySeparatorChar)"
    if ($resolved.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        & git -C $repoRoot check-ignore --quiet -- $resolved
        if ($LASTEXITCODE -ne 0) {
            throw 'GitHub App private key is inside the repository and is not ignored. Move it outside Git or into .aks-labs.'
        }
    }

    $firstLine = Get-Content -LiteralPath $resolved -TotalCount 1
    if ($firstLine -notmatch '^-----BEGIN (?:RSA )?PRIVATE KEY-----$') {
        throw 'GitHub App private key file is not a supported PEM private key.'
    }
    return $resolved
}

function Assert-ArcClusterContext {
    $config = Get-LabConfiguration
    $outputs = Get-DeploymentOutputs -Environment standard
    Assert-CourseResourceGroup $config.StandardResourceGroup

    $context = (& kubectl config current-context 2>$null)
    if ($LASTEXITCODE -ne 0 -or $context -ne $outputs.clusterName) {
        throw "Current kubectl context '$context' is not the Standard lab cluster '$($outputs.clusterName)'."
    }
    & kubectl get namespace default --request-timeout=10s --output name 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw 'The Standard lab Kubernetes API is not reachable with the current identity.'
    }

    return [pscustomobject]@{
        ClusterName = $outputs.clusterName
        ResourceGroup = $config.StandardResourceGroup
        RunnerNodePool = $script:ArcRunnerNodePool
        RunnerNamespace = $script:ArcRunnerNamespace
        SystemNamespace = $script:ArcSystemNamespace
    }
}

function Get-ArcChartArguments {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('Controller', 'RunnerScaleSet')]
        [string]$Chart
    )

    $configuration = Get-ArcConfiguration
    if ($Chart -eq 'Controller') {
        return @($configuration.controllerChart, '--version', $configuration.controllerChartVersion)
    }
    return @($configuration.runnerScaleSetChart, '--version', $configuration.runnerScaleSetChartVersion)
}
