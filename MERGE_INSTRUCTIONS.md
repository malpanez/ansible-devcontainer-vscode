# Instrucciones para Merge y Limpieza

**Fecha**: 2025-12-04

## 1️⃣ Crear PR para `feat/vscode-improvements-and-branch-cleanup`

La rama ya está pushed. Crear el PR manualmente:

**URL**: https://github.com/malpanez/ansible-devcontainer-vscode/compare/main...feat/vscode-improvements-and-branch-cleanup

**Título**:
```
feat: add VS Code improvements and automated branch cleanup
```

**Descripción**: (Copiar desde `/tmp/pr_body.md` o ver contenido abajo)

---

## 2️⃣ Crear PR para `docs/integration-guide`

La rama está rebased y lista.

**URL**: https://github.com/malpanez/ansible-devcontainer-vscode/compare/main...docs/integration-guide

**Título**:
```
docs: add integration guide improvements and devcontainer optimizations
```

**Descripción**:
```markdown
## Summary

Final updates to the integration guide with additional improvements:

- ✅ Added PROMPTS.md with ready-to-use LLM prompts
- ✅ Updated ARCHITECTURE.md with latest tool versions
- ✅ Fixed cache permissions in repo devcontainer
- ✅ Optimized devcontainer startup (removed unnecessary features)
- ✅ Updated README with sync workflow fix documentation

## Changes

### Documentation
- PROMPTS.md - Production-ready prompts for AI assistants
- ARCHITECTURE.md - Updated with current tool versions
- README.md - Added workflow fixes and version updates

### Devcontainer Optimizations
- Removed git/github-cli features (pre-installed in base image)
- Fixed pre-commit cache permissions
- Added updateContentCommand for proper cache ownership

### Workflow Fixes
- Updated sync-main-to-develop.yml branch condition

## Benefits

- 🤖 Easy integration with AI assistants (Claude, ChatGPT)
- ⚡ Faster devcontainer startup (~30s vs 2-5 min)
- 🔐 Resolved cache permission issues
- 📚 Complete integration documentation

## Rebased

This branch has been rebased with main and includes all latest changes.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

---

## 3️⃣ Merge PRs

Una vez aprobados los PRs, hacer merge en GitHub UI o via comandos:

```bash
# Opción A: Merge via GitHub UI (recomendado)
# - Ir a cada PR
# - Click "Squash and merge" o "Create merge commit"
# - Confirmar

# Opción B: Merge local (si prefieres CLI)
git checkout main
git pull origin main

# Merge vscode improvements
git merge --no-ff feat/vscode-improvements-and-branch-cleanup
git push origin main

# Merge integration guide
git merge --no-ff docs/integration-guide
git push origin main
```

---

## 4️⃣ Limpieza de Ramas (DESPUÉS de merges)

### Dry Run (preview seguro):
```bash
./scripts/cleanup-merged-branches.sh --dry-run
```

### Limpieza Real (interactiva):
```bash
./scripts/cleanup-merged-branches.sh
```

### O usar VS Code Task:
1. `Ctrl+Shift+P` (o `Cmd+Shift+P` en Mac)
2. Buscar: "Tasks: Run Task"
3. Seleccionar: "Cleanup Merged Branches"

---

## 5️⃣ Actualizar ROADMAP

Después de los merges, actualizar `docs/ROADMAP.md`:

```markdown
## Short Term

- [ ] **Baseline Release** – capture the current Ansible-focused stack...
- [ ] **WSL2 Onboarding Flow** – tighten the Windows bootstrap...
- [x] **Terraform Ready Stack** – ✅ DONE
- [x] **Context Switch Tasks** – ✅ DONE (PR #XXX - VS Code tasks)
- [x] **Automated Dependency Refresh** – ✅ DONE
- [x] **Recurring Image Hardening** – ✅ DONE
```

---

## 6️⃣ Verificación Post-Merge

```bash
# Actualizar main local
git checkout main
git pull origin main

# Verificar que todo está integrado
git log --oneline -10

# Verificar que las ramas fueron limpiadas automáticamente
git branch -a | grep -E "(feat/vscode|docs/integration)"
# No debería mostrar resultados si el workflow funcionó

# Ver estado de ramas
git branch --merged main
```

---

## 📋 Resumen de Comandos Rápidos

```bash
# 1. Crear PRs (manual en GitHub)
open https://github.com/malpanez/ansible-devcontainer-vscode/compare/main...feat/vscode-improvements-and-branch-cleanup
open https://github.com/malpanez/ansible-devcontainer-vscode/compare/main...docs/integration-guide

# 2. Después de merge, actualizar local
git checkout main && git pull origin main

# 3. Verificar limpieza automática (el workflow debería haberlo hecho)
git branch -a --merged main

# 4. Si hay ramas que no se limpiaron automáticamente:
./scripts/cleanup-merged-branches.sh --dry-run
./scripts/cleanup-merged-branches.sh

# 5. Actualizar ROADMAP
vim docs/ROADMAP.md
git add docs/ROADMAP.md
git commit -m "docs: update ROADMAP with completed tasks"
git push origin main
```

---

## ✅ Branches Que Se Limpiarán Automáticamente

Después de merge, el workflow `cleanup-merged-branches.yml` eliminará:
- `feat/vscode-improvements-and-branch-cleanup` ✅
- `docs/integration-guide` ✅

El resto de branches obsoletas (20+ identificadas en BRANCH_CLEANUP_REPORT.md)
se pueden limpiar manualmente después con el script.

---

## 🎯 Resultado Final Esperado

- ✅ 2 PRs merged a main
- ✅ VS Code mejorado con 11 nuevas tareas
- ✅ Workflow de limpieza automática activo
- ✅ Cache permissions resuelto
- ✅ Documentación actualizada
- ✅ ROADMAP marcado como completado
- ✅ ~20 branches obsoletas limpias

---

**Siguiente paso**: Abrir los PRs en GitHub con las URLs de arriba
