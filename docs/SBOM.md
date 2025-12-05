# Software Bill of Materials (SBOM)

**Last Updated**: 2025-12-05

This document explains how we generate, publish, and consume SBOMs for our devcontainer images.

---

## Table of Contents

- [What is an SBOM?](#what-is-an-sbom)
- [Why We Generate SBOMs](#why-we-generate-sboms)
- [How We Generate SBOMs](#how-we-generate-sboms)
- [Accessing SBOMs](#accessing-sboms)
- [Verifying SBOMs](#verifying-sboms)
- [SBOM Contents](#sbom-contents)
- [Security Scanning with SBOMs](#security-scanning-with-sboms)

---

## What is an SBOM?

A **Software Bill of Materials (SBOM)** is a formal, machine-readable inventory of all components, libraries, and dependencies in a software artifact.

Think of it like an ingredient list on food packaging - it tells you exactly what's inside.

### Standards

We generate SBOMs in **SPDX format** (Software Package Data Exchange), an ISO standard (ISO/IEC 5962:2021) supported by:
- US Executive Order 14028 (cybersecurity)
- Linux Foundation
- CISA (Cybersecurity & Infrastructure Security Agency)

---

## Why We Generate SBOMs

### 1. Supply Chain Security

SBOMs enable:
- **Vulnerability tracking**: Know exactly which package versions are installed
- **License compliance**: Identify all open-source licenses in use
- **Dependency auditing**: Track transitive dependencies
- **Incident response**: Quickly identify affected systems when vulnerabilities are disclosed

### 2. Transparency

Users can:
- Verify what's in our images before using them
- Assess security posture
- Meet their own compliance requirements
- Make informed decisions about adopting our devcontainers

### 3. Industry Best Practice

Elite open-source projects provide SBOMs:
- Kubernetes
- Docker Official Images
- GitHub Actions runners
- Chainguard Images

---

## How We Generate SBOMs

### Automatic Generation

SBOMs are automatically generated during the container build process in our CI/CD pipeline.

**Workflow**: [.github/workflows/ci.yml](../.github/workflows/ci.yml)

```yaml
- name: Build and push base
  uses: docker/build-push-action@v6
  with:
    sbom: true        # Generate SBOM
    provenance: true  # Generate provenance attestation
    push: true
```

This uses **BuildKit** with the SBOM generator plugin to create:
1. **SBOM document** in SPDX JSON format
2. **Provenance attestation** (who built it, when, from what source)

Both are:
- Signed with GitHub's Sigstore
- Attached to the container image
- Stored in GitHub Container Registry (GHCR)

### Tools Used

- **BuildKit SBOM Generator**: Built into Docker Buildx
- **Syft** (via BuildKit): Scans container layers for packages
- **Sigstore**: Signs SBOMs and attestations

---

## Accessing SBOMs

### Method 1: Docker CLI (Recommended)

```bash
# Pull the image
docker pull ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest

# View SBOM
docker buildx imagetools inspect \
  ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest \
  --format '{{ json .SBOM }}'
```

### Method 2: GitHub Container Registry UI

1. Navigate to [Packages](https://github.com/malpanez?tab=packages&repo_name=ansible-devcontainer-vscode)
2. Select the devcontainer image
3. Click "Attestations" tab
4. View SBOM and provenance

### Method 3: cosign (CLI Tool)

```bash
# Install cosign
brew install cosign  # macOS
# or: apt-get install cosign  # Debian/Ubuntu

# Download SBOM
cosign download sbom \
  ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest \
  > sbom.spdx.json

# Pretty-print
jq . sbom.spdx.json
```

### Method 4: syft (Local Generation)

Generate SBOM locally for testing:

```bash
# Install syft
brew install syft  # macOS
# or: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh

# Generate SBOM from local image
syft ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest \
  -o spdx-json > sbom.spdx.json

# Or from Dockerfile directory
syft dir:devcontainers/ansible -o spdx-json
```

---

## Verifying SBOMs

### Verify Signature

SBOMs are signed with Sigstore (keyless signing):

```bash
# Install cosign
brew install cosign

# Verify SBOM signature
cosign verify \
  --certificate-identity-regexp 'https://github.com/malpanez/ansible-devcontainer-vscode' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest
```

### Verify Provenance

Check where and how the image was built:

```bash
cosign verify-attestation \
  --type slsaprovenance \
  --certificate-identity-regexp 'https://github.com/malpanez/ansible-devcontainer-vscode' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest
```

---

## SBOM Contents

### Example SBOM Structure

```json
{
  "SPDXID": "SPDXRef-DOCUMENT",
  "spdxVersion": "SPDX-2.3",
  "name": "devcontainer-ansible",
  "packages": [
    {
      "SPDXID": "SPDXRef-Package-python",
      "name": "python",
      "versionInfo": "3.12.7",
      "licenseConcluded": "PSF-2.0",
      "supplier": "Organization: Python Software Foundation"
    },
    {
      "SPDXID": "SPDXRef-Package-ansible-core",
      "name": "ansible-core",
      "versionInfo": "2.17.6",
      "licenseConcluded": "GPL-3.0-or-later",
      "supplier": "Organization: Red Hat"
    }
    // ... hundreds more packages
  ]
}
```

### Package Information Included

For each component:
- **Name** and **version**
- **License** (SPDX identifier)
- **Supplier** (organization or person)
- **Checksums** (SHA256, SHA1)
- **Dependencies** (relationships between packages)
- **Locations** (file paths in container)

### Stacks Covered

We generate SBOMs for all devcontainer stacks:
- **ansible**: Python packages, Ansible collections, system packages
- **terraform**: Terraform, Terragrunt, TFLint binaries
- **golang**: Go standard library, compiled binaries
- **latex**: Tectonic, system fonts, Perl packages

---

## Security Scanning with SBOMs

### Grype (Vulnerability Scanner)

Use the SBOM to scan for vulnerabilities without pulling the image:

```bash
# Install grype
brew install grype

# Scan using SBOM
grype sbom:./sbom.spdx.json

# Or scan image directly (grype generates SBOM internally)
grype ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest
```

**Example output:**
```
NAME               INSTALLED  FIXED-IN  TYPE  VULNERABILITY  SEVERITY
urllib3            1.26.16    1.26.17   pypi  CVE-2023-43804 HIGH
setuptools         65.5.1     70.0.0    pypi  CVE-2024-6345  CRITICAL
```

### Trivy (Comprehensive Scanner)

```bash
# Install trivy
brew install trivy

# Scan using SBOM
trivy sbom ./sbom.spdx.json

# Or scan image (includes SBOM, config, secrets)
trivy image ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest
```

### OSV-Scanner (Open Source Vulnerabilities)

```bash
# Install osv-scanner
go install github.com/google/osv-scanner/cmd/osv-scanner@latest

# Scan SBOM
osv-scanner --sbom=sbom.spdx.json
```

---

## CI/CD Integration

### Automated Scanning

Our CI pipeline scans all images on every build:

```yaml
# .github/workflows/ci.yml
- name: Scan with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: devcontainer-${{ matrix.stack }}:ci
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'

- name: Upload to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: 'trivy-results.sarif'
```

Vulnerabilities appear in:
- GitHub Security tab
- Pull request checks
- Dependabot alerts (for base images)

---

## Best Practices

### For Users

1. **Always verify signatures** before using images in production
2. **Scan SBOMs regularly** for new vulnerabilities (CVEs are disclosed continuously)
3. **Check license compliance** if using in commercial products
4. **Pin image SHAs** instead of tags for reproducibility

### For Contributors

1. **Minimize dependencies**: Only include necessary packages
2. **Keep base images updated**: Use latest stable versions
3. **Document custom software**: Add to SBOM if manually installed
4. **Review security scan results**: Fix high/critical vulnerabilities before merge

---

## Compliance & Standards

### Supported Formats

- ✅ **SPDX 2.3** (ISO/IEC 5962:2021) - Primary format
- ✅ **CycloneDX** (via conversion tools)
- ✅ **SARIF** (for security findings)

### Regulatory Alignment

- ✅ **US Executive Order 14028** (May 2021) - Software supply chain security
- ✅ **NIST SP 800-218** - Secure Software Development Framework
- ✅ **CISA Guidelines** - SBOM minimum elements
- ✅ **OpenSSF Best Practices** - Supply chain security

---

## Tools Reference

| Tool | Purpose | Installation |
|------|---------|--------------|
| [cosign](https://github.com/sigstore/cosign) | Verify signatures | `brew install cosign` |
| [syft](https://github.com/anchore/syft) | Generate SBOMs | `brew install syft` |
| [grype](https://github.com/anchore/grype) | Scan vulnerabilities | `brew install grype` |
| [trivy](https://github.com/aquasecurity/trivy) | Comprehensive scanner | `brew install trivy` |
| [osv-scanner](https://github.com/google/osv-scanner) | OSV database scanner | `go install ...` |
| [sbom-tool](https://github.com/microsoft/sbom-tool) | Microsoft SBOM tool | `dotnet tool install ...` |

---

## Examples

### Complete Verification Workflow

```bash
#!/bin/bash
# verify-image.sh - Complete SBOM verification workflow

IMAGE="ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest"

echo "1. Verifying image signature..."
cosign verify \
  --certificate-identity-regexp 'https://github.com/malpanez/ansible-devcontainer-vscode' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  "$IMAGE"

echo "2. Downloading SBOM..."
cosign download sbom "$IMAGE" > sbom.spdx.json

echo "3. Scanning for vulnerabilities..."
grype sbom:./sbom.spdx.json --only-fixed

echo "4. Checking licenses..."
syft sbom:./sbom.spdx.json -o json | jq -r '.artifacts[].licenses[] | .value' | sort -u

echo "✅ Verification complete!"
```

### Find Specific Package

```bash
# Find if a specific package is in the image
syft ghcr.io/malpanez/ansible-devcontainer-vscode/devcontainer-ansible:latest \
  -o json | jq '.artifacts[] | select(.name == "ansible-core")'
```

### License Compliance Check

```bash
# List all licenses
syft sbom:./sbom.spdx.json -o json | \
  jq -r '.artifacts[].licenses[] | .value' | \
  sort | uniq -c | sort -rn
```

---

## Related Documentation

- [SECURITY.md](../SECURITY.md) - Security policy and vulnerability reporting
- [ARCHITECTURE.md](ARCHITECTURE.md) - Container build architecture
- [docs/OSSF_SCORECARD_PROGRESS.md](OSSF_SCORECARD_PROGRESS.md) - Supply chain security scorecard

---

## References

- [SPDX Specification](https://spdx.dev/specifications/)
- [NTIA Minimum Elements for SBOM](https://www.ntia.gov/files/ntia/publications/sbom_minimum_elements_report.pdf)
- [CISA SBOM Sharing Lifecycle Report](https://www.cisa.gov/sbom)
- [Sigstore Documentation](https://docs.sigstore.dev/)
- [Docker BuildKit SBOM](https://docs.docker.com/build/metadata/attestations/sbom/)

---

**Questions about SBOMs?** Open an issue or see [CONTRIBUTING.md](CONTRIBUTING.md).
