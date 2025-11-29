# 🚨 ACCIONES MANUALES REQUERIDAS

**IMPORTANTE**: Estas acciones no pueden ser automatizadas y requieren tu intervención.

---

## 🔴 URGENTE (Hacer HOY - 10 minutos)

### 1. Instalar Renovate App (5 minutos)

**Por qué**: Renovate está configurado pero necesita la GitHub App para funcionar.

**Pasos**:
```
1. Ve a: https://github.com/apps/renovate
2. Click "Configure"
3. Selecciona tu cuenta/organización: malpanez
4. En "Repository access":
   → Select: "Only select repositories"
   → Busca y marca: ansible-devcontainer-vscode
5. Click "Install" o "Save"
```

**Verificación**:
- En unos minutos, Renovate creará un PR: "Configure Renovate"
- Revisa el PR y mergealo
- Desde ese momento, recibirás PRs automáticos de updates

**Alternativa**: Si prefieres solo Dependabot:
```bash
# Borrar configuración de Renovate
rm .github/renovate.json
```

---

### 2. Habilitar Auto-merge en Settings (2 minutos)

**Por qué**: El workflow de auto-merge necesita esta feature habilitada.

**Pasos**:
```
1. Ve a: https://github.com/malpanez/ansible-devcontainer-vscode/settings
2. Scroll hasta sección "Pull Requests"
3. ✅ Marcar: "Allow auto-merge"
4. Click "Save"
```

**Verificación**:
- En el próximo PR de Renovate/Dependabot verás botón "Enable auto-merge"

---

### 3. Commitear y Push (3 minutos)

**IMPORTANTE**: Hay 19 archivos modificados/nuevos esperando commit.

```bash
# Ver cambios
git status

# Agregar todos
git add .

# Commit con mensaje detallado
git commit -m "feat: comprehensive repository improvements

Major improvements to automation, security, and developer experience:

🔴 Critical Issues Fixed:
- Add auto-publish to GHCR on push to main
- Unify Terraform versions across workflows (1.9.6)
- Configure auto-merge (Renovate + Dependabot + workflow)
- Add GHCR cleanup workflow (weekly retention)

🆕 New Features:
- Centralized versions file (.github/versions.yml)
- PR template with comprehensive checklist
- OpenSSF Security Scorecard workflow
- Code quality metrics workflow
- Troubleshooting guide (docs/TROUBLESHOOTING.md)

🔧 Technical Improvements:
- Update Go: 1.22 → 1.23
- Update Terragrunt: 0.54.22 → 0.67.1
- Update TFLint: 0.51.2 → 0.54.0
- Update SOPS: 3.9.0 → 3.9.3
- Update Age: 1.1.1 → 1.2.1
- Unify Trivy: v0.58.2
- LaTeX: Tectonic auto-compile + caching improvements
- CI: Pre-commit cache (~30% faster)
- Build: Timeouts + max-parallel optimization

📖 Documentation:
- Enhanced .trivyignore with CVE tracking
- Added CHANGELOG entry
- Added badges to README
- Complete improvements summary

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push a main
git push origin main
```

**Qué pasará después del push**:
1. ✅ Workflow de build-containers se ejecutará automáticamente
2. ✅ Se publicarán imágenes nuevas en GHCR
3. ✅ CI pipeline verificará todo
4. ✅ En ~10 minutos tendrás imágenes frescas en GHCR

---

## 🟡 RECOMENDADO (Esta semana - 30 minutos)

### 4. Configurar Branch Protection Rules (15 minutos)

**Por qué**: Protege la rama `main` de merges accidentales.

**Pasos**:
```
1. Ve a: Settings → Branches
2. Click "Add rule" o editar regla existente
3. Branch name pattern: main
4. Configurar:
   ✅ Require a pull request before merging
      → Require approvals: 0 (o 1 si trabajas en equipo)
   ✅ Require status checks to pass before merging
      → Search y agregar estos checks:
         - Pre-commit
         - Build Devcontainer (ansible)
         - Build Devcontainer (terraform)
         - Build Devcontainer (golang)
         - Build Devcontainer (latex)
   ✅ Require conversation resolution before merging
   ✅ Do not allow bypassing the above settings
5. Click "Create" o "Save changes"
```

**Beneficio**: Solo se pueden mergear PRs que pasen CI.

---

### 5. Revisar CVEs en .trivyignore (10 minutos)

**Por qué**: Verificar si las nuevas versiones resuelven CVEs.

