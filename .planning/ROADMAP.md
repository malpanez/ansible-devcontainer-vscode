# Roadmap: devcontainers

**Milestone:** v1.0 — CI verde, cobertura completa, seguridad limpia, pipeline rápido
**Core Value:** Arranca en menos de 60 segundos con herramientas actualizadas

---

## Phase 1 — CI Stability

**Goal:** Pipeline 100% verde y estable. Cero tests flaky. Cualquier commit en develop pasa CI de forma reproducible.

**Requirements:** CI-01, CI-02, CI-03

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Fix molecule trigger (develop) and add Python compat matrix to unit-tests
- [ ] 01-02-PLAN.md — Verify 3 consecutive green CI runs on develop (checkpoint)

**Deliverables:**
- Resolver conflictos pytest-ansible definitivamente (no solo con flags temporales)
- Verificar que los tests de ansible con regex_search pasan en todas las condiciones
- Añadir matriz de compatibilidad al CI para detectar regresiones futuras
- CI pasa en verde en 3 ejecuciones consecutivas

---

## Phase 2 — Test Coverage

**Goal:** Cobertura ≥95% en todos los scripts Python. Tests de estructura para todos los stacks. Scripts de shell validados.

**Requirements:** COV-01, COV-02, COV-03, COV-04, UX-02, UX-03

**Deliverables:**
- Tests unitarios para devcontainer-metadata.py y devcontainer-diff.py
- Tests de estructura de contenedor para los stacks que faltan
- Tests básicos para use-devcontainer.sh y doctor-devcontainer.sh
- Informe de cobertura en CI (codecov integrado)

---

## Phase 3 — Security Clean

**Goal:** Cero alertas de seguridad activas sin justificación. SECURITY_REVIEW.md actualizado y preciso.

**Requirements:** SEC-01, SEC-02, SEC-03, SEC-04

**Deliverables:**
- Resolver o documentar dismissal de todas las alertas Dependabot activas
- Resolver findings CodeQL o documentar falsos positivos con evidencia
- Grype sin CVEs HIGH/CRITICAL sin plan documentado
- SECURITY_REVIEW.md refleja estado actual (no el de diciembre 2025)

---

## Phase 4 — Pipeline Performance & UX Polish

**Goal:** Builds con caché efectivo, tiempos documentados, experiencia de usuario pulida.

**Requirements:** CI-04, PERF-01, PERF-02, PERF-03, UX-01

**Deliverables:**
- Caché de capas Docker optimizado en build-containers.yml
- Benchmark de startup medido y documentado en README
- CI completa en <15 minutos para cualquier stack
- README actualizado con tiempos reales, no estimaciones

---

## Status

| Phase | Status | Requirements |
|-------|--------|-------------|
| Phase 1 — CI Stability | In Progress | CI-01, CI-02, CI-03 |
| Phase 2 — Test Coverage | Not Started | COV-01..04, UX-02, UX-03 |
| Phase 3 — Security Clean | Not Started | SEC-01..04 |
| Phase 4 — Performance & UX | Not Started | CI-04, PERF-01..03, UX-01 |

---
*Created: 2026-03-25*
*Updated: 2026-03-25 — Phase 1 plans created*
