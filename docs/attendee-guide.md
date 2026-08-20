# Attendee guide

## Intended starting point

You should know Azure fundamentals and have basic experience with a command line, IP networking, and containers. No Kubernetes experience is assumed.

If you are new to Azure, Linux, networking, and containers as well, complete introductory training before this five-day bootcamp. The schedule does not have enough time to teach all of those foundations safely.

## How to work through a challenge

1. Read **Before you begin** and run the status command.
2. Read the outcome, must-know facts, and acceptance criteria before editing.
3. Use the linked cheat sheet instead of searching random examples.
4. Complete one checkpoint at a time.
5. On failure, collect evidence before changing or restarting anything.
6. Reveal hints in order. Open the solution only after the final hint.
7. Run the daily gate, cleanup, and next-state check.

All commands assume PowerShell from the repository root in the Dev Container.

## Environment progression

| Stage | Expected start | Workload stage | Expected end |
| --- | --- | --- | --- |
| Prework | No course resources | Full local `kind` | `kind` running |
| Day 1 | `kind` running | Day 1 starter -> full local; temporary Automatic Day 2 stage | Automatic deleted; `kind` retained |
| Day 2 | No Standard cluster | `azure-day2` | Standard stopped |
| Day 3 | Standard stopped | `azure-day3` through Flux | Standard stopped |
| Day 4 | Standard stopped | `azure-day4` plus opt-in scaling | Standard stopped; Spot absent |
| Day 5 | Standard stopped | Learner capstone | Standard deleted, or retained only for the instructor-approved ARC extension |
| Optional ARC | Day 5 gate passed; Standard retained | Private runner scale set | ARC removed; runner pool absent; Standard deleted or stopped |

Check state:

```powershell
./scripts/show-lab.ps1 -Environment kind
./scripts/show-lab.ps1 -Environment standard
```

Start a stopped Azure cluster:

```powershell
./scripts/start-lab.ps1 -Environment standard
```

## External prerequisites

### Day 3 GitOps

Flux needs a public GitHub repository and branch that contain your course copy. The instructor supplies the course repository URL before Day 3. Do not put a PAT or credential in a manifest or command URL.

### Day 3 human access

The instructor prepares two Entra test groups/accounts:

- platform operator;
- application operator.

If real accounts are unavailable, the instructor may use an authorization-only impersonation exercise. That simulation does **not** prove interactive Entra authentication and must be labeled accordingly.

### Optional ARC extension

The instructor must provide a disposable private sandbox repository and a narrowly scoped GitHub App installation. Never attach course runners to public `naytron/aks-labs` or a public fork. Keep the App private key outside Git, use the pinned `helm3` command for ARC read-only views, and follow [the instructor ARC setup](instructor-arc-setup.md).

## Evidence

Automated gates write to `evidence/`. Manual deliverables use the supplied worksheets/templates. Do not submit screenshots as the only evidence and review generated files before sharing them.

## Help ladder

1. Restate the failed acceptance criterion.
2. Locate the relevant object/controller in the cheat sheet.
3. Gather the first evidence source.
4. Use Hint 1, then Hint 2, then Hint 3.
5. Ask the coach for a bounded hint.
6. Review the reference solution after the attempt is recorded.

## Safety and cost

- Say the active subscription name and Kubernetes context before Azure or destructive commands.
- Stop if the target is not a tagged course resource.
- Delete Automatic on Day 1.
- Stop Standard after Days 2-4.
- Delete Spot immediately after its exercise.
- Delete Standard after Day 5 and verify the resource group is absent.
- If the optional ARC module follows Day 5, delay Standard deletion until ARC releases, GitHub registration, namespaces, Secret, and runner pool are removed.
- Budget alerts are delayed notifications, not an automatic shutoff.

See [cost controls](cost-controls.md) and [security rules](../SECURITY.md).
