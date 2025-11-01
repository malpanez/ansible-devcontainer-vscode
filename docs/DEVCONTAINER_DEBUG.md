# Dev Container Debugging Guide

Use these scripts when a Dev Container fails to build or behaves differently between contributors.

## 1. Build every template locally

```bash
./scripts/check-devcontainer.sh
```

Runs `devcontainer build` for each stack (`ansible`, `golang`, `latex`, `terraform`). Pass extra arguments to forward build flags, e.g. `--no-cache`.

The helper also normalises BuildKit cache mounts (APT, pip) so repeated runs do not corrupt the Dockerfiles—helpful if a previous manual edit introduced invalid mount syntax.

Python tooling (ansible-lint, Checkov) now installs during the devcontainer `postCreateCommand` via `sudo uv pip install --system ...`. When reproducing issues outside VS Code, run those commands manually inside the container after it starts.

## 2. Launch an interactive debug session

```bash
./scripts/debug-devcontainer.sh --stack latex -- ./scripts/run-smoke-tests.sh
```

The script:
1. Builds the selected template with the Dev Containers CLI.
2. Starts the container (`devcontainer up`).
3. Runs the provided command (or opens a shell if omitted).

For the LaTeX stack, use `-b LATEX_DISTRO=texlive` to override build args while testing toggles. Swap `--stack` to `ansible`, `golang`, or `terraform` to target other templates.

## 3. Validate template metadata

```bash
./scripts/devcontainer-metadata.py
```

Checks `.devcontainer/.template-metadata.json` to ensure the stack and checksum match the template under `devcontainers/`. Exit code `0` means everything matches; exit code `2` signals drift.

## 4. Inspect differences

```bash
./scripts/devcontainer-diff.py
```

Compares `.devcontainer/` files with the template and prints unified diffs for changed files, plus additions/removals. Pair with the metadata check to understand why a copy occurred.

## 5. Reproduce CI (Podman)

```bash
DEVCONTAINER_CONTAINER_ENGINE=podman ./scripts/check-devcontainer.sh
```

Matches the GitHub Actions Podman job. Ensure `podman system service --time=0 tcp:127.0.0.1:8080 &` is running or use Podman Desktop on Windows.
