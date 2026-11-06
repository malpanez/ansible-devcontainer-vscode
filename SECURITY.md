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
- Sign published container images with Cosign (this repository signs every published digest keyless from `build-containers.yml`; `release.yml` only adds version tags to those signed digests and signs the release SBOMs) and push to GHCR from protected branches or tagged releases only.

## Verifying Published Images

Every image digest published to GHCR carries a keyless Cosign signature made
by `build-containers.yml` on `main`, only after the digest passed the scan
gate. That signature is what says a digest was published. Check it with the
exact identity, never a pattern: the promotion pull request and the nightly
also sign build attestations for candidate digests, published or not, from
`ci.yml`, and a pattern over this repository's workflows accepts those.

```bash
# Published: signed by build-containers.yml on main
cosign verify \
  --certificate-identity 'https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/build-containers.yml@refs/heads/main' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/malpanez/devcontainer-ansible:main
```

A build-provenance attestation says how and from which commit a digest was
built, not that it passed or was published. Name the repository and the
workflow that signed it, never only the owner: `--owner` accepts any of the
owner's repositories.

```bash
# Built and attested by build-containers.yml on main
gh attestation verify oci://ghcr.io/malpanez/devcontainer-ansible:main \
  --repo malpanez/ansible-devcontainer-vscode \
  --signer-workflow malpanez/ansible-devcontainer-vscode/.github/workflows/build-containers.yml@refs/heads/main

# Candidate digests, built and attested by ci.yml in the promotion pull
# request or the nightly
gh attestation verify oci://ghcr.io/malpanez/devcontainer-ansible@sha256:<digest> \
  --repo malpanez/ansible-devcontainer-vscode \
  --signer-workflow malpanez/ansible-devcontainer-vscode/.github/workflows/ci.yml
```

Tagged releases additionally attach per-image SPDX SBOMs to the GitHub
release, each with a keyless Cosign signature bundle (`.sigstore`) made by
`release.yml` for that tag:

```bash
cosign verify-blob devcontainer-ansible.spdx.json \
  --bundle devcontainer-ansible.sigstore \
  --certificate-identity 'https://github.com/malpanez/ansible-devcontainer-vscode/.github/workflows/release.yml@refs/tags/<tag>' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Operational Recommendations

- Run `./scripts/smoke-devcontainer-image.sh --stack <name> --build` locally before pushing major changes to ensure the stack still boots and the expected tooling is present.
- Review CI logs for vulnerability scan results. Address HIGH and CRITICAL findings promptly; document accepted risks in pull requests.
- If you operate in regulated environments (HIPAA, PCI-DSS, etc.), layer your organisation’s compliance controls on top of this toolkit (network isolation, audit logging, change control) and subject the resulting images to your internal assessment processes.

Thank you for helping keep this project and its users secure.
