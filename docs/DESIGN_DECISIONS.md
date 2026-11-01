# Design Decisions

### Why not Microsoft's devcontainer images?

Microsoft's universal images ship tools for every possible use case. That's convenient but you pay for it every time you pull.

| Stack            | These images | Microsoft devcontainers | Difference |
| ---------------- | ------------ | ----------------------- | ---------- |
| Ansible / Python | 436 MiB      | ~1.8 GB                 | **≈ –75 %** |
| Terraform        | 669 MiB      | ~1.5 GB                 | **≈ –53 %** |
| Golang           | 376 MiB      | ~1.4 GB                 | **≈ –72 %** |

The sizes here are the uncompressed `linux/amd64` figures CI measures (`.github/image-size-budgets.json` holds the limits it enforces). The Microsoft figures were not re-measured; the percentages convert MiB to MB first.

Each image here includes only what the stack actually needs — a pinned toolchain, `uv` for Python, and nothing else. Pre-built on GHCR so VS Code pulls them directly; no local build step.

A daily CI run (`build-containers.yml`) rebuilds every image from scratch, so OS-level security patches land automatically even when the repository is quiet.

### AI agents inside devcontainers

Giving an AI agent (Claude Code, Copilot, Cursor, etc.) broad file-system and shell permissions on your laptop is a real risk. The same agent running inside a devcontainer has a naturally bounded blast radius:

- **Host OS is untouched** — the agent can only affect the mounted workspace
- **Recovery is trivial** — `git reset --hard` + rebuild restores the full environment in seconds
- **Credentials stay isolated** — only what you explicitly mount is visible
- **Audit trail is git** — every change the agent makes is tracked and reversible

The devcontainer is not just a development convenience. For AI-assisted workflows, it is a safe execution sandbox.


### Why not distroless or Alpine?

Dev Containers are interactive workstations: developers expect `bash`, package managers, and diagnostics tooling to be available. Distroless or scratch images deliberately omit those layers, which makes them great for production workloads but painful for day-to-day debugging. Alpine’s `musl` libc often breaks prebuilt Python wheels and forces slow source builds—exactly what we are trying to avoid when bootstrapping Ansible or `pre-commit`—so the Python stacks stay on slim Debian (`python:*-slim-trixie`). The Go stack is the exception because it only needs the Go toolchain and busybox utilities, so `golang:1.27-alpine3.23` keeps it lightweight.

That exception has a cost. VS Code's [Linux requirements](https://code.visualstudio.com/docs/remote/linux) support Alpine only as "Alpine Linux 64-bit x86 containers or WSL hosts (3.16+)", for Dev Containers and WSL, and warn that "Extensions installed in the container may not work due to `glibc` dependencies in extension native code." They mark AArch64 as "preview". `devcontainer-golang` is nevertheless published for `linux/amd64` and `linux/arm64`, so on an arm64 host it runs outside what VS Code lists as supported for Alpine; if an extension fails there, use a Debian-based stack.
