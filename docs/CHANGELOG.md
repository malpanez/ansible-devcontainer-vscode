# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Auto-publish to GHCR**: Images now publish automatically on push to `main` affecting `devcontainers/**` ([#PR])
- **GHCR Cleanup Workflow**: Automated weekly cleanup of old container images with intelligent retention policy
- **Renovate Integration**: Auto-merge dependency updates with grouping and security prioritization
- **Auto-merge Workflow**: Automatic merging of dependency PRs when CI passes
- **Security Scorecard**: Weekly OpenSSF Scorecard analysis for security posture monitoring
- **Quality Metrics Workflow**: Automated code quality analysis (complexity, maintainability, dead code)
- **PR Template**: Comprehensive pull request template with checklist
- **Troubleshooting Guide**: Complete guide at `docs/TROUBLESHOOTING.md`
- **Centralized Versions**: Tool versions now managed in `.github/versions.yml`
- **New Badges**: Added OpenSSF Scorecard, GHCR, and Renovate badges to README
- **LaTeX Improvements**:
  - Tectonic recipe for auto-compilation in VS Code
  - Persistent caching for UV, pre-commit, and Tectonic
  - Spell checker support (English, Spanish)
  - Optimized file watchers
  - Git smart commit enabled

### Changed
- **Terraform Version**: Unified to 1.9.6 across all workflows and Dockerfiles
- **Go Version**: Updated from 1.22 to 1.23
- **Terragrunt**: Updated from 0.54.22 to 0.67.1
- **TFLint**: Updated from 0.51.2 to 0.54.0
- **SOPS**: Updated from 3.9.0 to 3.9.3
- **Age**: Updated from 1.1.1 to 1.2.1
- **Trivy**: Unified to v0.58.2 across all workflows
- **Dependency Management**: Migrated from Dependabot to Renovate
  - Renovate provides superior dependency grouping and auto-merge capabilities
  - Added dependency grouping (ansible, testing, linting, GitHub Actions)
  - Added labels per stack (ansible-stack, terraform-stack, etc.)
- **CI Performance**: Added pre-commit cache (~30% faster builds)
- **Build Containers**: Added timeouts and max-parallel limit for better resource usage

### Improved
- **Documentation**: Enhanced `.trivyignore` with detailed CVE tracking and review schedule
- **Security**: Better CVE management with documented acceptance criteria
- **DX**: LaTeX devcontainer now auto-compiles on save with Tectonic

### Fixed
- **Terraform Version Inconsistency**: CI was using 1.7.5 while devcontainer used 1.9.6
- **GHCR Image Accumulation**: Old images were never cleaned up automatically
- **Dependency Updates**: Replaced Dependabot with Renovate for better automation

### Security
- Updated all tool versions to patch known vulnerabilities
- Added automated security scanning with OpenSSF Scorecard
- Enhanced Trivy scanning across all workflows
- Documented CVE acceptance in `.trivyignore`

---

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
