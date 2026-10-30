# Prompt para LLM: Configurar DevContainer de Terraform

**Prompt listo para copiar y pegar en Claude, ChatGPT, o cualquier LLM**

---

## 🎯 Objetivo

Configurar un entorno de desarrollo Terraform con devcontainers de malpanez que incluye:
- ✅ Terraform + Terragrunt + TFLint (versiones en `devcontainers/terraform/Dockerfile`)
- ✅ Pre-commit hooks (fmt, validate, tflint, trivy, terraform-docs)
- ✅ VS Code extensions (Terraform, GitLens)
- ✅ Security tools (SOPS + age; Trivy and gitleaks via pre-commit hooks)
- ✅ AWS CLI (imagen `devcontainer-terraform-aws`)
- ✅ Entorno consistente en todo el equipo
- ✅ Zero configuración manual

---

## 📋 Prompt Completo

```
Necesito configurar un proyecto de Terraform/Terragrunt usando los devcontainers production-ready de malpanez/ansible-devcontainer-vscode.

**Contexto del proyecto**:
- Tipo: [Terraform Module / Terragrunt Stack / Infrastructure]
- Cloud Provider: [AWS / Azure / GCP / Multi-cloud]
- Nombre: [nombre del proyecto]
- Repositorio: [URL o ruta local]

**Lo que necesito configurar**:

1. **DevContainer con la imagen de malpanez**:
   - Imagen: ghcr.io/malpanez/devcontainer-terraform:latest
   - Incluye: Terraform, Terragrunt, TFLint (versiones en `devcontainers/terraform/Dockerfile`)
   - Tools: SOPS, age (AWS CLI: usar devcontainer-terraform-aws)
   - Features adicionales: git, github-cli (ya están en el template)

2. **Pre-commit hooks que se ejecuten ANTES de cada commit**:
   - terraform fmt (auto-formato)
   - terraform validate (validación de sintaxis)
   - terraform-docs (auto-actualiza README.md)
   - tflint (best practices linting - configurado para AWS por defecto)
   - trivy (security scanning - solo CRITICAL/HIGH)
   - gitleaks (detección de secretos)
   - check-yaml, detect-private-key
   - trailing-whitespace, end-of-file-fixer

3. **VS Code configurado automáticamente** con:
   - Extensiones: Terraform (HashiCorp), GitLens, Docker, GitHub Actions
   - Settings: Language Server, Code Lens, format on save
   - Terraform formatter como default

4. **Permisos correctos para pre-commit** (esto es CRÍTICO):
   - PRE_COMMIT_HOME: /home/vscode/.cache/pre-commit
   - Arreglar permisos de ~/.cache al crear el container
   - Evitar errores de "Permission denied" en gitleaks/Go

5. **Montajes automáticos**:
   - ~/.aws (read-only, debe existir en el host) para credenciales de AWS; solo con la imagen -aws
   - ~/.ssh (read-only) para git/SSH
   - Mantener secrets fuera del container

**Setup rápido (comando de una línea)**:

```bash
# Descarga los archivos de configuración necesarios
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml && \
echo "✅ Configuración descargada. Abre VS Code: code ."
```

**Flujo de trabajo esperado**:

1. Abrir el proyecto en VS Code
2. Click en "Reopen in Container" cuando aparezca el popup
3. VS Code descarga la imagen ghcr.io/malpanez/devcontainer-terraform:latest
4. Container inicia con Terraform + Terragrunt + TFLint pre-instalado
5. AWS credentials se montan desde ~/.aws (read-only)
6. SSH keys se montan desde ~/.ssh (read-only)
7. Pre-commit hooks se instalan automáticamente
8. terraform init se ejecuta automáticamente
9. Extensiones de VS Code se configuran automáticamente
10. ¡Listo para desarrollar!

**Cuando hago commit**:

```bash
# Edito mi módulo
vim main.tf

# Hago commit
git add main.tf
git commit -m "feat: add VPC security group"

