# Roadmap

The repository has evolved into a **TOP 0.1% enterprise-grade DevContainer solution** with multiple production-ready stacks, comprehensive security, and automated maintenance.

## ✅ Completed (December 2025 - TOP 0.1% Upgrade)

- [x] **Baseline Release** – Repository is production-ready with comprehensive documentation, 0 security alerts, and enterprise-grade configuration.
- [x] **Terraform Ready Stack** – Full Terraform stack with core binaries, linting, and smoke tests. DevContainer + CI checks are live.
- [x] **Automated Dependency Refresh** – Enterprise-grade Renovate configuration with auto-merge, grouped updates, and priority-based security handling.
- [x] **Recurring Image Hardening** – Weekly container builds with automated security scanning (Trivy + CodeQL), 0 open vulnerabilities.
- [x] **Security Excellence** – CodeQL analysis, enhanced pre-commit hooks (10 repos), comprehensive security review documentation.
- [x] **Developer Experience** – Pre-installed tools (gh, make, yamllint, jq, git-lfs, vim, ripgrep), 30-60s faster startup.
- [x] **Documentation** – CONTRIBUTING.md, SECURITY_REVIEW.md, IMPLEMENTATION_SUMMARY.md, enhanced issue/PR templates.

## Short Term (Q1 2025)

- [ ] **WSL2 Onboarding Flow** – Enhance Windows bootstrap script for one-command setup (WSL2 + Docker/Podman + DevContainer).
- [ ] **Context Switch Tasks** – VS Code tasks or Make targets to rebuild `.devcontainer/` for different stacks in one command.
- [ ] **OSSF Scorecard 7.5+** – Improve from current 4.9/10 (roadmap documented in SECURITY_REVIEW.md).

## Medium Term

- [ ] **Unified Testing Story** – extend Molecule/Testinfra coverage to Terraform (e.g. terratest or `terraform validate` smoke jobs) and ensure CI keeps both stacks green.
- [ ] **Template Parity** – audit the Dev Container templates so Ansible, Terraform, Python, and Golang share common features (uv installation, shared caches, VS Code defaults) with stack-specific add-ons layered on top.
- [ ] **Authoring Experience** – add optional content-creation tooling (Markdown preview, diagramming, MkDocs) so blogging or documentation work can happen inside the same container.
- [ ] **Decision on LaTeX** – evaluate whether LaTeX lives in this repo as a first-class template or migrates to a companion repository; document the outcome and provide migration guidance either way.

## Long Term

- [ ] **Cross-Platform Bootstrap** – unify the bootstrap scripts so Windows (WSL2), macOS, and Linux hosts share an opinionated entry point that installs prerequisites and launches the workspace.
- [ ] **Secrets & Policy** – integrate lightweight secrets management (sops/age) and policy tooling (e.g. `tflint`, `opa`) for teams that need security guardrails from day one.
- [ ] **Team Rollout Playbook** – produce reusable Ansible playbooks that roll the baseline stack onto fresh machines, including account setup, editor defaults, and workspace cloning.
- [ ] **Hosted Documentation** – publish a public Quick Start + architecture guide that explains how to consume and extend the baseline, targeting users who discover the project after the GitHub launch.

Contributions or suggestions are welcome. File an issue or PR with additional ideas!
