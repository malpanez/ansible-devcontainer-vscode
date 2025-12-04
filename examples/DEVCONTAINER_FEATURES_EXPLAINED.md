# DevContainer: Pull vs Build - Explicación de Features

**TL;DR**: Si usas `"image"` solo → VS Code hace **pull** (rápido). Si usas `"image"` + `"features"` → VS Code hace **pull + build** (más lento).

---

## ¿Qué son las "Features"?

Las features en devcontainer.json son paquetes pre-configurados que VS Code puede instalar en tu container:

```json
"features": {
  "ghcr.io/devcontainers/features/git:1": {},
  "ghcr.io/devcontainers/features/github-cli:1": {},
  "ghcr.io/devcontainers/features/aws-cli:1": {}
}
```

Cada feature es un script que instala y configura herramientas adicionales.

---

## Comportamiento: Pull vs Build

### Opción 1: Solo `image` (RÁPIDO - Pull)

```json
{
  "name": "Ansible Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",
  "remoteUser": "vscode"
}
```

**Lo que hace VS Code**:
1. `docker pull ghcr.io/malpanez/devcontainer-ansible:latest` (descarga)
2. `docker run ...` (ejecuta directamente)

**Ventajas**:
- ✅ **Rápido** - solo descarga, no build
- ✅ Usa la imagen exactamente como fue construida
- ✅ Reproducible en todos los sistemas
- ✅ No genera imágenes temporales

**Desventajas**:
- ❌ No puedes añadir herramientas extra fácilmente
- ❌ Limitado a lo que incluye la imagen

**Tiempo**: ~30 segundos (solo primera vez, luego cache)

---

### Opción 2: `image` + `features` (LENTO - Pull + Build)

```json
{
  "name": "Ansible Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",
  "features": {
    "ghcr.io/devcontainers/features/git:1": {},
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
  "remoteUser": "vscode"
}
```

**Lo que hace VS Code**:
1. `docker pull ghcr.io/malpanez/devcontainer-ansible:latest` (descarga base image)
2. Genera un **Dockerfile temporal**:
   ```dockerfile
   FROM ghcr.io/malpanez/devcontainer-ansible:latest

   # Feature 1: git
   RUN curl -L https://github.com/devcontainers/features/releases/latest/download/devcontainer-feature-git.tgz | tar -xz
   RUN ./install.sh

   # Feature 2: github-cli
   RUN curl -L https://github.com/devcontainers/features/releases/latest/download/devcontainer-feature-github-cli.tgz | tar -xz
   RUN ./install.sh
   ```
3. `docker build -t vsc-ansible-xxxxx .` (construye imagen derivada)
4. `docker run vsc-ansible-xxxxx` (ejecuta la imagen derivada)

**Ventajas**:
- ✅ Puedes añadir herramientas extra fácilmente
- ✅ Customización sin modificar el Dockerfile
- ✅ Reutilizable entre proyectos (misma base + diferentes features)

**Desventajas**:
- ❌ **Lento** - hace build cada vez que cambias features
- ❌ Genera imágenes temporales (vsc-ansible-xxxxx)
- ❌ Consume más espacio en disco
- ❌ Menos reproducible (features pueden cambiar)

**Tiempo**: ~2-5 minutos (dependiendo de cuántas features)

---

## ¿Por qué nuestros templates usan features?

Nuestros templates incluyen estas features por defecto:

### Ansible
```json
"features": {
  "ghcr.io/devcontainers/features/git:1": {},
  "ghcr.io/devcontainers/features/github-cli:1": {}
}
```

### Terraform
```json
"features": {
  "ghcr.io/devcontainers/features/git:1": {},
  "ghcr.io/devcontainers/features/github-cli:1": {},
  "ghcr.io/devcontainers/features/aws-cli:1": {}
}
```

**Razones**:
1. **git** - Control de versiones (99% de proyectos lo necesitan)
2. **github-cli** - `gh` commands para PRs, issues, releases
3. **aws-cli** (Terraform) - AWS credentials y comandos

**Pero**... estas herramientas **YA ESTÁN en la base image** en muchos casos.

---

## Cómo evitar el build (usar solo pull)

