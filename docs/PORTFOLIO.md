# Portfolio Notes

This repository documents the way I automate my technical workflow. It doubles as a showcase I can reference when discussing process improvements, neurodivergent-friendly tooling, or developer-experience topics.

## Why This Exists

- **Automate everything** – I prefer deterministic environments so I can focus on the task at hand rather than on rebuilding my toolchain. Reproducible Dev Containers + CI give me that peace of mind.
- **Minimise context switching** – Standardised tasks and scripts help me execute repeatable steps quickly, which is vital when executive function has limited bandwidth.
- **Shareable playbook** – When I publish a post (e.g. on LinkedIn), I can point to this repo and walk through the entire automation story: dependencies locked with `uv`, proxy-aware roles, corporate guidance, and health checks.

## Highlights to Mention Publicly

- `pyproject.toml` + `uv.lock` + `requirements-ansible.txt` combo (with a compatibility `requirements.txt`) that keeps both fast tooling (`uv`) and compatibility (`pip`).
- Proxy-ready roles (`ansible_environment`) that accept corporate overrides via variables, keeping automation reliable even behind firewalls.
- Windows bootstrap script validates admin rights, configures proxies, reports reboot requirements, and installs either Docker Desktop or Podman depending on licensing needs.
- Opinionated VS Code tasks for linting, health checks, dependency refresh, and Molecule tests.
- Multiple Dev Container templates (`ansible`, `golang`, `latex`, `terraform`) with helper scripts to switch stacks instantly.
- LaTeX Dev Container includes a build-time toggle for MiKTeX vs TeX Live to match CI or on-demand needs.
- Dev Container tooling: `scripts/check-devcontainer.sh` exercises every template headlessly, `scripts/debug-devcontainer.sh` drops you into a live stack for smoke tests, `scripts/devcontainer-metadata.py` verifies provisioning metadata, and `scripts/devcontainer-diff.py` highlights local tweaks versus the template.
- Terraform workflow script (`scripts/run-terraform-tests.sh`) runs fmt/validate across modules so infrastructure changes stay healthy in CI and locally.
- Starter Proxmox Terraform module under `infrastructure/proxmox_lab/` with documentation and tfvars template for homelab services.
- Molecule scenarios cover both the default stack and a LaTeX toggle run (MiKTeX → TeX Live) ensuring reproducible template switches.
- CI that mirrors local flow (lint → `ansible-test` sanity → playbook tests → check mode → Molecule → Dev Container build).
- `scripts/run-ansible-tests.sh` packages each role into a temporary collection so `ansible-test` sanity runs locally and in CI without extra scaffolding.
- Documentation for troubleshooting, corporate setups, and (future) multi-stack Dev Containers (Golang, LaTeX, Terraform).

## Story Outline for External Posts

1. Problem statement (manual setups, exponential complexity, need for automation).
2. Approach (Dev Container + Ansible roles + uv for locking).
3. Pain points addressed (corporate proxies, secret management, pre-commit guard rails).
4. Future roadmap (extra Dev Containers, CV automation in LaTeX).
5. Outcome call-to-action (repo link, invitation to discuss automation strategies).

You can adapt this file when drafting articles, conference abstracts, or internal docs.
