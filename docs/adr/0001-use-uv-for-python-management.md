# ADR-0001: Use uv for Python Package Management

**Status**: Accepted
**Date**: 2024-11-15
**Deciders**: @malpanez
**Tags**: tooling, performance, dependencies

---

## Context

The Ansible devcontainer stack requires fast, reliable Python package management for:
- Installing Ansible and related tools
- Managing test dependencies (pytest, molecule, ansible-lint)
- Supporting rapid development iterations
- Ensuring reproducible builds across environments

Traditional tools like `pip` and `poetry` have known limitations:
- **pip**: Slow dependency resolution, no proper lockfiles, inconsistent behavior
- **poetry**: Better lockfiles but significantly slower than needed for CI/CD
- **pipenv**: Deprecated, slow, poor Windows support

The devcontainer needs to install 20+ Python packages quickly and reliably on every build.

---

## Decision

Adopt **`uv`** (https://github.com/astral-sh/uv) as the primary Python package manager for all Python-based devcontainer stacks.

Use `pyproject.toml` for dependency declaration and `uv.lock` for lockfile management.

---

## Rationale

### Speed
- **10-100x faster** than pip for dependency installation
- Rust-based implementation provides native performance
- Parallel downloads and caching significantly reduce build times

### Reliability
- Proper lockfile support (`uv.lock`) ensures reproducible installs
- Better dependency resolution algorithm than pip
- Cross-platform consistency (Windows, macOS, Linux)

### Modern Standards
- Native `pyproject.toml` support (PEP 621 compliant)
- Compatible with existing pip workflows
- Growing adoption in Python community (10k+ stars on GitHub)

### Developer Experience
- Simple commands: `uv pip install`, `uv pip sync`, `uv lock`
- Drop-in replacement for pip (minimal learning curve)
- Excellent error messages and diagnostics

---

## Consequences

### Positive

- ✅ **Faster CI builds**: Container builds reduced from 8min to 3min 45s
- ✅ **Reproducible environments**: `uv.lock` guarantees consistent versions
- ✅ **Better caching**: Named volumes for uv cache persist across rebuilds
- ✅ **Cross-platform consistency**: Same behavior on all operating systems
- ✅ **Future-proof**: Modern tool with active development and community support

### Negative

- ⚠️ **Newer ecosystem**: Less mature than pip (released 2023)
- ⚠️ **Learning curve**: Team needs to learn uv-specific commands
- ⚠️ **Documentation gaps**: Some edge cases less documented than pip

### Neutral

- ℹ️ Requires uv installation in all devcontainers (added to base image)
- ℹ️ Need to maintain both `pyproject.toml` and `uv.lock` in version control
- ℹ️ Contributors unfamiliar with uv may default to pip commands

---

## Alternatives Considered

### Alternative 1: pip + pip-tools

**Pros:**
- Most widely known and used
- Extensive documentation and community support
- Built into Python (no extra installation)

**Cons:**
- Significantly slower (5-10x compared to uv)
- Dependency resolution often fails or is incorrect
- No proper lockfile support (pip-tools adds complexity)
- Poor caching behavior in containers

**Why rejected:** Speed is critical for devcontainer rebuild cycles. pip's slow performance and unreliable dependency resolution outweigh its familiarity.

### Alternative 2: Poetry

**Pros:**
- Excellent lockfile support (`poetry.lock`)
- Good dependency resolution
- Professional packaging features
- Large community adoption

**Cons:**
- **Extremely slow** for CI/CD (3-5x slower than pip, 30x slower than uv)
- Heavyweight (200MB+ installation)
- Virtual environment management conflicts with devcontainer patterns
- Complex configuration (`pyproject.toml` + `poetry.lock` + `.toml` settings)

**Why rejected:** Poetry's slow performance makes it unsuitable for rapid devcontainer iterations. Build times were unacceptable in testing (8+ minutes vs 3.5 minutes with uv).

### Alternative 3: Pipenv

**Pros:**
- Official Python.org recommendation (historically)
- Combined `Pipfile` and `Pipfile.lock`

**Cons:**
- **Officially deprecated** and no longer actively maintained
- Extremely slow dependency resolution
- Poor Windows support
- Abandoned by maintainers

**Why rejected:** Deprecated status makes it a non-starter.

### Alternative 4: PDM

**Pros:**
- Modern PEP 582 support
- Fast dependency resolution
- Good lockfile support

**Cons:**
- Smaller community than poetry or pip
- Less battle-tested in production
- PEP 582 adoption uncertain
- More complex than needed for our use case

**Why rejected:** While PDM is promising, uv provides better performance and simpler workflows for our specific use case.

---

## Implementation Notes

### Installation in Devcontainer

Add to `Dockerfile`:
```dockerfile
# Install uv (standalone installer, no pip needed)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH
ENV PATH="/root/.cargo/bin:$PATH"
```

### Usage Patterns

```bash
# Install dependencies from pyproject.toml
uv pip install --system -e .

# Lock dependencies
uv lock

# Sync from lockfile (CI/reproducible builds)
uv pip sync --system uv.lock

# Update specific package
uv pip install --upgrade ansible-lint
uv lock
```

### Named Volume for Cache

```json
{
  "mounts": [
    "source=uv-cache,target=/root/.cache/uv,type=volume"
  ]
}
```

This persists the uv cache across container rebuilds for even faster installs.

---

## References

- [uv Documentation](https://github.com/astral-sh/uv)
- [PEP 621 - pyproject.toml specification](https://peps.python.org/pep-0621/)
- [Performance Benchmarks](../PERFORMANCE.md#python-dependencies)
- [Python Package Manager Comparison (2024)](https://lincolnloop.com/insights/python-package-managers-2024/)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2024-11-15 | @malpanez | Created ADR based on uv adoption decision |
| 2024-12-04 | @malpanez | Added performance metrics and updated status |
