# Security Review - Análisis Completo del Repositorio

**Fecha**: 2025-12-05
**Revisor**: Claude Code
**Repositorio**: malpanez/ansible-devcontainer-vscode

---

## 1. OSSF Scorecard - Análisis de Resultados

### Estado Actual: 4.9/10

El repositorio tiene un score razonable pero hay áreas críticas de mejora:

#### ✅ Áreas Bien Implementadas (Score Alto/Medio)

1. **Binary-Artifacts (10/10)** - No hay binarios comprometidos en el repo
2. **Vulnerabilities (10/10)** - Security advisories habilitados
3. **Security-Policy (10/10)** - Excelente [SECURITY.md](SECURITY.md) presente
4. **License (10/10)** - Licencia definida
5. **CI-Tests (10/10)** - Tests automatizados en CI
6. **Contributors (3/10)** - Bajo pero aceptable para proyecto personal

#### ❌ Áreas Críticas que Requieren Atención Inmediata

1. **Maintained (0/10)** - HIGH PRIORITY
   - **Problema**: El proyecto no muestra actividad de mantenimiento constante
   - **Impacto**: Dependabot alerts no se resuelven, issues no se responden
   - **Recomendación**:
     - Establecer revisión semanal de dependencias
     - Responder issues en <7 días
     - Actualizar README con estado de mantenimiento

2. **Code-Review (0/10)** - HIGH PRIORITY
   - **Problema**: No hay revisión de código requerida antes de merge
   - **Impacto**: Código potencialmente inseguro puede pasar directo a main
   - **Recomendación**:
     - Habilitar branch protection en main/develop
     - Requerir al menos 1 revisor antes de merge
     - Ver solución detallada abajo

3. **Dependency-Update-Tool (0/10)** - HIGH PRIORITY
   - **Problema**: Dependabot no está habilitado correctamente
   - **Impacto**: Vulnerabilidades conocidas no se detectan automáticamente
   - **Recomendación**: Crear [.github/dependabot.yml](.github/dependabot.yml)

4. **Fuzzing (0/10)** - MEDIUM (informational)
   - No hay fuzzing implementado
   - Para este proyecto (devcontainer) no es crítico
   - Considerar en el futuro si se exponen APIs

5. **Pinned-Dependencies (5/10)** - MEDIUM
   - **Problema**: Algunas dependencias no están pinneadas con hash
   - **Impacto**: Posible supply chain attack
   - **Status**: Parcialmente implementado (GitHub Actions ya usan SHA256)
   - **Acción**: Revisar requirements.txt y ansible collections

6. **SAST (10/10)** - MEDIUM
   - **Problema**: Trivy habilitado pero hay 38 alertas abiertas
   - **Impacto**: Vulnerabilidades conocidas en binarios vendor
   - **Acción**: Ver sección "Security Issues" abajo

7. **Dangerous-Workflow (?)** - CRITICAL
   - **Problema**: Workflows con permisos write no están adecuadamente protegidos
   - **Impacto**: Posible token exfiltration o code injection
   - **Archivos**: [sync-main-to-develop.yml](.github/workflows/sync-main-to-develop.yml#L79)
   - **Recomendación**: Ver análisis detallado abajo

8. **Token-Permissions (?)** - HIGH
   - Algunos workflows no siguen principio de least privilege
   - Ver análisis por workflow abajo

9. **Branch-Protection (?)** - CRITICAL
   - **Email en workflow falló**: El workflow no tiene jobs, por lo que no se ejecutó
   - **Problema**: [sync-main-to-develop.yml](.github/workflows/sync-main-to-develop.yml) línea 24 tiene condición que impide ejecución
   - **Fix**: Revisar lógica del if condition

10. **Signed-Releases (0/10)** - HIGH
    - Los releases no están firmados criptográficamente
    - Aunque usas attestations en [ci.yml](.github/workflows/ci.yml#L629), los git tags no están firmados
    - Recomendación: Habilitar GPG signing para releases

11. **Packaging (0/10)** - MEDIUM (informational)
    - El proyecto no está publicado en package manager
    - No es crítico para devcontainer project

---

## 2. Security Issues - Análisis de 38 Alertas

### Contexto
El repositorio tiene **38 alertas de code scanning abiertas** según OSSF Scorecard. Estas están relacionadas principalmente con:

1. **CVEs en binarios vendor** (Podman, Terraform, Terragrunt, TFLint, Age, SOPS)
2. **Go stdlib vulnerabilities** en dependencias transitivas
3. **Trivy false positives** por detection de versiones en binarios

### Estrategia de Mitigación

Ya tienes un excelente script automatizado: [.github/scripts/manage-code-scanning-alerts.sh](.github/scripts/manage-code-scanning-alerts.sh)

#### Recomendaciones Específicas:

1. **Ejecutar el script periódicamente**
   - El workflow [security-alert-management.yml](.github/workflows/security-alert-management.yml) ya está configurado
   - Verificar que está ejecutándose correctamente los lunes

2. **Categorías de Dismissal Válidas**:

   a) **Stale alerts** (>90 días): Auto-dismiss como "won't fix"

   b) **Podman false positives**:
      - Tu Dockerfile usa v5.7.0 pero Trivy detecta versiones antiguas
      - Esto es un problema conocido de detección de versiones
      - Script ya tiene lógica para esto (líneas 135-151)

   c) **Go stdlib CVEs en vendor binaries**:
      - CVEs 2024-45336, 2024-45341, 2025-series en x/crypto, x/net
      - Estos están en binarios pre-compilados de:
        - age/age-keygen
        - sops
        - terragrunt
        - terraform
        - tflint
        - podman
      - **Impacto**: LOW (desarrollo only, no producción)
      - **Mitigación**: Esperar updates upstream, revisar quarterly
      - Script ya tiene lógica (líneas 176-188)

