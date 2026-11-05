# Makefile for TOP 0.1% DevContainer Repository
# Provides convenient shortcuts for common development tasks

.PHONY: help
help: ## Show this help message
	@echo '╔════════════════════════════════════════════════════════════╗'
	@echo '║  TOP 0.1% DevContainer - Available Commands               ║'
	@echo '╚════════════════════════════════════════════════════════════╝'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ## Initial setup - install all dependencies
	@echo "🚀 Setting up development environment..."
	@command -v gh >/dev/null 2>&1 || (echo "Installing gh CLI..." && sudo apt-get update && sudo apt-get install -y gh)
	@$(MAKE) --no-print-directory lint-deps
	@echo "Installing pre-commit hooks..."
	@uv run --locked --no-build pre-commit install --install-hooks
	@echo "✅ Setup complete!"

.PHONY: lint-deps
lint-deps: ## Install what the lint hooks need: the uv.lock environment and the image's pinned Ansible collections
	@uv sync --locked --no-build
	@rm -rf .cache/ansible-lint/collections && mkdir -p .cache/ansible-lint/collections
	@uv run --locked --no-build bash devcontainers/ansible/install-collections.sh \
		.cache/ansible-lint/collections devcontainers/ansible/collections.txt

.PHONY: lint
lint: ## Run all linters (the same pre-commit run as CI's Lint job)
	@echo "🔍 Running linters..."
	@uv run --locked --no-build pre-commit run --all-files

.PHONY: lint-fix
lint-fix: ## Run linters and auto-fix issues
	@echo "🔧 Running linters with auto-fix..."
	@uv run --locked --no-build pre-commit run --all-files || uv run --locked --no-build pre-commit run --all-files
	@echo "✅ Auto-fix complete!"

.PHONY: security
security: ## Run security scans
	@echo "🔒 Running security scans..."
	@echo "Checking for secrets..."
	@uv run --locked --no-build pre-commit run detect-secrets --all-files
	@echo "Running Grype scan..."
	@if command -v grype >/dev/null 2>&1; then \
		grype dir:. --only-fixed --fail-on high; \
	else \
		echo "Grype not installed, skipping"; \
	fi
	@echo "✅ Security scan complete!"

.PHONY: test
test: ## Run all tests
	@echo "🧪 Running tests..."
	@if [ -d "tests" ]; then \
		pytest tests/ -v; \
	else \
		echo "No tests directory found"; \
	fi

.PHONY: build
build: ## Build all devcontainers locally
	@echo "🏗️  Building devcontainers..."
	@docker build -t devcontainer-terraform:local -f .devcontainer/Dockerfile .
	@echo "✅ Build complete!"

.PHONY: switch-ansible
switch-ansible: ## Switch to Ansible stack
	@./scripts/use-devcontainer.sh ansible

.PHONY: switch-terraform
switch-terraform: ## Switch to Terraform stack
	@./scripts/use-devcontainer.sh terraform

.PHONY: switch-golang
switch-golang: ## Switch to Golang stack
	@./scripts/use-devcontainer.sh golang

.PHONY: switch-latex
switch-latex: ## Switch to LaTeX stack
	@./scripts/use-devcontainer.sh latex

.PHONY: doctor-devcontainer
doctor-devcontainer: ## Diagnose active .devcontainer health and drift
	@bash ./scripts/doctor-devcontainer.sh

.PHONY: clean
clean: ## Clean cache and temporary files
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf .cache/* || true
	@echo "✅ Cleanup complete!"

.PHONY: update-deps
update-deps: ## Update all dependencies
	@echo "⬆️  Updating dependencies..."
	@uv run --locked --no-build pre-commit autoupdate --freeze
	@echo "✅ Dependencies updated! Review changes before committing."

.PHONY: check-alerts
check-alerts: ## Check GitHub security alerts
	@echo "🔔 Checking security alerts..."
	@gh api repos/malpanez/ansible-devcontainer-vscode/code-scanning/alerts --jq '.[] | select(.state == "open") | {number: .number, severity: .rule.severity, rule: .rule.id}' || echo "gh CLI not authenticated"

.PHONY: validate-yaml
validate-yaml: ## Validate all YAML files
	@echo "📝 Validating YAML files..."
	@uv run --locked --no-build pre-commit run yamllint --all-files

.PHONY: validate-docker
validate-docker: ## Validate all Dockerfiles
	@echo "🐳 Validating Dockerfiles..."
	@uv run --locked --no-build pre-commit run hadolint --all-files

.PHONY: ci-local
ci-local: lint security ## Run the lint and security checks locally (lint already runs yamllint and hadolint)
	@echo "✅ Full CI pipeline complete!"

.PHONY: git-status
git-status: ## Show enhanced git status
	@echo "📊 Git Status:"
	@git status --short --branch
	@echo ""
	@echo "📈 Recent commits:"
	@git log --oneline -5

.PHONY: pr-check
pr-check: lint test ## Pre-PR checklist - run before creating PR
	@echo "✅ PR checklist complete! Ready to push."

.PHONY: version
version: ## Show versions of all tools
	@echo "📦 Tool Versions:"
	@echo "Terraform:  $$(terraform version -json | jq -r '.terraform_version')"
	@echo "Terragrunt: $$(terragrunt --version | head -1)"
	@echo "TFLint:     $$(tflint --version)"
	@echo "Ansible:    $$(ansible --version | head -1)"
	@echo "Python:     $$(python --version)"
	@echo "Docker:     $$(docker --version)"
	@echo "gh CLI:     $$(gh --version | head -1)"

.DEFAULT_GOAL := help
