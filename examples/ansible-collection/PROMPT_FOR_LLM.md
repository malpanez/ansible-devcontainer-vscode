# Prompt para LLM: Configurar DevContainer de Ansible

**Prompt listo para copiar y pegar en Claude, ChatGPT, o cualquier LLM**

---

## 🎯 Objetivo

Configurar un entorno de desarrollo Ansible con devcontainers de malpanez que incluye:
- ✅ Ansible 9.14.0 + Python 3.12.12 + uv (10-100x más rápido que pip)
- ✅ Pre-commit hooks (ansible-lint, yamllint, gitleaks)
- ✅ VS Code extensions (Ansible, YAML, Jinja2)
- ✅ Entorno consistente en todo el equipo
- ✅ Zero configuración manual

---

## 📋 Prompt Completo

```
Necesito configurar un proyecto de Ansible (collection/playbook/role) usando los devcontainers production-ready de malpanez/ansible-devcontainer-vscode.

**Contexto del proyecto**:
- Tipo: [Ansible Collection / Playbook / Role]
- Nombre: [nombre del proyecto]
- Repositorio: [URL o ruta local]

**Lo que necesito configurar**:

1. **DevContainer con la imagen de malpanez**:
   - Imagen: ghcr.io/malpanez/devcontainer-ansible:latest
   - Incluye: Ansible 9.14.0, Python 3.12.12, uv, ansible-lint, yamllint
   - Features adicionales: git, github-cli (ya están en el template)

2. **Pre-commit hooks que se ejecuten ANTES de cada commit**:
   - ansible-lint (con --fix automático)
   - yamllint (con configuración personalizada)
   - gitleaks (detección de secretos)
   - check-yaml, detect-private-key
   - trailing-whitespace, end-of-file-fixer

3. **VS Code configurado automáticamente** con:
   - Extensiones: Ansible, YAML, Jinja2, GitLens, Python, Ruff
   - Settings: interpretador Python, validación Ansible, schemas YAML
   - Asociaciones de archivos (*.yml → ansible)

4. **Permisos correctos para pre-commit** (esto es CRÍTICO):
   - PRE_COMMIT_HOME: /home/vscode/.cache/pre-commit
   - Arreglar permisos de ~/.cache al crear el container
   - Evitar errores de "Permission denied" en gitleaks/Go

5. **Montajes automáticos**:
   - ~/.ssh (read-only) para git/SSH
   - Mantener secrets fuera del container

**Setup rápido (comando de una línea)**:

```bash
# Descarga los archivos de configuración necesarios
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml && \
echo "✅ Configuración descargada. Abre VS Code: code ."
```

**Flujo de trabajo esperado**:

1. Abrir el proyecto en VS Code
2. Click en "Reopen in Container" cuando aparezca el popup
3. VS Code descarga la imagen ghcr.io/malpanez/devcontainer-ansible:latest
4. Container inicia con Ansible + Python + uv pre-instalado
5. Pre-commit hooks se instalan automáticamente
6. Extensiones de VS Code se configuran automáticamente
7. ¡Listo para desarrollar!

**Cuando hago commit**:

```bash
# Edito mi role/playbook
vim roles/security/tasks/main.yml

# Hago commit
git add roles/security/
git commit -m "feat: add CIS compliance checks"

# Pre-commit se ejecuta AUTOMÁTICAMENTE:
# ✅ ansible-lint.......................................Passed
# ✅ yamllint............................................Passed
# ✅ gitleaks............................................Passed
# ✅ check-yaml..........................................Passed
# ✅ Commit exitoso!
```

**Lo que el devcontainer.json debe incluir (CRÍTICO - permisos de caché)**:

```json
{
  "name": "Ansible Collection Development",
  "image": "ghcr.io/malpanez/devcontainer-ansible:latest",

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
    "pre-commit install --install-hooks || true; [ -f requirements.yml ] && ansible-galaxy collection install -r requirements.yml || true"
  ],

  "remoteUser": "vscode"
}
```

**¿Por qué estos devcontainers son mejores que la imagen oficial de Ansible?**

| Feature | Oficial Ansible | malpanez/devcontainer-ansible |
|---------|----------------|--------------------------------|
| Python | 3.11 | 3.12.12 (latest) |
| Package Manager | pip | uv (10-100x faster) |
| Pre-commit | ❌ No | ✅ Si (configurado) |
| Security Tools | ❌ Básico | ✅ Trivy, gitleaks |
| OpenSSF Scorecard | N/A | ✅ 6.1/10 |
| Automation | ❌ No | ✅ 90% automatizado |
| Maintenance | Manual | Renovate bot |

**Ventajas adicionales**:
- ✅ Pinned dependencies (SHA256) - reproducible
- ✅ Multi-arch (amd64/arm64) - funciona en Apple Silicon
- ✅ Automated updates (Renovate bot) - siempre actualizado
- ✅ Security scanning built-in (Trivy) - detecta vulnerabilidades
- ✅ 90% maintenance automated - casi cero mantenimiento

**Recursos adicionales**:
- Guía completa: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
- Ejemplos: https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples/ansible-collection
- Mantenimiento: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/MAINTENANCE.md

**Por favor ayúdame a**:
1. ✅ Verificar que el setup funciona correctamente
2. ✅ Probar que los pre-commit hooks se ejecutan
3. ✅ Entender qué hace cada hook y por qué es importante
4. ✅ Customizar para mi proyecto específico (si es necesario)
5. ✅ Troubleshoot cualquier problema que encuentre
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

### "Pre-commit hooks not running"

```bash
# Reinstalar hooks
pre-commit install --install-hooks

# Probar manualmente
pre-commit run --all-files

# Actualizar hooks
pre-commit autoupdate
```

### "Container won't start"

```bash
# Pull de la imagen latest
docker pull ghcr.io/malpanez/devcontainer-ansible:latest

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

Usamos devcontainers de malpanez para Ansible (production-ready, OpenSSF 6.1/10).

**Setup rápido (2 minutos)**:
1. Instala Docker Desktop + VS Code
2. Clona el repo
3. Ejecuta:
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.devcontainer/devcontainer.json -o .devcontainer/devcontainer.json --create-dirs && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.pre-commit-config.yaml -o .pre-commit-config.yaml && \
   curl -fsSL https://raw.githubusercontent.com/malpanez/ansible-devcontainer-vscode/main/examples/ansible-collection/.yamllint.yml -o .yamllint.yml
4. Abre en VS Code: code .
5. Click "Reopen in Container"
6. ¡Listo!

Pre-commit hooks se ejecutan automáticamente antes de cada commit.

¿Dudas? Revisa: https://github.com/malpanez/ansible-devcontainer-vscode/blob/main/INTEGRATION_GUIDE.md
```

---

## 📚 Archivos de Configuración

Los archivos que necesitas:

1. **.devcontainer/devcontainer.json** - Configuración del container
2. **.pre-commit-config.yaml** - Hooks de pre-commit
3. **.yamllint.yml** - Configuración de yamllint
4. **(opcional) requirements.yml** - Ansible Galaxy collections

Todos disponibles en:
https://github.com/malpanez/ansible-devcontainer-vscode/tree/main/examples/ansible-collection
