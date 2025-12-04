# Makefile for ansible-devcontainer-vscode
# Universal task runner for CLI, CI, and any IDE
#
# Usage: make <target>
#        make help  - Show all available targets

.PHONY: help
help:  ## Show this help message
	@echo "Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}' | \
		sort
	@echo ""
	@echo "Stack switching:"
	@grep -E '^switch-.*:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[33m%-25s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Testing
# =============================================================================

.PHONY: test
test:  ## Run all tests (smoke + Terraform + Python)
	@echo "Running smoke tests..."
	@./scripts/run-smoke-tests.sh
	@echo ""
	@echo "Running Terraform tests..."
	@./scripts/run-terraform-tests.sh
	@echo ""
	@echo "Running Python tests..."
	@pytest tests/ -v

.PHONY: test-smoke
test-smoke:  ## Run smoke tests only
	@./scripts/run-smoke-tests.sh

.PHONY: test-terraform
test-terraform:  ## Run Terraform tests only
	@./scripts/run-terraform-tests.sh

.PHONY: test-ansible
test-ansible:  ## Run Ansible tests with Molecule
	@./scripts/run-ansible-tests.sh

.PHONY: test-quick
test-quick:  ## Run quick sanity checks
	@echo "Quick sanity checks..."
	@ansible --version >/dev/null 2>&1 && echo "✓ Ansible OK" || echo "✗ Ansible missing"
	@terraform --version >/dev/null 2>&1 && echo "✓ Terraform OK" || echo "✗ Terraform missing"
	@yamllint --version >/dev/null 2>&1 && echo "✓ yamllint OK" || echo "✗ yamllint missing"

# =============================================================================
# Code Quality
# =============================================================================

.PHONY: lint
lint:  ## Run all linters (pre-commit on all files)
	@echo "Running pre-commit hooks on all files..."
	@uvx pre-commit run --all-files

.PHONY: lint-yaml
lint-yaml:  ## Run YAML linting only
	@yamllint .

.PHONY: lint-ansible
lint-ansible:  ## Run Ansible linting only
	@uvx ansible-lint playbooks/ roles/

.PHONY: format
format:  ## Format all code (Python, Terraform, YAML)
	@echo "Formatting Python files..."
	@uvx ruff format .
	@echo "Formatting Terraform files..."
	@terraform fmt -recursive devcontainers/terraform/ || true
	@echo "Done!"

.PHONY: format-check
format-check:  ## Check formatting without making changes
	@uvx ruff format --check .
	@terraform fmt -check -recursive devcontainers/terraform/ || true

# =============================================================================
# Development
# =============================================================================

.PHONY: install
install:  ## Install Python dependencies with uv
	@echo "Installing Python dependencies..."
	@uv pip install --system -e .

.PHONY: install-dev
install-dev:  ## Install Python dependencies + dev tools
	@echo "Installing dev dependencies..."
	@uv pip install --system -e ".[dev]"
	@uvx pre-commit install

.PHONY: clean
clean:  ## Clean build artifacts and caches
	@echo "Cleaning build artifacts..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Done!"

.PHONY: clean-all
clean-all: clean  ## Clean everything including Docker volumes
	@echo "Cleaning Docker volumes..."
	@docker volume rm uv-cache ansible-galaxy-cache 2>/dev/null || true
	@echo "Done!"

# =============================================================================
# Container Operations
# =============================================================================

.PHONY: build
build:  ## Build all devcontainer images
	@echo "Building all devcontainer images..."
	@for stack in ansible terraform golang latex; do \
		echo ""; \
		echo "Building $$stack..."; \
		docker build -t devcontainer-$$stack devcontainers/$$stack/; \
	done
	@echo ""
	@echo "✓ All images built successfully!"

.PHONY: build-ansible
build-ansible:  ## Build Ansible devcontainer only
	@docker build -t devcontainer-ansible devcontainers/ansible/

.PHONY: build-terraform
build-terraform:  ## Build Terraform devcontainer only
	@docker build -t devcontainer-terraform devcontainers/terraform/

.PHONY: build-golang
build-golang:  ## Build Golang devcontainer only
	@docker build -t devcontainer-golang devcontainers/golang/

.PHONY: build-latex
build-latex:  ## Build LaTeX devcontainer only
	@docker build -t devcontainer-latex devcontainers/latex/

