# devcontainers

## What This Is

Colección de DevContainers multi-stack (Ansible, Terraform, Go, LaTeX) optimizados para consumir los mínimos recursos posibles y arrancar en menos de 60 segundos. El objetivo es que cualquier persona pueda clonar el repo y tener un entorno de desarrollo completamente funcional sin esperas, listo para Claude Code, CVs, o cualquier proyecto.

## Core Value

Arranca en menos de 60 segundos con herramientas actualizadas — sin builds lentos, sin configuración manual, sin excusas para no empezar.

## Requirements

### Validated

<!-- Implementado y funcionando en producción -->

- ✓ 6 stacks de DevContainer publicados (base, ansible, ansible-podman, terraform, golang, latex) — milestone inicial
- ✓ Builds multi-arch (amd64/arm64) con GitHub Actions — milestone inicial
- ✓ Pipeline CI/CD completo con path-based change detection — milestone inicial
- ✓ Testing con pytest + molecule + testinfra — milestone inicial
- ✓ Documentación completa (README 38KB, ARCHITECTURE, CONTRIBUTING, ADRs) — milestone inicial
- ✓ Gestión automática de dependencias con Renovate — milestone inicial
- ✓ Seguridad: Trivy, CodeQL, Grype, detect-secrets — milestone inicial
- ✓ Pre-commit hooks (20+): black, ruff, hadolint, shellcheck, ansible-lint — milestone inicial
- ✓ Scripts de utilidad: use-devcontainer.sh, doctor-devcontainer.sh, bootstrap-windows.ps1 — milestone inicial
- ✓ Ansible roles reutilizables (5 roles, 3 playbooks) — milestone inicial

### Active

<!-- Scope actual: lo que falta para considerar el proyecto terminado -->

- [ ] CI completamente verde y estable (sin tests flaky ni falsos positivos)
- [ ] Cobertura de tests completa para todos los stacks y scripts
- [ ] Cero alertas de seguridad activas (Dependabot/CodeQL/Grype)
- [ ] Pipeline optimizado (builds más rápidos, mejor caché)
- [ ] Cualquier persona puede clonar y arrancar en <60 segundos verificado y documentado

### Out of Scope

- Stacks adicionales (Node, Java, Kotlin, C#) — complejidad no justificada para los casos de uso actuales
- App web o CLI interactiva — el proyecto es infraestructura, no producto
- Kubernetes stack — fuera del alcance del proyecto actual, posible v2
- Soporte para Docker Desktop en Windows sin WSL2 — demasiada variabilidad de entorno

## Context

- El proyecto está ~95% completo; los últimos 10 commits son todos fixes de CI (pytest-ansible conflicts, ansible_version variable, regex_search compatibility)
- Los tests más recientes que fallan están relacionados con pytest-ansible plugin vs pytest argparse conflicts
- Hay alertas de seguridad sin resolver documentadas en SECURITY_REVIEW.md (38 alertas con estrategia de dismissal)
- La imagen Ansible es 3-5x más pequeña que la universal de Microsoft (~650MB vs ~1.8GB)
- Usa uv en lugar de pip para instalaciones más rápidas y reproducibles
- El repo tiene branch protection: main=strict, develop=CI-only

## Constraints

- **Compatibilidad**: Debe funcionar en GitHub Codespaces (one-click launch)
- **Tamaño**: Imágenes deben mantenerse significativamente por debajo de las de Microsoft
- **Herramientas**: Solo herramientas disponibles en el devcontainer (no dependencias externas para pre-commit)
- **Seguridad**: No secrets en imágenes, no curl|sh sin versión pinneada

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| uv en lugar de pip | Instalaciones 10-100x más rápidas, lock reproducible | ✓ Good |
| python:3.12-slim-bookworm como base | Balance tamaño/compatibilidad | ✓ Good |
| Renovate auto-merge | Reducir fricción de mantenimiento | ✓ Good |
| pytest-ansible con `--p no:ansible` | Evitar conflictos argparse en pytest | — Pending |
| GHCR como registry | Integración nativa con GitHub Actions, gratuito | ✓ Good |
| Multi-arch (amd64+arm64) | Soporte Apple Silicon sin emulación | ✓ Good |

---
*Last updated: 2026-03-25 after GSD initialization*