# Pre-commit se ejecuta AUTOMÁTICAMENTE:
# ✅ Terraform fmt......................................Passed
# ✅ Terraform validate..................................Passed
# ✅ Terraform docs......................................Passed (README.md actualizado!)
# ✅ Terraform validate with tflint......................Passed
# ✅ Terraform validate with trivy.......................Passed
# ✅ Detect secrets......................................Passed
# ✅ Commit exitoso!
```

**Lo que el devcontainer.json debe incluir (CRÍTICO - permisos de caché)**:

```json
{
  "name": "Terraform Project Development",
  "image": "ghcr.io/malpanez/devcontainer-terraform:latest",

  "containerEnv": {
    "PRE_COMMIT_HOME": "/home/vscode/.cache/pre-commit"
  },

  "updateContentCommand": [
    "bash",
    "-c",
    "mkdir -p /home/vscode/.cache/pre-commit && chown -R vscode:vscode /home/vscode/.cache"
  ],

  "postCreateCommand": [
    "bash",
    "-c",
    "pre-commit install --install-hooks || true; terraform init || true"
  ],

  "remoteUser": "vscode"
}
```

**¿Por qué estos devcontainers son mejores que la imagen oficial de Terraform?**

| Feature | Oficial HashiCorp | malpanez/devcontainer-terraform |
|---------|------------------|----------------------------------|
| Terraform | Latest | pinned (`devcontainers/terraform/Dockerfile`) |
| Terragrunt | ❌ No | ✅ pinned |
| TFLint | ❌ No | ✅ pinned (con rulesets) |
| Pre-commit | ❌ No | ✅ Si (configurado) |
| Security Tools | ❌ No | ✅ Trivy, SOPS, age, gitleaks |
| terraform-docs | ❌ No | ✅ Si (auto-updates README) |
| OpenSSF Scorecard | N/A | ✅ 6.1/10 |
| Automation | ❌ No | ✅ 90% automatizado |
| Maintenance | Manual | Renovate bot |

**Ventajas adicionales**:
- ✅ Pinned dependencies (SHA256) - reproducible
- ✅ Multi-arch (amd64/arm64) - funciona en Apple Silicon
- ✅ Automated updates (Renovate bot) - siempre actualizado
- ✅ Security scanning built-in (Trivy) - detecta vulnerabilidades
- ✅ 90% maintenance automated - casi cero mantenimiento
- ✅ SOPS + age para secrets - cifrado de secretos en git
- ✅ terraform-docs - documentación automática

**Features especiales para Terraform**:

### terraform-docs (auto-documentación)

Añade esto a tu README.md:

```markdown
<!-- BEGIN_TF_DOCS -->
<!-- terraform-docs insertará la documentación aquí automáticamente -->
<!-- END_TF_DOCS -->
```

Pre-commit actualizará automáticamente esta sección con:
- Inputs (variables)
- Outputs
- Resources
- Modules
- Requirements

### SOPS + age (gestión de secrets)

```bash
# Generar clave age (primera vez)
age-keygen -o ~/.age/key.txt

# Cifrar archivo sensible
export SOPS_AGE_KEY_FILE=~/.age/key.txt
sops --encrypt --age $(age-keygen -y ~/.age/key.txt) terraform.tfvars > terraform.tfvars.enc

# Editar archivo cifrado
sops terraform.tfvars.enc

# Descifrar para uso
sops --decrypt terraform.tfvars.enc > terraform.tfvars