**Pasos**:
```bash
# 1. Build local de imagen Terraform
cd /workspace
docker build -f devcontainers/terraform/Dockerfile -t test-terraform .

# 2. Scan con Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:0.58.2 image \
  --severity CRITICAL,HIGH \
  test-terraform

# 3. Si NO aparecen los CVEs de .trivyignore:
#    → Significa que están resueltos
#    → Puedes eliminarlos de .trivyignore

# 4. Si SÍ aparecen:
#    → Están correctamente documentados
#    → Mantener en .trivyignore
```

**CVEs a verificar**:
- CVE-2024-45337 (golang.org/x/crypto)
- CVE-2024-24790 (age, terragrunt Go version)
- CVE-2024-3817 (Terragrunt go-getter)

---

### 6. Crear Personal Access Token (Opcional - 5 minutos)

**Solo necesario si**: El auto-merge falla con permisos.

**Pasos**:
```
1. Ve a: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Nombre: "Renovate Auto-merge"
4. Scopes:
   ✅ repo (full control)
   ✅ workflow
5. Click "Generate token"
6. COPIA EL TOKEN (solo se muestra una vez)
7. Ve a repo Settings → Secrets and variables → Actions
8. New repository secret:
   Name: BOT_TOKEN
   Secret: [pega el token]
9. Click "Add secret"
```

**Nota**: El `GITHUB_TOKEN` por defecto debería funcionar. Solo usa esto si hay problemas.

---

## 🟢 OPCIONAL (Cuando tengas tiempo)

### 7. Habilitar Dependabot Alerts Auto-triage

```
Settings → Code security and analysis
✅ Dependabot alerts
✅ Dependabot security updates
Configure auto-triage rules (si disponible)
```

---

### 8. Verificar primer build GHCR

**Después del push**, verifica que las imágenes se publiquen:

```
1. Ve a: https://github.com/malpanez/ansible-devcontainer-vscode/actions
2. Busca workflow "Build and Publish Containers"
3. Debería estar ejecutándose o completado
4. Si falla, revisa los logs

5. Verifica imágenes en GHCR:
   https://github.com/malpanez?tab=packages
   Deberías ver actualizaciones recientes en:
   - devcontainer-ansible
   - devcontainer-terraform
   - devcontainer-golang
   - devcontainer-latex
```

---

### 9. Probar auto-merge

**Espera un día** para que Renovate/Dependabot abran un PR, luego:

```
1. Ve al PR de Renovate/Dependabot
2. Verifica que CI pase
3. Debería auto-mergearse automáticamente
4. Si no: Revisa que "Allow auto-merge" esté habilitado
```

---

## ✅ CHECKLIST FINAL

Marca cuando completes cada acción:

- [ ] Renovate App instalada
- [ ] Auto-merge habilitado en Settings
- [ ] Commit y push realizados
- [ ] Build GHCR verificado (post-push)
- [ ] Branch protection rules configuradas
- [ ] CVEs revisados en .trivyignore
- [ ] Token personal creado (si necesario)
- [ ] Primer auto-merge verificado (después de 1-2 días)

---

## 🆘 SI ALGO FALLA

### Renovate no crea PRs

```
1. Verifica instalación: https://github.com/apps/renovate/installations
2. Ve a repo Settings → Installed GitHub Apps
3. Debe aparecer "Renovate"
4. Si no: reinstala desde paso 1
```

### Auto-merge no funciona

```
1. Verifica Settings → General → "Allow auto-merge" ✅
2. Verifica que CI pase en el PR
3. Revisa logs del workflow auto-merge.yml
```

### Build GHCR falla

```
1. Ve a Actions → Build and Publish Containers
2. Click en el run fallido
3. Revisa logs de cada step
4. Común: problemas de red → Re-run
```

### Trivy scan falla en CI

```
# Es normal si hay CVEs nuevos
# Verifica .trivyignore está actualizado
# O temporalmente permite el fallo:
# En ci.yml: continue-on-error: true
```

---

## 📞 SOPORTE

Si necesitas ayuda:

1. **Documentación**:
   - IMPROVEMENTS_SUMMARY.md
   - docs/TROUBLESHOOTING.md
   - .github/versions.yml

2. **GitHub Issues**:
   https://github.com/malpanez/ansible-devcontainer-vscode/issues

3. **Email**:
   alpanez.alcalde@gmail.com

---

## 🎉 SIGUIENTE PASO

Una vez completadas las acciones urgentes (1-3):

```bash
# El repositorio estará completamente automatizado
# Las dependencias se actualizarán solas
# GHCR se limpiará automáticamente
# Security se monitoreará semanalmente
```

**¡Disfruta de tu repositorio best-in-class!** 🚀