3. **Acciones Inmediatas**:

   ```bash
   # Ejecutar el script en dry-run para ver qué se dismissiría
   DRY_RUN=true MAX_ALERT_AGE_DAYS=90 \
     .github/scripts/manage-code-scanning-alerts.sh

   # Si todo se ve bien, ejecutar en modo real
   DRY_RUN=false MAX_ALERT_AGE_DAYS=90 \
     .github/scripts/manage-code-scanning-alerts.sh
   ```

4. **Documentar Risk Acceptance**:
   - Los CVEs en vendor binaries son riesgo aceptado para dev env
   - Ya está documentado en [SECURITY.md](SECURITY.md#L30-L32)
   - Script añade comentarios automáticos con justificación

### Vulnerabilities específicas a revisar:

**Podman CVEs** (según tu script):
- CVE-2024-1753: Fixed in 5.0.1
- CVE-2024-9407: Fixed in 5.2.4
- CVE-2025-6032: Fixed in 5.5.2
- CVE-2025-9566: Fixed in 5.6.1
- CVE-2025-47914, CVE-2025-58181: golang.org/x/crypto

**Go stdlib CVEs** (según script líneas 177-181):
- CVE-2025-58181, 47914, 61725, 61724, 61723, 58185-58189, 47912, 52881
- CVE-2025-47910, 0913, 22866, 22869, 22871, 4673, 47906-47907, 46394
- CVE-2024-45336, 45341

**Acción**: Todos estos pueden ser dismissed según tu política de security después de 30 días si son vendor binaries.

---

## 3. Devcontainer Configuration - Análisis

### Archivo: [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json)

#### ✅ Aspectos Positivos:
1. Configuración bien estructurada
2. Extensions bien elegidas para el stack
3. DNS custom (Cloudflare 1.1.1.1) - buena práctica
4. Docker-in-docker habilitado correctamente
5. Cache para uv y pre-commit - excelente performance
6. PostCreateCommand instala pre-commit hooks automáticamente

#### ❌ Problemas Identificados:

1. **gh CLI no estaba instalado** (YA RESUELTO)
   - Línea 76: `sudo apt-get install -y gh`
   - ✅ Ya está en postCreateCommand

2. **yamllint no estaba instalado** (YA RESUELTO)
   - Línea 76: `sudo apt-get install -y yamllint`
   - ✅ Ya está en postCreateCommand

3. **make no estaba instalado** (PENDIENTE)
   - Línea 76 no incluye make
   - **Impacto**: Si tienes Makefile no funcionará
   - **Fix**: Ya está en postCreateCommand desde tu última actualización

4. **Dockerfile no refleja postCreateCommand**
   - [Dockerfile](.devcontainer/Dockerfile) no instala gh/yamllint/make
   - Esto significa que se instalan en cada `devcontainer up`
   - **Recomendación**: Mover estas instalaciones al Dockerfile para performance

5. **Falta verificación de salud del container**
   - No hay health check
   - **Recomendación**: Agregar verification script

6. **Secrets management no documentado**
   - No hay ejemplo de cómo montar secrets
   - **Recomendación**: Agregar ejemplo en README

#### Mejoras Sugeridas:

```json
{
  // ... existing config ...

  // Agregar lifecycle commands para debugging
  "postStartCommand": "echo 'DevContainer started successfully!'",

  // Agregar inicialización más robusta
  "postCreateCommand": [
    "bash",
    "-lc",
    "set -euo pipefail; \
     sudo mkdir -p /home/vscode/.cache/pre-commit /workspace/.cache; \
     sudo chown -R vscode:vscode /home/vscode/.cache /workspace/.cache; \
     sudo apt-get update && sudo apt-get install -y gh make yamllint git-lfs jq || true; \
     uvx pre-commit install --install-hooks || true; \
     git lfs install || true"
  ],

  // Agregar features adicionales útiles
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}  // Alternativa a apt install
  }
}
```

### Archivo: [.devcontainer/Dockerfile](.devcontainer/Dockerfile)

#### ✅ Aspectos Positivos:
1. Multi-stage build - excelente performance
2. Usa BuildKit syntax 1.7
3. Versiones pinneadas de Terraform/Terragrunt/TFLint
4. Build args bien definidos
5. Cache mounts para apt
6. User vscode (no root) - buena seguridad

#### ❌ Problemas Identificados:

1. **Base image no verificada**
   - Línea 38: `BASE_IMAGE=ghcr.io/malpanez/devcontainer-base:py312`
   - No hay verificación de checksum/signature
   - **Recomendación**: Considerar `cosign verify` si publicas con signing

2. **Binarios descargados sin verificación**
   - Líneas 29-32: Terragrunt y TFLint sin checksum validation
   - **Riesgo**: Supply chain attack
   - **Fix**: Agregar SHA256 verification

3. **Faltan tools comunes**
   - No están pre-instalados: gh, yamllint, make, jq
   - Se instalan en postCreateCommand = más lento
   - **Fix**: Ver mejora abajo

4. **Checkov version constraint demasiado amplio**
   - Línea 54: `"checkov>=3.0.0,<4.0.0"`
   - Puede introducir breaking changes
   - **Recomendación**: Pin a versión específica

#### Mejoras Sugeridas:

```dockerfile
# Add after line 46 (after ENV declarations)

# Install common CLI tools that are currently in postCreateCommand
RUN --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gh \
        make \
        yamllint \
        jq \
        git-lfs && \
    rm -rf /var/lib/apt/lists/*

# Add checksum validation for Terragrunt
# After line 29, before curl command:
TERRAGRUNT_SHA256_AMD64="<expected_sha256_for_amd64>" \
TERRAGRUNT_SHA256_ARM64="<expected_sha256_for_arm64>" \

# Then modify download section to:
RUN set -eux; \
    case "${TARGETPLATFORM}" in \
      "linux/amd64") ARCH="amd64"; EXPECTED_SHA="${TERRAGRUNT_SHA256_AMD64}" ;; \
      "linux/arm64") ARCH="arm64"; EXPECTED_SHA="${TERRAGRUNT_SHA256_ARM64}" ;; \
      *) echo "Unsupported TARGETPLATFORM: ${TARGETPLATFORM}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_${ARCH}" \
      -o /usr/local/bin/terragrunt; \
    echo "${EXPECTED_SHA}  /usr/local/bin/terragrunt" | sha256sum -c -; \
    chmod +x /usr/local/bin/terragrunt
```

---

## 4. Workflows - Análisis de Seguridad

### Problemas Críticos Encontrados:

#### 1. [sync-main-to-develop.yml](.github/workflows/sync-main-to-develop.yml)

**Problema CRÍTICO** - Línea 79-98:
```yaml
gh pr create \
  --base develop \
  --head "$BRANCH_NAME" \
  --title "chore: sync main to develop" \
  --body "$(cat <<'PRBODY'
## Summary

Automated sync from main to develop branch.

**Trigger**: ${{ github.event_name }}
**Main SHA**: ${{ github.sha }}
```

**Vulnerabilidad**: Las variables de GitHub (`${{ github.event_name }}`, `${{ github.sha }}`) están dentro de un HEREDOC de bash, pero **NO** están siendo interpoladas por GitHub Actions porque están dentro de una string de bash.

**Impacto**:
- Las variables aparecerán literalmente como "${{ github.event_name }}" en el PR body
- NO es una vulnerabilidad de seguridad pero es un bug funcional

**Fix**:
```yaml
# Opción 1: Usar variables de entorno
- name: Sync main to develop
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    TRIGGER: ${{ github.event_name }}
    MAIN_SHA: ${{ github.sha }}
  run: |
    # ... existing code ...
    gh pr create \
      --base develop \
      --head "$BRANCH_NAME" \
      --title "chore: sync main to develop" \
      --body "$(cat <<PRBODY
## Summary

Automated sync from main to develop branch.

**Trigger**: ${TRIGGER}
**Main SHA**: ${MAIN_SHA}

### Review Notes
- Check for any merge conflicts
- Verify all changes are expected
- Ensure CI passes before merging

**Auto-generated by sync workflow**
PRBODY
)"
```

**Workflow que falló**: Este workflow mostró "No jobs were run" porque la condición en línea 24 falló:
```yaml
if: github.ref == 'refs/heads/main' || (github.event_name == 'workflow_dispatch' && github.event.inputs.force == 'true')
```
Esto es correcto para prevenir ejecuciones accidentales, pero el email que recibiste es porque el workflow se triggereó pero no ejecutó ningún job.

#### 2. Permissions en Workflows

**Análisis por archivo**:

| Workflow | Permisos | Riesgo | Recomendación |
|----------|----------|--------|---------------|
| [ci.yml](.github/workflows/ci.yml) | `contents: read` (global)<br>`packages: write` (jobs) | ✅ SEGURO | Excelente - least privilege |
| [sync-main-to-develop.yml](.github/workflows/sync-main-to-develop.yml#L15-L17) | `contents: write`<br>`pull-requests: write` | ⚠️ MEDIO | OK para propósito, pero limitar a job específico |
| [build-containers.yml](.github/workflows/build-containers.yml) | Probablemente tiene `packages: write` | ⚠️ MEDIO | Verificar y documentar |
| [release.yml](.github/workflows/release.yml) | Probablemente tiene varios write | ⚠️ MEDIO | Verificar que solo corre en tags |

**Mejora para sync-main-to-develop.yml**:
```yaml
permissions:
  contents: read  # Default restrictivo

jobs:
  sync:
    name: Sync Main to Develop
    runs-on: ubuntu-latest
    permissions:
      contents: write        # Solo para git push
      pull-requests: write   # Solo para gh pr create
    # ... rest of job
```

#### 3. CodeQL / SAST

**Estado actual**:
- Trivy habilitado en [ci.yml](.github/workflows/ci.yml#L736-L753)
- Upload to SARIF en [ci.yml](.github/workflows/ci.yml#L748-L753)
- Scorecard habilitado en [scorecard.yml](.github/workflows/scorecard.yml)

**Problema**:
- No hay CodeQL para análisis de código Python/Shell
- Solo Trivy para containers

**Recomendación**: Agregar CodeQL workflow

---

## 5. Mejoras Generales del Repositorio

### 5.1. Branch Protection (CRÍTICO)

**Configurar para `main` y `develop`**:

1. Via GitHub UI: Settings → Branches → Branch protection rules
2. O via Terraform/API (más reproducible):

```hcl
# github_branch_protection.tf
resource "github_branch_protection" "main" {
  repository_id = github_repository.repo.node_id
  pattern       = "main"

  required_pull_request_reviews {
    required_approving_review_count = 1
    require_code_owner_reviews      = false
    dismiss_stale_reviews           = true
  }

  required_status_checks {
    strict   = true
    contexts = ["CI Success"]
  }

  enforce_admins                  = false  # Permite emergency fixes
  require_signed_commits          = true
  require_conversation_resolution = true
}
```

**Configuración mínima recomendada**:
- ✅ Require pull request before merging
- ✅ Require approvals: 1 (para proyecto con múltiples maintainers)
- ✅ Require status checks to pass: CI Success
- ✅ Require conversation resolution
- ⚠️ Require signed commits (opcional pero recomendado)
- ❌ Do not require administrator enforcement (permite emergency fixes)

### 5.2. Dependabot Configuration (CRÍTICO)

**Crear**: [.github/dependabot.yml](.github/dependabot.yml)

```yaml
version: 2
updates:
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 10
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "chore(deps)"

  # Docker (devcontainer base images)
  - package-ecosystem: "docker"
    directory: "/devcontainers/base"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  - package-ecosystem: "docker"
    directory: "/devcontainers/ansible"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  - package-ecosystem: "docker"
    directory: "/.devcontainer"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  # Python dependencies
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "python"
    commit-message:
      prefix: "chore(deps)"

  # Terraform
  - package-ecosystem: "terraform"
    directory: "/terraform"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "terraform"
    ignore:
      # Ignore patch updates for Terraform modules
      - dependency-name: "*"
        update-types: ["version-update:semver-patch"]
```

### 5.3. CodeQL Workflow (HIGH)

**Crear**: [.github/workflows/codeql.yml](.github/workflows/codeql.yml)

```yaml
---
name: CodeQL Security Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 6 * * 1'  # Weekly Monday 6 AM UTC

permissions:
  contents: read

jobs:
  analyze:
    name: Analyze Code
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: ['python', 'javascript']

    steps:
      - name: Checkout repository
        uses: actions/checkout@1af3b93b6815bc44a9784bd300feb67ff0d1eeb3  # v6.0.0

      - name: Initialize CodeQL
        uses: github/codeql-action/init@fdbfb4d2750291e159f0156def62b853c2798ca2  # v4
        with:
          languages: ${{ matrix.language }}
          queries: +security-extended,security-and-quality

      - name: Autobuild
        uses: github/codeql-action/autobuild@fdbfb4d2750291e159f0156def62b853c2798ca2  # v4

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@fdbfb4d2750291e159f0156def62b853c2798ca2  # v4
        with:
          category: "/language:${{ matrix.language }}"
```

### 5.4. Renovate como alternativa a Dependabot

Si prefieres más control, considera Renovate:

**Crear**: [.github/renovate.json](.github/renovate.json)

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base",
    ":dependencyDashboard",
    ":semanticCommits",
    ":separateMajorReleases"
  ],
  "labels": ["dependencies"],
  "schedule": ["before 6am on monday"],
  "timezone": "UTC",
  "prConcurrentLimit": 5,
  "packageRules": [
    {
      "matchManagers": ["github-actions"],
      "groupName": "GitHub Actions",
      "automerge": true,
      "automergeType": "pr",
      "platformAutomerge": true
    },
    {
      "matchManagers": ["dockerfile"],
      "groupName": "Docker dependencies",
      "schedule": ["before 6am on monday"]
    },
    {
      "matchManagers": ["pip_requirements"],
      "groupName": "Python dependencies",
      "schedule": ["before 6am on monday"]
    }
  ],
  "vulnerabilityAlerts": {
    "labels": ["security"],
    "assignees": ["@malpanez"]
  }
}
```

### 5.5. Pre-commit Hooks Enhancement

Tu configuración actual es buena, pero considera agregar más hooks:

**Archivo**: `.pre-commit-config.yaml` (si no existe)

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key
      - id: check-added-large-files
        args: ['--maxkb=1000']

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-docker

  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.86.0
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_tflint

  - repo: https://github.com/ansible/ansible-lint
    rev: v6.22.1
    hooks:
      - id: ansible-lint

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.9.0.6
    hooks:
      - id: shellcheck
```

### 5.6. Documentación de Seguridad

**Crear**: [docs/SECURITY_PRACTICES.md](docs/SECURITY_PRACTICES.md)

```markdown
# Security Practices

## Development Workflow

1. **Never commit secrets**
   - Use `.secrets.baseline` and pre-commit hooks
   - Store in 1Password/Bitwarden/Vault
   - Inject via environment variables

2. **Dependency Management**
   - Pin versions in Dockerfile
   - Use SHA256 for GitHub Actions
   - Review Dependabot PRs weekly

3. **Code Review**
   - All changes require PR
   - At least 1 approval required
   - CI must pass

4. **Container Security**
   - Scan with Trivy
   - Review HIGH/CRITICAL findings
   - Document risk acceptance in PR

## Security Contacts

- Security issues: alpanez.alcalde@gmail.com
- Response time: 3 business days
```

### 5.7. SECURITY.md Improvements

Tu [SECURITY.md](SECURITY.md) es excelente. Pequeñas mejoras:

```markdown
# Add after line 32:

## Security Scanning

We use multiple tools to detect vulnerabilities:

- **Trivy**: Container and filesystem scanning (weekly)
- **CodeQL**: Static analysis for Python/Shell (weekly)
- **Scorecard**: OSSF best practices (weekly)
- **Dependabot**: Dependency vulnerability alerts (daily)

### Known Security Issues

See [SECURITY_REVIEW.md](SECURITY_REVIEW.md) for current security posture and accepted risks.

### Automated Alert Management

We automatically dismiss certain false positives and stale alerts:
- Vendor binary CVEs where we're using patched versions
- Go stdlib CVEs in pre-compiled binaries (dev environment only)
- Alerts older than 90 days without re-detection

For details, see [.github/scripts/manage-code-scanning-alerts.sh](.github/scripts/manage-code-scanning-alerts.sh).
```

---

## 6. Plan de Acción Prioritizado

### 🔴 CRÍTICO (Esta Semana)

1. **Habilitar Branch Protection**
   - Ir a Settings → Branches → Add rule
   - Pattern: `main`
   - ✅ Require pull request
   - ✅ Require 1 approval
   - ✅ Require status checks: "CI Success"

2. **Crear Dependabot Config**
   - Copiar el YAML de arriba a `.github/dependabot.yml`
   - Commit y push
   - Verificar que se crean PRs en la siguiente semana

3. **Ejecutar Security Alert Management**
   ```bash
   # Conectar gh CLI
   gh auth login

   # Dry run first
   DRY_RUN=true .github/scripts/manage-code-scanning-alerts.sh

   # Real execution
   DRY_RUN=false .github/scripts/manage-code-scanning-alerts.sh
   ```

4. **Fix sync-main-to-develop.yml**
   - Aplicar el fix de variables de entorno sugerido arriba
   - Test con workflow_dispatch

### 🟠 HIGH (Próxima Semana)

5. **Agregar CodeQL Workflow**
   - Copiar workflow sugerido arriba
   - Commit y verificar que corre

6. **Mejorar Dockerfile**
   - Agregar checksum validation para binarios
   - Pre-instalar gh, make, yamllint, jq
   - Rebuild y test

7. **Documentar Procesos de Seguridad**
   - Crear docs/SECURITY_PRACTICES.md
   - Actualizar README con security badges
   - Actualizar SECURITY.md con información de scanning

### 🟡 MEDIUM (Próximas 2 Semanas)

8. **Pin Dependencies con Hash**
   - Revisar requirements.yml (Ansible collections)
   - Considerar usar lock files donde sea posible

9. **Mejorar Pre-commit Hooks**
   - Agregar hooks sugeridos arriba
   - Test localmente
   - Documentar en CONTRIBUTING.md

10. **Setup Signed Releases**
    - Configurar GPG key en GitHub
    - Actualizar release workflow para firmar tags
    - Documentar proceso

### 🟢 LOW (Cuando Tengas Tiempo)

11. **Considerar Fuzzing**
    - Solo si expones APIs públicas
    - No crítico para devcontainer project

12. **Mejorar DevContainer Health Checks**
    - Agregar script de verificación
    - Test automático de tools instalados

13. **Renovate en lugar de Dependabot**
    - Solo si quieres más control
    - Dependabot es suficiente para la mayoría de casos

---

## 7. Métricas de Éxito

### Objetivo: OSSF Scorecard > 7.0

| Check | Actual | Objetivo | Acción |
|-------|--------|----------|--------|
| Maintained | 0 | 5+ | Resolver issues/PRs en <7 días |
| Code-Review | 0 | 10 | Branch protection + require reviews |
| Dependency-Update | 0 | 10 | Habilitar Dependabot |
| Branch-Protection | ? | 10 | Configurar rules en GitHub |
| Dangerous-Workflow | ? | 10 | Fix sync-main-to-develop.yml |
| Token-Permissions | ? | 10 | Least privilege en todos los workflows |
| Signed-Releases | 0 | 8+ | GPG signing para tags |
| SAST | 10 | 10 | Mantener + agregar CodeQL |
| Pinned-Dependencies | 5 | 8+ | Pin con hash donde sea posible |

### Objetivo: 0 Security Alerts Críticas

- Ejecutar script de alert management semanalmente
- Revisar Dependabot PRs en <3 días
- Update vendor binaries quarterly

### Objetivo: 100% Test Coverage para Scripts Críticos

- `.github/scripts/manage-code-scanning-alerts.sh`
- Otros scripts de automation

---

## 8. Recursos Adicionales

- [OSSF Scorecard Docs](https://github.com/ossf/scorecard)
- [GitHub Security Best Practices](https://docs.github.com/en/code-security)
- [Trivy Documentation](https://trivy.dev/)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

---

## 9. Contacto

Para preguntas sobre este review:
- Email: alpanez.alcalde@gmail.com
- GitHub: @malpanez

---

**Próxima revisión**: 2026-03-05 (quarterly)
**Responsable**: Miguel Alpañez
**Status**: ⚠️ ACCIÓN REQUERIDA - Ver sección 6 "Plan de Acción"
