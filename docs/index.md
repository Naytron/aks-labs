---
layout: home
title: AKS Level 400 Bootcamp
permalink: /
---

Build practical Azure Kubernetes Service skills from your first Kubernetes workload through production architecture, security, reliability, and incident response.

## Choose your path

| Path | Use it for | Start here |
| --- | --- | --- |
| Hands-on bootcamp | Five challenge-driven days with labs, failures, evidence, and cleanup | [Open the course map on GitHub](https://github.com/Naytron/aks-labs/blob/main/docs/course-map.md) |
| Interview preparation | 72 progressive AKS questions for Cloud, DevOps, SRE, and Platform roles | <a href="{{ '/interview-questions/' | relative_url }}">Open the question bank</a> |
| Quick reference | Architecture, security, triage, operations, and ARC reminders | [Open the cheat sheets on GitHub](https://github.com/Naytron/aks-labs/tree/main/docs/cheatsheets) |

## Course progression

| Stage | Focus |
| --- | --- |
| Level 100 | Kubernetes and AKS fundamentals |
| Level 200 | Networking, storage, identity, delivery, and operations |
| Level 300 | Security, reliability, observability, scaling, and troubleshooting |
| Level 400 | Enterprise architecture, multi-cluster operations, DR, FinOps, and production incidents |

The hands-on course is approximately 80 percent lab work. Its authoritative manifests, scripts, solutions, and evidence contracts remain in the [GitHub repository](https://github.com/Naytron/aks-labs).

## Before using Azure

The local prework and `kind` exercises do not require an Azure subscription. The full Azure path assumes a dedicated lab subscription, Owner capability, a supported region, and sufficient D-series quota.

Read the [setup guide](https://github.com/Naytron/aks-labs/blob/main/docs/setup.md) and [cost controls](https://github.com/Naytron/aks-labs/blob/main/docs/cost-controls.md) before deployment. Paid resources are never created by the repository's pull-request workflows.

## Optional Level 400 extension

The [GitHub Actions Runner Controller module](https://github.com/Naytron/aks-labs/tree/main/labs/06-arc-runners) covers ephemeral self-hosted runners, GitHub App authentication, isolated AKS capacity, two-layer autoscaling, security, break/fix, and cleanup.