### Verificar qué incluye la base image

```bash
# Verificar si git está en la imagen
docker run --rm ghcr.io/malpanez/devcontainer-ansible:latest which git

# Verificar si gh está en la imagen
docker run --rm ghcr.io/malpanez/devcontainer-ansible:latest which gh

# Verificar si aws está en la imagen (terraform)
docker run --rm ghcr.io/malpanez/devcontainer-terraform:latest which aws
```

Si el comando retorna una ruta (`/usr/bin/git`), **ya está instalado**.

### Remover features innecesarias

**Si git/gh/aws ya están en la imagen**, puedes simplificar:

#### devcontainer.json SIN features (RÁPIDO)

```json
{
  "name": "Ansible Collection Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",

  "containerEnv": {
    "PRE_COMMIT_HOME": "/home/vscode/.cache/pre-commit"
  },

  "customizations": {
    "vscode": {
      "settings": { /* ... */ },
      "extensions": [ /* ... */ ]
    }
  },

  "mounts": [
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,readonly"
  ],

  "postCreateCommand": [
    "bash", "-lc",
    "set -euo pipefail; sudo mkdir -p /home/vscode/.cache/pre-commit; sudo chown -R vscode:vscode /home/vscode/.cache; pre-commit install --install-hooks || true; [ -f requirements.yml ] && ansible-galaxy collection install -r requirements.yml || true"
  ],

  "remoteUser": "vscode"
}
```

**Ventajas**:
- ✅ Pull directo (rápido)
- ✅ No build
- ✅ No imágenes temporales

---

## Cuándo SÍ usar features

### Caso 1: Necesitas herramientas NO incluidas en la base image

Ejemplo: Necesitas Azure CLI en el container de Terraform:

```json
{
  "image": "ghcr.io/malpanez/devcontainer-terraform:latest",
  "features": {
    "ghcr.io/devcontainers/features/azure-cli:1": {}
  }
}
```

**Justificación**: Azure CLI no está en la imagen base, necesitas el feature.

### Caso 2: Customización específica del proyecto

Ejemplo: Proyecto que necesita Docker-in-Docker:

```json
{
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {}
  }
}
```

### Caso 3: Versión específica de una herramienta

Ejemplo: Necesitas Node.js 20 para Ansible + Terraform:

```json
{
  "image": "ghcr.io/malpanez/devcontainer-terraform:latest",
  "features": {
    "ghcr.io/devcontainers/features/node:1": {
      "version": "20"
    }
  }
}
```

---

## Recomendaciones

### ✅ Usa solo `image` (sin features) si:
- Las herramientas que necesitas ya están en la base image
- Quieres máxima velocidad
- No necesitas customizaciones extra

### ✅ Usa `image` + `features` si:
- Necesitas herramientas adicionales NO incluidas en la base
- Cada proyecto necesita diferentes tools
- La customización justifica el tiempo extra de build

---

## Qué incluyen nuestras base images

### ghcr.io/malpanez/devcontainer-ansible:latest

**Incluye**:
- Python 3.12.12
- uv (package manager)
- Ansible 9.14.0 (ansible-core 2.18.2)
- ansible-lint, yamllint
- molecule, ansible-test
- ✅ **git** (ya instalado)
- ✅ **github-cli (gh)** (ya instalado)
- gitleaks
- trivy
- Pre-commit

**Features que PUEDES ELIMINAR**: git, github-cli (ya están)

### ghcr.io/malpanez/devcontainer-terraform:latest

**Incluye**:
- Terraform 1.14.0
- Terragrunt 0.93.11
- TFLint 0.60.0
- SOPS 3.11.0
- age 1.2.1
- ✅ **git** (ya instalado)
- ✅ **github-cli (gh)** (ya instalado)
- ✅ **AWS CLI** (ya instalado)
- gitleaks
- trivy
- Pre-commit

**Features que PUEDES ELIMINAR**: git, github-cli, aws-cli (ya están)

**Features que SÍ NECESITARÍAS**:
- Azure CLI (`ghcr.io/devcontainers/features/azure-cli:1`)
- GCP CLI (`ghcr.io/devcontainers/features/gcp-cli:1`)

---

