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
	@command -v pre-commit >/dev/null 2>&1 || (echo "Installing pre-commit..." && uvx pre-commit --version)
	@echo "Installing pre-commit hooks..."
	@uvx pre-commit install --install-hooks
	@echo "✅ Setup complete!"

.PHONY: lint
lint: ## Run all linters
	@echo "🔍 Running linters..."
	@uvx pre-commit run --all-files

.PHONY: lint-fix
lint-fix: ## Run linters and auto-fix issues
	@echo "🔧 Running linters with auto-fix..."
	@uvx pre-commit run --all-files || true
	@echo "✅ Auto-fix complete!"

.PHONY: security
security: ## Run security scans
	@echo "🔒 Running security scans..."
	@echo "Checking for secrets..."
	@uvx pre-commit run detect-secrets --all-files || true
	@echo "Running Trivy scan..."
	@trivy fs . --severity HIGH,CRITICAL || echo "Trivy not installed, skipping"
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
	@uvx pre-commit autoupdate
	@echo "✅ Dependencies updated! Review changes before committing."

.PHONY: check-alerts
check-alerts: ## Check GitHub security alerts
	@echo "🔔 Checking security alerts..."
	@gh api repos/malpanez/ansible-devcontainer-vscode/code-scanning/alerts --jq '.[] | select(.state == "open") | {number: .number, severity: .rule.severity, rule: .rule.id}' || echo "gh CLI not authenticated"

.PHONY: dismiss-alerts
dismiss-alerts: ## Run alert management script (dry-run)
	@echo "🤖 Running alert management (dry-run)..."
	@DRY_RUN=true .github/scripts/manage-code-scanning-alerts.sh

.PHONY: dismiss-alerts-for-real
dismiss-alerts-for-real: ## Dismiss alerts for real (use with caution)
	@echo "⚠️  Running alert management (REAL)..."
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		DRY_RUN=false .github/scripts/manage-code-scanning-alerts.sh; \
	else \
		echo "Cancelled."; \
	fi

.PHONY: validate-yaml
validate-yaml: ## Validate all YAML files
	@echo "📝 Validating YAML files..."
	@find . -name "*.yml" -o -name "*.yaml" | grep -v ".cache" | grep -v "node_modules" | xargs yamllint -c .yamllint || true

.PHONY: validate-docker
validate-docker: ## Validate all Dockerfiles
	@echo "🐳 Validating Dockerfiles..."
	@find . -name "Dockerfile*" | xargs -I {} docker run --rm -i hadolint/hadolint < {} || true

.PHONY: ci-local
ci-local: lint security validate-yaml validate-docker ## Run full CI pipeline locally
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
