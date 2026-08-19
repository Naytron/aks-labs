# Instructor identity and Git prerequisites

Complete this before Day 3.

## Entra test personas

Prepare two disposable test groups or paired accounts:

| Persona | Intended proof | Minimum course access |
| --- | --- | --- |
| Platform operator | Cluster-wide read and controlled platform administration | Instructor-selected AKS RBAC role at cluster scope |
| Application operator | Workload changes only in `orders` | AKS RBAC Writer at `orders` namespace scope |

Requirements:

- Do not share passwords, kubeconfigs, service-principal secrets, or personal accounts.
- Use group-based role assignments where possible.
- Verify each account can sign in before class.
- Record one allowed and one denied action for each persona.
- Remove course-only assignments after the bootcamp.

Apply the prepared group object IDs without storing them in the repository:

```powershell
./scripts/configure-personas.ps1 `
  -PlatformGroupObjectId "<group-object-id>" `
  -ApplicationGroupObjectId "<group-object-id>"
```

Remove them after the live pilot:

```powershell
./scripts/configure-personas.ps1 `
  -PlatformGroupObjectId "<group-object-id>" `
  -ApplicationGroupObjectId "<group-object-id>" `
  -Remove
```

If test accounts are unavailable, use `kubectl auth can-i --as` only as an authorization simulation. Tell learners it does not prove Entra authentication.

## Public Git repository

Before Day 3, publish the course to a public GitHub repository or provide a public learner fork:

- branch contains `platform/environments/azure-day3` and the validation workflow;
- repository URL has no credential or token;
- learners can create a branch and observe CI;
- instructor confirms managed Flux can read it anonymously;
- solutions remain available but are clearly separated from learner files.

Use:

```powershell
./scripts/bootstrap-gitops.ps1 `
  -RepositoryUrl "https://github.com/naytron/aks-labs" `
  -Branch main `
  -Stage day3
```

Private repositories require an authentication design outside the default course path.
