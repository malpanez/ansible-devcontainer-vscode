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
- Pin dependency versions (Python, Go, Terraform, etc.) to avoid unexpected upgrades. Re-run the security scans in CI (`hadolint`, `grype`) after any bump.
- Sign published container images with Cosign (this repository signs every published digest keyless from `build-containers.yml` and `release.yml`) and push to GHCR from protected branches or tagged releases only.

## Verifying Published Images

Every image digest published to GHCR carries a keyless Cosign signature and a
GitHub build-provenance attestation. To verify before use:

```bash
# Cosign signature (keyless, Fulcio certificate tied to the publishing workflow)
cosign verify \
  --certificate-identity-regexp 'https://github.com/malpanez/ansible-devcontainer-vscode/\.github/workflows/.+' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/malpanez/devcontainer-ansible:main

# Build provenance attestation (SLSA)
gh attestation verify oci://ghcr.io/malpanez/devcontainer-ansible:main \
  --owner malpanez
```

Tagged releases additionally attach per-image SPDX SBOMs to the GitHub
release, each with a detached Cosign signature (`.sig`) and certificate
(`.pem`):

```bash
cosign verify-blob devcontainer-ansible.spdx.json \
  --signature devcontainer-ansible.spdx.json.sig \
  --certificate devcontainer-ansible.spdx.json.pem \
  --certificate-identity-regexp 'https://github.com/malpanez/ansible-devcontainer-vscode/\.github/workflows/.+' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Operational Recommendations

- Run `./scripts/smoke-devcontainer-image.sh --stack <name> --build` locally before pushing major changes to ensure the stack still boots and the expected tooling is present.
- Review CI logs for vulnerability scan results. Address HIGH and CRITICAL findings promptly; document accepted risks in pull requests.
- If you operate in regulated environments (HIPAA, PCI-DSS, etc.), layer your organisation’s compliance controls on top of this toolkit (network isolation, audit logging, change control) and subject the resulting images to your internal assessment processes.

Thank you for helping keep this project and its users secure.
