# AKS Hands-On Lab Guide

> Lives on the **`lab-guide`** branch of this repo, alongside the five-day AKS bootcamp on `main`. Grab [`index.html`](index.html) from this branch and open it in any browser — it's fully self-contained.

A self-contained, dark-theme HTML lab guide with **32 step-by-step labs** covering the full [Azure Kubernetes Service](https://learn.microsoft.com/azure/aks/) lifecycle — from `az aks create` to production guardrails.

Every lab gives you the same task three ways — **Azure Portal**, **Azure CLI (Bash)** and **kubectl & YAML** — because the control plane and the data plane are different skills, and you need both.

## What's covered

| # | Domain                          | Focus                  | Labs   |
| - | ------------------------------- | ---------------------- | ------ |
| 1 | Clusters & Node Pools           | Foundation             | 6      |
| 2 | Workloads & Scheduling          | Day-1 skills           | 6      |
| 3 | Networking                      | Where clusters break   | 6      |
| 4 | Storage                         | Stateful workloads     | 4      |
| 5 | Security & Identity             | Non-negotiable         | 5      |
| 6 | Scaling, Observability & Ops    | Day-2 operations       | 5      |
|   | **Total**                       |                        | **32** |

## What each lab includes

* **"What you need to know"** — the specific facts, defaults, limits and distinctions the lab is built on, stated up front.
* **Azure Portal steps** — numbered, with exact blade names, wizard tabs and field values.
* **Azure CLI (Bash)** — the equivalent using `az`, complete and runnable.
* **kubectl & YAML** — manifests and verification commands for the data-plane half.
* **Traps & gotchas** — the misconfigurations that bite in production.
* **Cleanup** — teardown commands so you don't leave billable nodes running.

## Reading it

Download or clone the `lab-guide` branch and open `index.html` in any browser. No build step, no server, no dependencies — everything is inlined in one file.

Features:

* Collapsible labs with Portal / CLI / kubectl tabs
* Copy button on every code block
* Live search across lab titles, commands **and** concepts (try `CNI overlay`, `workload identity`, `PDB`)
* Filter by domain and by difficulty (Foundational / Core / Advanced)
* Expand-all and print-friendly stylesheet
* Light/dark theme toggle

## Building

The HTML is generated from Python sources. Standard library only — no packages to install.

```
cd src
python build.py
```

This regenerates `index.html` at the repo root.

```
.
├── index.html              # generated — the lab guide
└── src
    ├── build.py            # generator: HTML/CSS/JS templating
    └── domains
        ├── d1.py           # Domain 1 — clusters & node pools
        ├── d2.py           # Domain 2 — workloads & scheduling
        ├── d3.py           # Domain 3 — networking
        ├── d4.py           # Domain 4 — storage
        ├── d5.py           # Domain 5 — security & identity
        └── d6.py           # Domain 6 — scaling, observability & ops
```

Each domain module exposes a `DOMAIN` dict and a `LABS` list. A lab is a plain dict:

```python
{
  "id": "2.6",
  "title": "Short imperative title",
  "time": "35 min",
  "level": "Core",              # Foundational | Core | Advanced
  "objective": "One sentence describing the outcome.",
  "exam":    [ "HTML-allowed bullets on what you need to know." ],
  "prereq":  "What you need before starting.",
  "portal":  [ "##Section heading", "Numbered step. HTML allowed." ],
  "cli":     r"""# Azure CLI (bash)""",
  "kubectl": r"""# kubectl & YAML""",
  "traps":   [ "HTML-allowed bullets on common mistakes." ],
  "cleanup": r"""# teardown commands""",
}
```

Notes:

* A `portal` entry beginning with `##` renders as a sub-heading; step numbering continues across headings.
* `exam`, `traps` and `portal` entries accept inline HTML (`<b>`, `<code>`, `<i>`).
* Use raw strings (`r"""..."""`) for `cli` / `kubectl` so backslashes and heredocs survive.

Then rerun `python build.py`.

## Cost warning

These labs deploy real Azure resources. **AKS nodes bill for every hour they run** — a three-node Standard_DS2_v2 cluster is roughly $6/day — and Standard-tier control planes, NAT gateways, load balancers and managed Prometheus/Grafana add to it.

Most labs share one cluster (`aks-lab` in `rg-aks-labs`, built in Lab 1.1). Stop it between sessions with `az aks stop`, run the cleanup block at the end of each lab, and delete the whole resource group when you're finished. Consider setting a [budget alert](https://learn.microsoft.com/azure/cost-management-billing/costs/tutorial-acm-create-budgets) on your subscription before you start.

## Accuracy

Command syntax reflects Azure CLI 2.x and AKS defaults as of authoring. AKS moves fast — features graduate from preview and defaults change. **Verify against [Microsoft Learn](https://learn.microsoft.com/azure/aks/) before relying on any specific flag, limit or default.**

Corrections are welcome — especially where AKS has changed a default, a limit, or a command flag. Open an issue or a PR against the relevant module in `src/domains/`, and rerun `python build.py` so `index.html` stays in sync with its sources.

## License

[MIT](LICENSE) © 2026 Nate Langston

Community study material. Not affiliated with, endorsed by, or sponsored by Microsoft.