# Añadir a .gitignore
echo "terraform.tfvars" >> .gitignore
echo "!terraform.tfvars.enc" >> .gitignore
```

### TFLint (customización por cloud provider)

**Por defecto**: Configurado para AWS

**Para Azure**: Edita `.tflint.hcl`:

```hcl
plugin "azurerm" {
  enabled = true
  version = "0.30.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}
```

**Para GCP**: Edita `.tflint.hcl`:

```hcl
plugin "google" {
  enabled = true
  version = "0.30.0"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}
```

### Trivy (optimización de performance)

Si Trivy es muy lento:

```bash
# Skip trivy en commits rápidos
SKIP=terraform_trivy git commit -m "feat: quick change"

# O ajusta severidad en .pre-commit-config.yaml:
- id: terraform_trivy
  args:
    - --args=--severity=CRITICAL  # Solo CRITICAL (más rápido)
```

**Recursos adicionales**:
- Guía completa: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
- Ejemplos: https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples/terraform-project
- Mantenimiento: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/MAINTENANCE.md

**Por favor ayúdame a**:
1. ✅ Verificar que el setup funciona correctamente
2. ✅ Probar que los pre-commit hooks se ejecutan
3. ✅ Entender terraform-docs y cómo configuro el README
4. ✅ Configurar SOPS + age para secrets
5. ✅ Customizar TFLint para mi cloud provider
6. ✅ Optimizar Trivy si es muy lento
7. ✅ Troubleshoot cualquier problema que encuentre
```

---

## 🔧 Troubleshooting Común

### "Permission denied" en pre-commit / gitleaks

**Causa**: Permisos incorrectos en ~/.cache/pre-commit

**Solución**: Asegúrate que el devcontainer.json incluye:

```json
{
  "containerEnv": {
    "PRE_COMMIT_HOME": "/home/vscode/.cache/pre-commit"
  },
  "updateContentCommand": [
    "bash", "-c",
    "mkdir -p /home/vscode/.cache/pre-commit && chown -R vscode:vscode /home/vscode/.cache"
  ],
  "postCreateCommand": [
    "bash", "-c",
    "pre-commit install --install-hooks || true"
  ]
}
```

**IMPORTANTE**: Usa `updateContentCommand` (ejecuta como root) en lugar de `postCreateCommand` con sudo, para evitar problemas de permisos en diferentes entornos.

### "Trivy muy lento"

```bash
# Opción 1: Skip en commits rápidos
SKIP=terraform_trivy git commit -m "feat: quick change"

# Opción 2: Solo CRITICAL
# Edita .pre-commit-config.yaml:
- id: terraform_trivy
  args:
    - --args=--severity=CRITICAL
```

### "terraform init fails"

```bash
# Ejecutar manualmente
terraform init

# Si usas workspaces
terraform workspace select dev

# Si usas backend remoto
terraform init -backend-config=backend.hcl
```

### "AWS credentials not found"

```bash
# Verifica que ~/.aws existe en el host
ls -la ~/.aws

# Debe contener:
# ~/.aws/credentials
# ~/.aws/config

# El devcontainer monta automáticamente (read-only)
```

### "terraform-docs no actualiza README"

Verifica que tu README.md tiene los marcadores:

```markdown
<!-- BEGIN_TF_DOCS -->
<!-- END_TF_DOCS -->
```

### "Container won't start"

```bash
# Pull de la imagen latest
docker pull ghcr.io/malpanez/devcontainer-terraform:latest

# Rebuild en VS Code
# Ctrl+Shift+P → "Dev Containers: Rebuild Container"
```

---

## 📊 Métricas de Producción

- **OpenSSF Scorecard**: 6.1/10
- **Automation**: 90%
- **Maintenance**: 5 min/semana (review), 2 horas/trimestre (comprehensive)
- **Security**: Renovate bot + weekly alert cleanup + Trivy scanning

---

## 🎓 Para Equipos

**Mensaje de onboarding** (copia esto a Slack/Discord):

```
👋 Bienvenido al equipo!

Usamos devcontainers de malpanez para Terraform (production-ready, OpenSSF 6.1/10).

**Setup rápido (2 minutos)**:
1. Instala Docker Desktop + VS Code
2. Clona el repo
3. Ejecuta:
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.tflint.hcl -o .tflint.hcl && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/terraform-project/.terraform-docs.yml -o .terraform-docs.yml
4. Abre en VS Code: code .
5. Click "Reopen in Container"
6. ¡Listo!

Pre-commit hooks se ejecutan automáticamente (fmt, validate, tflint, trivy, terraform-docs).

terraform-docs actualiza el README automáticamente.

¿Dudas? Revisa: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
```

---

## 📚 Archivos de Configuración

Los archivos que necesitas:

1. **.devcontainer/devcontainer.json** - Configuración del container
2. **.pre-commit-config.yaml** - Hooks de pre-commit
3. **.tflint.hcl** - Configuración de TFLint (AWS por defecto)
4. **.terraform-docs.yml** - Configuración de terraform-docs
5. **(opcional) .sops.yaml** - Configuración de SOPS para secrets

Todos disponibles en:
https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples/terraform-project

---

## 🔐 Gestión de Secrets con SOPS

### Setup inicial

```bash
# 1. Generar clave age
age-keygen -o ~/.age/key.txt

# 2. Obtener public key
age-keygen -y ~/.age/key.txt
# Output: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 3. Crear .sops.yaml en el repo
cat > .sops.yaml <<'EOF'
creation_rules:
  - path_regex: \.enc\.(yaml|yml|json|env|ini)$
    age: age1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
EOF

# 4. Añadir a .gitignore
echo "*.tfvars" >> .gitignore
echo "!*.tfvars.enc" >> .gitignore
```

### Uso diario

```bash
# Cifrar archivo
export SOPS_AGE_KEY_FILE=~/.age/key.txt
sops --encrypt terraform.tfvars > terraform.tfvars.enc

# Editar cifrado
sops terraform.tfvars.enc

# Descifrar para terraform
sops --decrypt terraform.tfvars.enc > terraform.tfvars
terraform plan -var-file=terraform.tfvars

# Limpiar después
rm terraform.tfvars
```

### Integración con CI/CD

```yaml
# GitHub Actions
- name: Decrypt secrets
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    echo "$SOPS_AGE_KEY" > /tmp/key.txt
    export SOPS_AGE_KEY_FILE=/tmp/key.txt
    sops --decrypt terraform.tfvars.enc > terraform.tfvars
```

---

## 📖 Cómo funcionan las Features en devcontainer.json

**Pregunta común**: "¿Si uso `image`, se hace pull o build?"

**Respuesta**:

1. **Solo `image`**: VS Code hace **pull** de la imagen (rápido)
   ```json
   {
     "image": "ghcr.io/malpanez/devcontainer-terraform:latest"
   }
   ```

2. **`image` + `features`**: VS Code hace **pull + build**
   ```json
   {
     "image": "ghcr.io/malpanez/devcontainer-terraform:latest",
     "features": {
       "ghcr.io/devcontainers/features/aws-cli:1": {}
     }
   }
   ```
   - Pull de la base image
   - Build de una capa derivada para aplicar features
   - Resultado: imagen temporal con features aplicados

**¿Por qué usar features si hace build?**

✅ **Ventajas**:
- Customización sin modificar el Dockerfile
- Añadir tools específicos del proyecto (azure-cli, gcloud, etc.)
- Compartir base image, customizar por proyecto

❌ **Desventajas**:
- Más lento (build adicional)
- Cada proyecto genera su propia imagen derivada

**Recomendación**:
- Si solo necesitas lo que incluye la base image → No uses features
- Si necesitas tools adicionales (aws-cli, azure-cli) → Usa features

**Nuestros templates ya incluyen features útiles**:
- git (control de versiones)
- github-cli (gh commands)
- aws-cli (para Terraform)

Si no los necesitas, puedes eliminar la sección `features` del devcontainer.json.
