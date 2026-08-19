# AKS Automatic comparison environment

Deploy this environment only during Day 1. Inspect the managed defaults, deploy the course workload, capture evidence, and delete the resource group the same day.

```powershell
./scripts/deploy-lab.ps1 -Environment automatic -WhatIf
./scripts/deploy-lab.ps1 -Environment automatic
./scripts/cleanup-lab.ps1 -Mode Automatic
```

AKS Automatic is the recommended starting point for most production workloads. The Standard environment exists in this course because level-400 learners must understand the decisions that Automatic manages and the specialized cases that require direct control.