.PHONY: smoke
smoke:  ## Run smoke tests on built containers
	@for stack in ansible terraform golang latex; do \
		echo "Smoke testing $$stack..."; \
		./scripts/smoke-devcontainer-image.sh $$stack || exit 1; \
	done

# =============================================================================
# Stack Switching (Devcontainer Context)
# =============================================================================

.PHONY: switch-ansible
switch-ansible:  ## Switch to Ansible devcontainer stack
	@./scripts/use-devcontainer.sh ansible
	@echo "✓ Switched to Ansible stack. Reopen in container to apply."

.PHONY: switch-terraform
switch-terraform:  ## Switch to Terraform devcontainer stack
	@./scripts/use-devcontainer.sh terraform
	@echo "✓ Switched to Terraform stack. Reopen in container to apply."

.PHONY: switch-golang
switch-golang:  ## Switch to Golang devcontainer stack
	@./scripts/use-devcontainer.sh golang
	@echo "✓ Switched to Golang stack. Reopen in container to apply."

.PHONY: switch-latex
switch-latex:  ## Switch to LaTeX devcontainer stack
	@./scripts/use-devcontainer.sh latex
	@echo "✓ Switched to LaTeX stack. Reopen in container to apply."

# =============================================================================
# Maintenance
# =============================================================================

.PHONY: update-deps
update-deps:  ## Update Python dependencies
	@echo "Updating Python dependencies..."
	@uv pip compile pyproject.toml -o requirements.txt
	@uv pip install --system -r requirements.txt

.PHONY: update-hooks
update-hooks:  ## Update pre-commit hooks
	@uvx pre-commit autoupdate

.PHONY: cleanup-branches
cleanup-branches:  ## Cleanup merged Git branches (dry-run)
	@./scripts/cleanup-merged-branches.sh --dry-run

.PHONY: cleanup-branches-force
cleanup-branches-force:  ## Cleanup merged Git branches (for real)
	@./scripts/cleanup-merged-branches.sh

.PHONY: check-versions
check-versions:  ## Check tool versions across project
	@echo "Tool versions in use:"
	@echo ""
	@echo "Python:      $$(python --version 2>&1 | cut -d' ' -f2 || echo 'Not installed')"
	@echo "Terraform:   $$(terraform --version 2>&1 | head -1 | cut -d'v' -f2 || echo 'Not installed')"
	@echo "Go:          $$(go version 2>&1 | awk '{print $$3}' | cut -d'o' -f2 || echo 'Not installed')"
	@echo "Ansible:     $$(ansible --version 2>&1 | head -1 | awk '{print $$3}' || echo 'Not installed')"
	@echo "uv:          $$(uv --version 2>&1 | cut -d' ' -f2 || echo 'Not installed')"
	@echo ""
	@echo "See .github/versions.yml for canonical versions"

.PHONY: check-security
check-security:  ## Run security checks (detect-secrets)
	@echo "Running security scans..."
	@uvx detect-secrets scan --baseline .secrets.baseline

# =============================================================================
# Documentation
# =============================================================================

.PHONY: docs
docs:  ## Open documentation index
	@echo "Opening documentation..."
	@cat docs/README.md

.PHONY: readme
readme:  ## Display main README
	@cat README.md

# =============================================================================
# CI/CD Helpers
# =============================================================================

.PHONY: ci-test
ci-test: test lint  ## Run all CI tests locally

.PHONY: ci-build
ci-build: build smoke  ## Run all CI build steps locally

.PHONY: validate
validate:  ## Validate project configuration files
	@echo "Validating YAML files..."
	@yamllint .github/workflows/*.yml
	@echo "Validating Dockerfiles..."
	@docker run --rm -i hadolint/hadolint < devcontainers/ansible/Dockerfile || true
	@echo "Validating pre-commit config..."
	@uvx pre-commit validate-config

# =============================================================================
# Info
# =============================================================================

.PHONY: info
info:  ## Display project information
	@echo "Project: ansible-devcontainer-vscode"
	@echo "Repository: https://github.com/malpanez/ansible-devcontainer-vscode"
	@echo ""
	@echo "Available stacks:"
	@echo "  - Ansible (default)"
	@echo "  - Terraform"
	@echo "  - Golang"
	@echo "  - LaTeX"
	@echo ""
	@echo "Run 'make help' to see all available commands"

.PHONY: version
version:  ## Show project version
	@echo "Version: 0.1.0"
	@echo "See docs/CHANGELOG.md for release notes"

# Default target
.DEFAULT_GOAL := help
