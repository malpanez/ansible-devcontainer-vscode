# Design Decisions

### Why not Microsoft's devcontainer images?

Microsoft's universal images ship tools for every possible use case. That's convenient but you pay for it every time you pull.

| Stack            | These images | Microsoft devcontainers | Difference |
| ---------------- | ------------ | ----------------------- | ---------- |
| Ansible / Python | ~650 MB      | ~1.8 GB                 | **–64 %**  |
| Terraform        | ~240 MB      | ~1.5 GB                 | **–84 %**  |
| Golang           | ~210 MB      | ~1.4 GB                 | **–85 %**  |

Each image here includes only what the stack actually needs — a pinned toolchain, `uv` for Python, and nothing else. Pre-built on GHCR so VS Code pulls them directly; no local build step.

A weekly CI run rebuilds every image from scratch, so OS-level security patches land automatically even when the repository is quiet.

### AI agents inside devcontainers

Giving an AI agent (Claude Code, Copilot, Cursor, etc.) broad file-system and shell permissions on your laptop is a real risk. The same agent running inside a devcontainer has a naturally bounded blast radius:

- **Host OS is untouched** — the agent can only affect the mounted workspace
- **Recovery is trivial** — `git reset --hard` + rebuild restores the full environment in seconds
- **Credentials stay isolated** — only what you explicitly mount is visible
- **Audit trail is git** — every change the agent makes is tracked and reversible

The devcontainer is not just a development convenience. For AI-assisted workflows, it is a safe execution sandbox.


### Why not distroless or Alpine?

Dev Containers are interactive workstations: developers expect `bash`, package managers, `sudo`, and diagnostics tooling to be available. Distroless or scratch images deliberately omit those layers, which makes them great for production workloads but painful for day-to-day debugging. Alpine’s `musl` libc often breaks prebuilt Python wheels and forces slow source builds—exactly what we are trying to avoid when bootstrapping Ansible or `pre-commit`—so the Python stacks stay on slim Debian / Wolfi bases. The Go stack is the exception because it only needs the Go toolchain and busybox utilities, so `golang:1.23-alpine` keeps it lightweight without impacting DX.
