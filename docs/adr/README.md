# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for significant technical choices made in this project.

## What is an ADR?

An ADR is a document that captures an important architectural decision made along with its context and consequences. ADRs help us:
- Understand why decisions were made
- Onboard new contributors faster
- Avoid repeating discussions
- Learn from past choices
- Document trade-offs

## Format

We use a consistent template for all ADRs (see [template.md](template.md)).

Each ADR includes:
- **Context**: What problem are we solving?
- **Decision**: What did we choose to do?
- **Rationale**: Why did we make this choice?
- **Consequences**: What are the impacts (positive and negative)?
- **Alternatives**: What other options did we consider?

## Index of ADRs

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-use-uv-for-python-management.md) | Use uv for Python Package Management | Accepted | 2024-11-15 |
| [0002](0002-git-flow-branching-strategy.md) | Git Flow Branching Strategy | Accepted | 2024-10-20 |
| [0003](0003-editorconfig-vs-prettier.md) | EditorConfig Instead of Prettier for Formatting | Accepted | 2024-12-03 |

## Status Definitions

- **Proposed**: Decision under discussion
- **Accepted**: Decision approved and implemented
- **Deprecated**: Decision no longer recommended but still in use
- **Superseded**: Decision replaced by a newer ADR (reference the new ADR)

## Creating a New ADR

1. Copy [template.md](template.md) to a new file: `NNNN-brief-title.md`
2. Use the next sequential number (e.g., 0004)
3. Fill in all sections thoughtfully
4. Create a pull request for review
5. After approval, update this README index
6. Set status to "Accepted" and add implementation date

## Questions?

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the overall development workflow.
