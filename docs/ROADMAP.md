# Roadmap

The repository currently focuses on Ansible, but the goal is to reuse the same automation patterns for other stacks and to make onboarding even smoother.

## Short Term

- [ ] **Baseline Release** – capture the current Ansible-focused stack, refresh documentation for the new repo, and tag an initial release candidate that is safe to share publicly.
- [ ] **WSL2 Onboarding Flow** – tighten the Windows bootstrap so a new contributor can run a single PowerShell command, get WSL2 + Docker/Podman configured, and reopen the project in a Dev Container without manual tweaks.
- [x] **Terraform Ready Stack** – mirror the Ansible toolchain for Terraform by adding core binaries, linting, and smoke tests so infrastructure authors can switch languages without leaving the workspace. (Devcontainer + CI checks are live.)
- [ ] **Context Switch Tasks** – ship VS Code tasks (or Make targets) that rebuild `.devcontainer/` for Ansible, Terraform, Python, or Golang in one command to minimise downtime when swapping stacks.
- [x] **Automated Dependency Refresh** – schedule weekly lockfile bumps via `uv` with a PAT-backed PR workflow to keep Python tooling patched.
- [x] **Recurring Image Hardening** – run weekly Build & Publish containers with `apt full-upgrade` baked into every stack so Trivy scans trend down over time.

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
