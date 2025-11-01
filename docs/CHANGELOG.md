# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-stack Dev Container support (Ansible, Golang, LaTeX, Terraform) with
  helper scripts to switch stacks and debug builds.
- Comprehensive CI pipeline (linting, playbooks, ansible-test sanity, Molecule,
  Dev Container builds for Docker/Podman, Terraform validation, Trivy scan).
- Terraform baseline module (`infrastructure/proxmox_lab`) with automation
  script (`scripts/run-terraform-tests.sh`) and VS Code task.
- Documentation for onboarding (README, Quick Start, secrets guidance, roadmap,
  portfolio notes) plus roadmap alignment to future goals.

Use this section to track ongoing work until the first tagged release.
