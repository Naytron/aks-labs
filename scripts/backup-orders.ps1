[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Backup', 'RestoreTest')]
    [string]$Mode,
    [string]$Path = 'evidence/orders-backup.db'
)

. (Join-Path $PSScriptRoot 'common.ps1')

$outputs = Get-DeploymentOutputs -Environment standard
$context = $outputs.clusterName
$currentContext = (& kubectl config current-context 2>$null)
if ($LASTEXITCODE -ne 0 -or $currentContext -ne $context) {
    throw "Select the Standard context '$context' before backup or restore."
}

$root = Get-RepoRoot
$resolvedPath = if ([IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $root $Path }

if ($Mode -eq 'Backup') {
    $directory = Split-Path -Parent $resolvedPath
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $pod = (& kubectl --context $context get pod -n orders -l app.kubernetes.io/name=orders-api -o jsonpath='{.items[0].metadata.name}')
    if ($LASTEXITCODE -ne 0 -or -not $pod) {
        throw 'No orders-api pod is available.'
    }
    $backupCommand = "import sqlite3; source=sqlite3.connect('/data/orders.db'); target=sqlite3.connect('/tmp/orders-backup.db'); source.backup(target); target.close(); source.close()"
    Invoke-Checked kubectl @('--context', $context, 'exec', '-n', 'orders', $pod, '--', 'python', '-c', $backupCommand)
    Invoke-Checked kubectl @('--context', $context, 'cp', "orders/${pod}:/tmp/orders-backup.db", $resolvedPath)
    Invoke-Checked kubectl @('--context', $context, 'exec', '-n', 'orders', $pod, '--', 'rm', '-f', '/tmp/orders-backup.db')
    $hash = (Get-FileHash -LiteralPath $resolvedPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "Backup written to $resolvedPath (sha256 $hash)."
    exit 0
}

if (-not (Test-Path -LiteralPath $resolvedPath)) {
    throw "Backup file not found at $resolvedPath."
}

$manifest = @'
apiVersion: v1
kind: Namespace
metadata:
  name: orders-restore
  labels:
    pod-security.kubernetes.io/enforce: restricted
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restore-data
  namespace: orders-restore
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: restore-check
  namespace: orders-restore
spec:
  restartPolicy: Never
  automountServiceAccountToken: false
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    runAsGroup: 10001
    fsGroup: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: restore
      image: python:3.14.0-slim-trixie@sha256:0aecac02dc3d4c5dbb024b753af084cafe41f5416e02193f1ce345d671ec966e
      command: [python, -c, "import time; time.sleep(600)"]
      resources:
        requests: {cpu: 10m, memory: 24Mi}
        limits: {cpu: 100m, memory: 64Mi}
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: {drop: [ALL]}
        readOnlyRootFilesystem: true
      volumeMounts:
        - name: data
          mountPath: /restore
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: restore-data
'@

try {
    $manifest | & kubectl --context $context apply -f -
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create isolated restore target.' }
    Invoke-Checked kubectl @('--context', $context, 'wait', '--for=condition=Ready', 'pod/restore-check', '-n', 'orders-restore', '--timeout=5m')
    Invoke-Checked kubectl @('--context', $context, 'cp', $resolvedPath, 'orders-restore/restore-check:/restore/orders.db')
    $count = Invoke-Checked kubectl @(
        '--context', $context,
        'exec', '-n', 'orders-restore', 'restore-check', '--',
        'python', '-c', "import sqlite3; print(sqlite3.connect('/restore/orders.db').execute('select count(*) from orders').fetchone()[0])"
    ) -Capture
    Write-Host "Isolated restore verified $count order row(s)."
} finally {
    & kubectl --context $context delete namespace orders-restore --ignore-not-found --wait=true 2>$null | Out-Null
}
