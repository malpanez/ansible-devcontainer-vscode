# Requirements: devcontainers

**Defined:** 2026-03-25
**Core Value:** Arranca en menos de 60 segundos con herramientas actualizadas — sin builds lentos, sin configuración manual, sin excusas para no empezar.

## v1 Requirements

### CI Stability

- [ ] **CI-01**: Todos los tests de pytest pasan consistentemente sin flakiness
- [ ] **CI-02**: No hay conflictos entre pytest-ansible y argparse en ningún entorno
- [ ] **CI-03**: Los tests de molecule/testinfra pasan en CI (no solo localmente)
- [ ] **CI-04**: El pipeline de CI completa en <15 minutos para cualquier stack

### Test Coverage

- [ ] **COV-01**: Cobertura ≥95% en todos los scripts Python (devcontainer-metadata.py, devcontainer-diff.py)
- [ ] **COV-02**: Tests de estructura de contenedor para todos los stacks (ansible, terraform, golang, latex)
- [ ] **COV-03**: Tests de smoke/validación para use-devcontainer.sh y doctor-devcontainer.sh
- [ ] **COV-04**: Tests de integración que validan el flujo completo de cambio de stack

### Security

- [ ] **SEC-01**: Cero alertas activas de Dependabot en dependencias críticas
- [ ] **SEC-02**: Cero findings de CodeQL sin justificación documentada
- [ ] **SEC-03**: Grype no reporta CVEs HIGH/CRITICAL sin plan de mitigación
- [ ] **SEC-04**: Todas las alertas dismisseadas tienen razón documentada en SECURITY_REVIEW.md

### Performance

- [ ] **PERF-01**: Build de imagen Ansible en <5 minutos con caché caliente
- [ ] **PERF-02**: Startup del devcontainer desde imagen pre-construida en <60 segundos
- [ ] **PERF-03**: Pipeline CI usa caché de capas Docker efectivamente (sin rebuilds innecesarios)

### User Experience

- [ ] **UX-01**: README documenta tiempo de inicio real medido (no estimado)
- [ ] **UX-02**: use-devcontainer.sh funciona sin prerrequisitos más allá de bash y git
- [ ] **UX-03**: doctor-devcontainer.sh detecta y explica cualquier problema de configuración

## v2 Requirements

### Stacks adicionales

- **STACK-01**: Stack Node.js/TypeScript (base Alpine + Node LTS)
- **STACK-02**: Stack Python puro (sin Ansible, para data science o scripting)
- **STACK-03**: Stack con kubectl + helm + kind para Kubernetes local

### Distribución

- **DIST-01**: Script de instalación one-liner que detecta el stack apropiado
- **DIST-02**: GitHub Template repo habilitado para fork rápido
- **DIST-03**: Attestaciones SLSA para supply-chain security

## Out of Scope

| Feature | Reason |
|---------|--------|
| Stacks Java/C#/Kotlin | No hay casos de uso actuales que los justifiquen |
| App web de configuración | El proyecto es infraestructura, no producto |
| Docker Desktop sin WSL2 | Demasiada variabilidad de entorno para soporte fiable |
| Signed releases con GPG | Infraestructura lista pero no prioritario ahora |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CI-01 | Phase 1 | Pending |
| CI-02 | Phase 1 | Pending |
| CI-03 | Phase 1 | Pending |
| CI-04 | Phase 4 | Pending |
| COV-01 | Phase 2 | Pending |
| COV-02 | Phase 2 | Pending |
| COV-03 | Phase 2 | Pending |
| COV-04 | Phase 2 | Pending |
| SEC-01 | Phase 3 | Pending |
| SEC-02 | Phase 3 | Pending |
| SEC-03 | Phase 3 | Pending |
| SEC-04 | Phase 3 | Pending |
| PERF-01 | Phase 4 | Pending |
| PERF-02 | Phase 4 | Pending |
| PERF-03 | Phase 4 | Pending |
| UX-01 | Phase 4 | Pending |
| UX-02 | Phase 2 | Pending |
| UX-03 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initial definition*
