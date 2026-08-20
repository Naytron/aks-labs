# ARC platform assets

These files support the optional post-capstone [ARC runner module](../../labs/06-arc-runners/README.md).

## Pinned compatibility

- ARC controller chart: `0.14.2`
- ARC runner scale-set chart: `0.14.2`
- Helm: `3.21.4`
- Actions runner: `2.336.0`

`versions.json` records chart OCI digests, immutable controller/runner image references, and the upstream release commit. `test-arc-static.ps1` verifies the chart digests and rendered images.

GitHub's current ARC prerequisite documents Helm 3. The core course retains Helm 4 as `helm`; ARC automation resolves the separate `helm3` binary.

## Placement

- `arc-systems`: controller, listener, and PodMonitors on the always-on general pool.
- `arc-runners`: runner scale set, GitHub App Secret, guardrails, and ephemeral runners.
- `arcrunner` node pool: runner pods only, selected and tolerated through `template.spec`.

The standard manifests enforce baseline Pod Security, warn/audit restricted violations, disable the runner service-account token, bound runner namespace resources, and deny unsolicited ingress. The default values do not enable Docker-in-Docker or Kubernetes container mode.

## Use

Do not install the values files directly or place a credential in them. Use:

```powershell
./scripts/deploy-arc.ps1 -DryRun -RepositoryUrl "https://github.com/example/private-sandbox"
Get-Help ./scripts/deploy-arc.ps1 -Full
Get-Help ./scripts/cleanup-arc.ps1 -Full
```

Live deployment requires a verified private repository and a pre-created GitHub App key file. The public course repository is rejected.

## Upgrade

Update only after reviewing the [ARC release](https://github.com/actions/actions-runner-controller/releases), [upgrade order](https://docs.github.com/actions/how-tos/manage-runners/use-actions-runner-controller/deploy-runner-scale-sets#upgrading-arc), chart values, runner release, and image manifests. Update `versions.json`, both values files, the Helm 3 tool pin if required, contracts, and documentation together; then run the full static and private live gates.