## Verificación de herramientas en la imagen

```bash
# Listar todas las herramientas instaladas (Ansible)
docker run --rm ghcr.io/malpanez/devcontainer-ansible:latest bash -c "
  echo '=== Git ==='
  git --version
  echo '=== GitHub CLI ==='
  gh --version
  echo '=== Ansible ==='
  ansible --version
  echo '=== Pre-commit ==='
  pre-commit --version
  echo '=== uv ==='
  uv --version
"

# Listar todas las herramientas instaladas (Terraform)
docker run --rm ghcr.io/malpanez/devcontainer-terraform:latest bash -c "
  echo '=== Git ==='
  git --version
  echo '=== GitHub CLI ==='
  gh --version
  echo '=== AWS CLI ==='
  aws --version
  echo '=== Terraform ==='
  terraform --version
  echo '=== Terragrunt ==='
  terragrunt --version
  echo '=== TFLint ==='
  tflint --version
  echo '=== SOPS ==='
  sops --version
  echo '=== age ==='
  age --version
"
```

---

## Actualizar templates para evitar build

### Versión RÁPIDA (sin features) - Ansible

```json
{
  "name": "Ansible Collection Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",

  "containerEnv": {
    "PRE_COMMIT_HOME": "/home/vscode/.cache/pre-commit"
  },

  "customizations": {
    "vscode": {
      "settings": {
        "ansible.python.interpreterPath": "/usr/local/bin/python",
        "ansible.validation.enabled": true,
        "ansible.validation.lint.enabled": true
      },
      "extensions": [
        "redhat.ansible",
        "redhat.vscode-yaml",
        "eamodio.gitlens",
        "ms-python.python"
      ]
    }
  },

  "mounts": [
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,readonly"
  ],

  "postCreateCommand": [
    "bash", "-lc",
    "sudo mkdir -p /home/vscode/.cache/pre-commit && sudo chown -R vscode:vscode /home/vscode/.cache && pre-commit install --install-hooks || true"
  ],

  "remoteUser": "vscode"
}
```

### Versión RÁPIDA (sin features) - Terraform

```json
{
  "name": "Terraform Project Development",
  "image": "ghcr.io/malpanez/devcontainer-terraform:latest",

  "containerEnv": {
    "PRE_COMMIT_HOME": "/home/vscode/.cache/pre-commit"
  },

  "customizations": {
    "vscode": {
      "settings": {
        "terraform.languageServer.enable": true,
        "terraform.codelens.enabled": true,
        "[terraform]": {
          "editor.defaultFormatter": "hashicorp.terraform",
          "editor.formatOnSave": true
        }
      },
      "extensions": [
        "hashicorp.terraform",
        "eamodio.gitlens"
      ]
    }
  },

  "mounts": [
    "source=${localEnv:HOME}/.aws,target=/home/vscode/.aws,type=bind,readonly",
    "source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,readonly"
  ],

  "postCreateCommand": [
    "bash", "-lc",
    "sudo mkdir -p /home/vscode/.cache/pre-commit && sudo chown -R vscode:vscode /home/vscode/.cache && pre-commit install --install-hooks || true && terraform init || true"
  ],

  "remoteUser": "vscode"
}
```

---

## Resumen

| Configuración | Tiempo de inicio | Build | Imágenes temporales | Customización |
|---------------|------------------|-------|---------------------|---------------|
| Solo `image` | ⚡ 30s | ❌ No | ❌ No | ⚠️ Limitada |
| `image` + `features` | 🐢 2-5min | ✅ Si | ✅ Si | ✅ Flexible |

**Recomendación para nuestros containers**:
- Si git/gh/aws ya están en la imagen → **Elimina features** (usa solo `image`)
- Si necesitas Azure/GCP CLI → **Añade solo esos features**
- Si quieres velocidad máxima → **Elimina todas las features**

**Cómo migrar**:
1. Verifica qué tools incluye la base image con `docker run --rm IMAGE which TOOL`
2. Elimina features duplicadas del devcontainer.json
3. Rebuild container en VS Code: `Ctrl+Shift+P` → "Dev Containers: Rebuild Container"
4. ¡Disfruta del inicio rápido!
