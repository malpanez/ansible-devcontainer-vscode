# Security Policy

We take the security of this project seriously. The repository bundles tooling for infrastructure automation, so supply-chain and secrets hygiene are critical for anyone adopting it.

## Reporting a Vulnerability

If you discover a security issue:

1. **Do not** open a public issue.
2. Email the maintainer at `alpanez.alcalde@gmail.com` with:
   - A detailed description of the problem.
   - Steps to reproduce and the scope of impact.
   - Any known mitigations or workarounds.
3. Expect an acknowledgement within 3 business days. If you do not receive a response, please resend the report.

We will coordinate on a fix, publish patches, and disclose responsibly once mitigations are available.

## Supported Versions

We support the latest tagged release and the `main` branch. Older tags may remain available on GHCR for reproducibility, but they will not receive security fixes.

## Handling Secrets

- Do not commit secrets to the repository. Use `.secrets.baseline` and `pre-commit` hooks to detect accidental leaks.
- For local development, store secrets in secure managers (1Password, Bitwarden, Vault) and inject them via environment variables or external files mounted into the devcontainer.
- When mirroring dependencies (PyPI, npm, container registries) through corporate proxies, never bake credentials into Dockerfiles; rely on runtime configuration (`remoteEnv`, secret mounts) instead.

## Supply-Chain Expectations

- All third-party binaries should be fetched over HTTPS with checksum validation. Multi-architecture builds must verify the checksum that matches the target platform.
- Pin dependency versions (Python, Go, Terraform, etc.) to avoid unexpected upgrades. Re-run the security scans in CI (`hadolint`, `trivy`) after any bump.
- Sign published container images with Cosign (this repository uses keyless signing in `release.yml`) and push to GHCR from protected branches or tagged releases only.

## Operational Recommendations

- Run `./scripts/smoke-devcontainer-image.sh --stack <name> --build` locally before pushing major changes to ensure the stack still boots and the expected tooling is present.
- Review CI logs for vulnerability scan results. Address HIGH and CRITICAL findings promptly; document accepted risks in pull requests.
- If you operate in regulated environments (HIPAA, PCI-DSS, etc.), layer your organisation’s compliance controls on top of this toolkit (network isolation, audit logging, change control) and subject the resulting images to your internal assessment processes.

Thank you for helping keep this project and its users secure.
