# Contributing to Ansible DevContainer VSCode

Thank you for considering contributing to this project! This guide will help you get started.

## 🎯 Project Vision

This project aims to provide **TOP 0.1%** DevContainer environments for Infrastructure as Code development. We prioritize:

- **Security First**: All changes must pass security scans
- **Developer Experience**: Fast, reliable, and well-documented
- **Automation**: CI/CD for everything
- **Quality**: Enterprise-grade code standards

## 🚀 Getting Started

### Prerequisites

- Docker Desktop or compatible container runtime
- VS Code with Dev Containers extension
- Git
- (Optional) GitHub CLI (`gh`)

### Setup

1. **Fork and Clone**
   ```bash
   gh repo fork malpanez/ansible-devcontainer-vscode --clone
   cd ansible-devcontainer-vscode
   ```

2. **Open in DevContainer**
   ```bash
   code .
   # Select "Reopen in Container" when prompted
   ```

3. **Install Pre-commit Hooks**
   ```bash
   make setup
   # or manually:
   uvx pre-commit install --install-hooks
   ```

## 📝 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-awesome-feature
# or
git checkout -b fix/bug-description
```

**Branch Naming Convention**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `chore/` - Maintenance tasks
- `refactor/` - Code refactoring

### 2. Make Changes

- Follow existing code style
- Add tests for new functionality
- Update documentation as needed
- Run linters locally: `make lint`

### 3. Test Your Changes

```bash
# Run full CI locally
make ci-local

# Or run specific checks
make lint        # Linting
make security    # Security scans
make test        # Tests
```

### 4. Commit Your Changes

We use **Conventional Commits** format:

```bash
git commit -m "feat: add support for new tool X"
git commit -m "fix: resolve issue with Y"
git commit -m "docs: update README with Z"
```

**Commit Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code restructuring
- `test:` - Test changes
- `chore:` - Maintenance
- `ci:` - CI/CD changes
- `perf:` - Performance improvements

### 5. Push and Create PR

```bash
git push origin feature/my-awesome-feature
gh pr create --fill
```

## 🎨 Code Style

### Python
- Use `ruff` for linting and formatting
- Max line length: 120 characters
- Follow PEP 8

### YAML
- 2 spaces indentation
- Use `yamllint` configuration
- Quote strings when ambiguous

### Terraform
- Use `terraform fmt`
- Follow HashiCorp style guide

### Shell Scripts
- Use ShellCheck
- Prefer `bash` over `sh`
- Add error handling (`set -euo pipefail`)

### Dockerfiles
- Use `hadolint`
- Multi-stage builds preferred
- Pin versions with comments for Renovate

## 🧪 Testing

### Docker Images
```bash
# Build locally
make build

# Test manually
docker run --rm -it devcontainer-terraform:local bash
```

### Workflows
- Test workflow changes in a fork first
- Use `act` for local testing (optional)

## 🔒 Security

### Before Committing
- **Never commit secrets** - Use `.secrets.baseline`
- Run `make security` to scan
- Pre-commit hooks will catch common issues

### Reporting Security Issues
- **DO NOT** open public issues for security vulnerabilities
- Email: alpanez.alcalde@gmail.com
- Include detailed description and steps to reproduce

## 📖 Documentation

### What to Document
- New features require documentation updates
- Breaking changes need migration guides
- Complex logic needs inline comments

### Where to Document
- `README.md` - Project overview and quick start
- `docs/` - Detailed guides
- Inline comments - Complex code logic
- SECURITY.md - Security-related information

## ✅ Pull Request Guidelines

### Before Submitting
- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] Documentation is updated
- [ ] Commits follow conventional commits
- [ ] Pre-commit hooks pass
- [ ] No merge conflicts with `develop`

### PR Description
Use the PR template to provide:
- Clear description of changes
- Related issues (Fixes #123)
- Testing performed
- Screenshots (if applicable)

### Review Process
1. Automated CI checks must pass
2. At least 1 approval required
3. All conversations resolved
4. No merge conflicts

## 🐛 Bug Reports

Use the Bug Report template and include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs

## ✨ Feature Requests

Use the Feature Request template and include:
- Problem statement
- Proposed solution
- Alternatives considered
- Priority level

## 🏷️ Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Documentation improvements
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed
- `security` - Security-related
- `dependencies` - Dependency updates

## 📚 Additional Resources

- [Development Guide](docs/DEVELOPMENT.md)
- [Security Policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## 💬 Questions?

- Open a [Discussion](https://github.com/malpanez/ansible-devcontainer-vscode/discussions)
- Check existing issues
- Review documentation

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.

---

**Thank you for contributing to making this the TOP 0.1% DevContainer project!** 🚀
