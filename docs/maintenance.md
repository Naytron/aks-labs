# Course maintenance

Review quarterly and four weeks before each delivery.

1. Check [supported AKS versions](https://learn.microsoft.com/azure/aks/supported-kubernetes-versions) and Kubernetes client skew.
2. Update `.devcontainer/tools.env` from official release pages and refresh SHA-256 values.
3. Update Azure CLI and Dev Container feature versions.
4. Check AVM module `version.json` files in `Azure/bicep-registry-modules`.
5. Run Bicep build and `what-if` in the delivery region.
6. Render the starter, kind, Azure Day 2/3/4, and Flux Kustomize paths and validate all schemas.
7. Re-run every failure injection and daily gate.
8. Review AKS deprecations, feature registrations, pricing, and regional availability.
9. Pilot the clean Dev Container, Automatic, Standard, stop/start, Flux, incidents, and cleanup; record elapsed time and actual cost in `release-readiness.md`.

Do not silently float versions in learner environments. Update pins in one change with validation evidence and release notes.
