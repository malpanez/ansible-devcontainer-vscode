# ADR-0003: EditorConfig Instead of Prettier for Formatting

**Status**: Accepted
**Date**: 2024-12-03
**Deciders**: @malpanez
**Tags**: tooling, code-quality, formatting

---

## Context

The repository contains multiple file types that require consistent formatting:
- Python (`.py`)
- YAML (`.yml`, `.yaml`)
- Terraform (`.tf`, `.tfvars`)
- Markdown (`.md`)
- Shell scripts (`.sh`)
- JSON (`.json`)

We needed a solution to ensure:
- Consistent indentation across file types
- Proper line endings (LF vs CRLF)
- Trailing whitespace removal
- Final newline enforcement
- Cross-editor compatibility (VS Code, Vim, IntelliJ, etc.)

The question was whether to use **Prettier** (popular universal formatter) or **EditorConfig** (editor-agnostic configuration).

---

## Decision

Adopt **EditorConfig** (`.editorconfig` file) for basic formatting rules, and rely on **specialized formatters** for each language:
- Python: `ruff format` and `black`
- YAML: `yamllint` (with --fix where applicable)
- Terraform: `terraform fmt`
- Markdown: No formatter (EditorConfig handles basics)

Do **not** adopt Prettier to avoid conflicts with existing specialized tools.

---

## Rationale

### Avoid Tool Conflicts
- **ruff** and **black** already format Python code perfectly
- **terraform fmt** is the canonical Terraform formatter
- **yamllint** enforces YAML style rules
- Adding Prettier would create conflicts with these tools

### Editor-Agnostic
- EditorConfig works in **all major editors** (VS Code, Vim, Emacs, IntelliJ, Sublime)
- Prettier requires installation and configuration per editor
- Contributors can use any editor without plugin requirements

### Simpler Tool Chain
- One configuration file (`.editorconfig`) vs multiple Prettier configs
- No additional dependencies to install
- Faster pre-commit hooks (no Prettier execution time)
- Less configuration maintenance

### Granular Control
- Language-specific formatters have better knowledge of their syntax
- `terraform fmt` understands HCL alignment
- `ruff` and `black` understand Python semantics
- Generic formatters like Prettier can make suboptimal choices

---

## Consequences

### Positive

- ✅ **No conflicts**: Specialized formatters don't fight with each other
- ✅ **Editor flexibility**: Contributors can use any editor/IDE
- ✅ **Faster CI**: Don't need to run Prettier on all files
- ✅ **Simpler**: One `.editorconfig` file vs multiple tool configs
- ✅ **Language-optimal**: Each language gets best-in-class formatting
- ✅ **Lightweight**: No additional npm packages or Python deps

### Negative

- ⚠️ **Multiple tools**: Contributors need to run `ruff`, `terraform fmt`, `yamllint` separately
- ⚠️ **Learning curve**: Need to know which tool formats which file type
- ⚠️ **Partial automation**: EditorConfig doesn't auto-format, just guides editors

### Neutral

- ℹ️ Makefile provides `make format` to run all formatters
- ℹ️ Pre-commit hooks run all formatters automatically
- ℹ️ VS Code settings configure format-on-save per language

---

## Alternatives Considered

### Alternative 1: Prettier for Everything

**Pros:**
- Single tool for all languages
- Opinionated, no bikeshedding
- Very popular (30M+ weekly npm downloads)
- Good IDE integration
- Auto-fixes on save

**Cons:**
- **Conflicts with ruff/black**: Prettier's Python formatting differs from black
- **Conflicts with terraform fmt**: Prettier's HCL formatting is not canonical
- **Heavy dependency**: Requires Node.js in all devcontainers (even non-JS stacks)
- **Configuration complexity**: Need to ignore files already formatted by other tools
- **Not optimal**: Generic formatter can't match language-specific tools

**Why rejected:** The conflicts with existing formatters (ruff, black, terraform fmt) would create confusion and CI failures. We'd need complex configuration to exclude Python and Terraform files, defeating Prettier's "universal" benefit.

### Alternative 2: Language-Specific Formatters Only (No EditorConfig)

**Pros:**
- Best formatting for each language
- No generic tool compromises
- Explicit about what formats what

**Cons:**
- **No cross-editor consistency**: Each developer's editor uses different defaults
- **Inconsistent basics**: Some editors use tabs, others spaces
- **Line ending chaos**: Windows users might commit CRLF
- **No guidance**: New files don't automatically get correct formatting

**Why rejected:** While specialized formatters are great, EditorConfig provides essential baseline consistency (indentation, line endings) that prevents common issues like CRLF commits from Windows.

### Alternative 3: Prettier + Configuration to Defer to Specialized Tools

**Pros:**
- Get Prettier for Markdown, JSON, etc.
- Keep specialized tools for Python, Terraform
- Best of both worlds?

**Cons:**
- **Complex configuration**: Need extensive `prettierignore` and config overrides
- **Maintenance burden**: Keep Prettier config in sync with other tools
- **Confusing for contributors**: "Use Prettier except for..."
- **Still requires Node.js**: Heavy dependency for minimal benefit

**Why rejected:** The configuration complexity and maintenance burden outweigh the benefit. EditorConfig + specialized formatters is simpler and clearer.

---

## Implementation Notes

### .editorconfig File

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.{py,pyi}]
indent_style = space
indent_size = 4

[*.{yml,yaml,json}]
indent_style = space
indent_size = 2

[*.{tf,tfvars,hcl}]
indent_style = space
indent_size = 2

[*.go]
indent_style = tab

[Makefile]
indent_style = tab

[*.md]
trim_trailing_whitespace = false  # Preserve two-space line breaks
```

### Makefile Format Target

```makefile
.PHONY: format
format:  ## Format all code
	@echo "Formatting Python files..."
	@uvx ruff format .
	@echo "Formatting Terraform files..."
	@terraform fmt -recursive devcontainers/terraform/ || true
	@echo "Done!"
```

### Pre-commit Hook Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff-format

  - repo: https://github.com/hashicorp/terraform
    hooks:
      - id: terraform_fmt
```

### VS Code Settings

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "[terraform]": {
    "editor.defaultFormatter": "hashicorp.terraform",
    "editor.formatOnSave": true
  },
  "files.insertFinalNewline": true,
  "files.trimTrailingWhitespace": true
}
```

---

## References

- [EditorConfig Official Site](https://editorconfig.org/)
- [Prettier vs Language-Specific Formatters Discussion](https://github.com/prettier/prettier/issues/15388)
- [ruff Documentation](https://docs.astral.sh/ruff/)
- [Black vs Prettier for Python](https://github.com/psf/black/issues/118)
- Previous discussion: feat/vscode-improvements-and-branch-cleanup PR

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2024-12-03 | @malpanez | Created ADR based on Prettier evaluation |
| 2024-12-04 | @malpanez | Added implementation details and VS Code config |
