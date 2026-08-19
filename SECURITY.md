# Security

## Lab data rules

- Use only disposable, synthetic data.
- Never paste or commit subscription IDs, tenant IDs, kubeconfigs, tokens, passwords, certificates, or production URLs.
- Use interactive Azure CLI authentication for learners, managed identity for Azure-hosted workloads, and Workload Identity for pods.
- Store lab secrets in Key Vault. Kubernetes Secret exercises use generated disposable values only.
- Delete generated evidence before sharing the repository.

## Azure scope

Use a dedicated lab subscription. If an instructor adapts the templates for a shared subscription, use dedicated resource groups, budgets, unique prefixes, expiration tags, and least-privilege assignments. Do not run the labs in a production cluster.

## Reporting a course vulnerability

Do not open a public issue containing sensitive details. Report the affected file, impact, and safe reproduction steps to the repository owner through the organization's private security channel.
